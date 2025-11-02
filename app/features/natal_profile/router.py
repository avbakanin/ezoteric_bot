"""Сбор и обновление натальных данных пользователя."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.shared.birth_profiles import (
    birth_profile_storage,
    validate_age,
    validate_birth_date,
    validate_birth_time,
    validate_timezone,
)
from app.shared.decorators import catch_errors
from app.shared.formatters import format_iso_to_display
from app.shared.geocoding import GeocodeResult, geocode_candidates
from app.shared.helpers import check_base_achievements, get_achievement_info, update_user_activity
from app.shared.keyboards import get_back_to_main_keyboard, get_yes_no_keyboard
from app.shared.messages import CallbackData, CommandsData, MessagesData
from app.shared.state import NatalProfileStates
from app.shared.storage import user_storage

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover - для старых версий Python (не ожидается)
    ZoneInfo = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)

router = Router()

EXIT_WORDS = {"выход", "cancel", "отмена", "exit"}

POPULAR_TIMEZONES = [
    ("Europe/Moscow", "🇷🇺 Москва"),
    ("Europe/Kaliningrad", "🇷🇺 Калининград"),
    ("Europe/Samara", "🇷🇺 Самара"),
    ("Asia/Yekaterinburg", "🇷🇺 Екатеринбург"),
    ("Asia/Almaty", "🇰🇿 Алматы"),
    ("America/New_York", "🇺🇸 Нью-Йорк"),
]


def _should_exit(text: str) -> bool:
    return text.strip().lower() in EXIT_WORDS




async def _update_collected(state: FSMContext, **kwargs: Any) -> dict[str, Any]:
    data = await state.get_data()
    collected: dict[str, Any] = data.get("collected", {})
    collected.update(kwargs)
    await state.update_data(collected=collected)
    return collected


async def _prompt_age(message: Message, state: FSMContext) -> None:
    await message.answer(MessagesData.NATAL_PROFILE_REQUEST_AGE)
    await state.set_state(NatalProfileStates.waiting_for_age)


async def _prompt_birth_time(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    existing_time = data.get("existing_birth_time")
    if existing_time:
        await message.answer(
            MessagesData.NATAL_PROFILE_PROMPT_TIME_WITH_EXISTING.format(time=existing_time)
        )
    else:
        await message.answer(MessagesData.NATAL_PROFILE_PROMPT_TIME)
    await state.set_state(NatalProfileStates.waiting_for_birth_time)


async def _prompt_place(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    existing_place = data.get("existing_place")
    if existing_place:
        await message.answer(
            MessagesData.NATAL_PROFILE_PROMPT_PLACE_WITH_EXISTING.format(place=existing_place)
        )
    else:
        await message.answer(MessagesData.NATAL_PROFILE_PROMPT_PLACE)
    await state.set_state(NatalProfileStates.waiting_for_place)


async def _prompt_timezone(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    existing_timezone = data.get("existing_timezone")
    if existing_timezone:
        text = MessagesData.NATAL_PROFILE_PROMPT_TIMEZONE_WITH_EXISTING.format(
            timezone=existing_timezone
        )
    else:
        text = MessagesData.NATAL_PROFILE_PROMPT_TIMEZONE
    await message.answer(text, reply_markup=_build_timezone_keyboard(existing_timezone))
    await state.set_state(NatalProfileStates.waiting_for_timezone)


def _compute_utc_offset(birth_date_iso: str, birth_time: Optional[str], timezone: Optional[str]) -> Optional[float]:
    if not (timezone and ZoneInfo):
        return None
    try:
        birth_dt = datetime.strptime(
            f"{birth_date_iso} {birth_time or '12:00'}",
            "%Y-%m-%d %H:%M",
        )
        tz = ZoneInfo(timezone)
        offset = tz.utcoffset(birth_dt)
        if offset is None:
            return None
        hours = offset.total_seconds() / 3600
        return round(hours, 2)
    except Exception as exc:  # noqa: BLE001 - хотим лог, но не падать
        logger.debug("Не удалось вычислить UTC-смещение: %s", exc)
        return None


def _build_summary_text(collected: dict[str, Any]) -> str:
    return MessagesData.NATAL_PROFILE_SUMMARY.format(
        birth_date=collected.get("birth_date_display", "не указана"),
        birth_time=collected.get("birth_time", "не указано"),
        place=collected.get("place_name", "не указано"),
        timezone=collected.get("timezone", "не указан"),
        age=collected.get("age", "не указан"),
    )


def _build_place_options_keyboard(count: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=str(index + 1),
                callback_data=f"{CallbackData.NATAL_PLACE_PREFIX}{index}",
            )
        ]
        for index in range(count)
    ]
    rows.append(
        [InlineKeyboardButton(text="Ввести вручную", callback_data=CallbackData.NATAL_PLACE_REENTER)]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _serialize_candidates(candidates: list[GeocodeResult]) -> list[dict[str, Any]]:
    return [candidate.to_dict() for candidate in candidates]


def _deserialize_candidates(raw: list[dict[str, Any]]) -> list[GeocodeResult]:
    return [GeocodeResult.from_dict(item) for item in raw]


def _build_timezone_keyboard(current: str | None = None) -> InlineKeyboardMarkup:
    options = list(POPULAR_TIMEZONES)
    if current and current not in {tz for tz, _ in options}:
        options.insert(0, (current, "🟢 Текущий"))

    buttons: list[InlineKeyboardButton] = []
    for tz, label in options:
        if label.startswith("🟢"):
            text = f"{label}: {tz}"
        else:
            text = f"{label} ({tz})"
        buttons.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"{CallbackData.NATAL_TIMEZONE_PREFIX}{tz}",
            )
        )

    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    rows.append(
        [InlineKeyboardButton(text="Другое…", callback_data=CallbackData.NATAL_TIMEZONE_MANUAL)]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _apply_timezone(message: Message, state: FSMContext, timezone: str) -> None:
    await _update_collected(state, timezone=timezone)

    data = await state.get_data()
    collected = data.get("collected", {})
    utc_offset = _compute_utc_offset(
        collected.get("birth_date"),
        collected.get("birth_time"),
        timezone,
    )
    await _update_collected(state, utc_offset=utc_offset)

    offset_hint = ""
    if utc_offset is not None:
        sign = "+" if utc_offset >= 0 else ""
        offset_hint = f" (UTC{sign}{utc_offset:.1f})"

    await message.answer(
        MessagesData.NATAL_PROFILE_TIMEZONE_SAVED.format(timezone=timezone, offset_hint=offset_hint)
    )
    await _save_profile_and_finish(message, state)


async def _save_profile_and_finish(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    collected: dict[str, Any] = data.get("collected", {})
    birth_date_iso = collected.get("birth_date")

    if not birth_date_iso:
        await message.answer(MessagesData.ERROR_DEFAULT, reply_markup=get_back_to_main_keyboard())
        await state.clear()
        return

    utc_offset = collected.get("utc_offset")
    if utc_offset is None:
        utc_offset = _compute_utc_offset(
            birth_date_iso,
            collected.get("birth_time"),
            collected.get("timezone"),
        )
        collected["utc_offset"] = utc_offset
        await state.update_data(collected=collected)

    user_id = message.from_user.id
    birth_profile_storage.upsert_profile(
        user_id,
        birth_date=birth_date_iso,
        birth_time=collected.get("birth_time"),
        timezone=collected.get("timezone"),
        utc_offset=utc_offset,
        lat=collected.get("lat"),
        lon=collected.get("lon"),
        place_name=collected.get("place_name"),
        age=collected.get("age"),
    )

    user_storage.update_user(
        user_id,
        birth_date=collected.get("birth_date_display"),
        birth_time=collected.get("birth_time"),
        timezone=collected.get("timezone"),
        utc_offset=utc_offset,
        lat=collected.get("lat"),
        lon=collected.get("lon"),
        place_name=collected.get("place_name"),
        age=collected.get("age"),
    )

    summary = _build_summary_text(collected)
    await message.answer(summary)
    
    # Обновляем стрик и проверяем достижения
    streak = update_user_activity(user_id, "natal_profile")
    unlocked_base = check_base_achievements(user_id)
    
    await message.answer(MessagesData.NATAL_PROFILE_COMPLETED, reply_markup=get_back_to_main_keyboard())
    
    # Показываем достижения, если разблокированы
    if unlocked_base:
        for achievement_id in unlocked_base:
            name, desc = get_achievement_info(achievement_id)
            achievement_text = MessagesData.STREAK_ACHIEVEMENT_UNLOCKED.format(
                achievement_name=name,
                achievement_description=desc
            )
            await message.answer(achievement_text, reply_markup=get_back_to_main_keyboard())
    
    await state.clear()


@router.message(Command(CommandsData.NATAL_PROFILE), StateFilter("*"))
@catch_errors()
async def start_natal_profile(message: Message, state: FSMContext):
    await state.clear()

    user_id = message.from_user.id
    user_data = user_storage.get_user(user_id)
    profile = birth_profile_storage.get_profile(user_id) or {}

    existing_birth_date_iso: Optional[str] = profile.get("birth_date")
    if not existing_birth_date_iso and user_data.get("birth_date"):
        try:
            existing_birth_date_iso = validate_birth_date(user_data["birth_date"])
        except ValueError:
            existing_birth_date_iso = None

    existing_age = None
    for raw_age in (profile.get("age"), user_data.get("age")):
        try:
            candidate = validate_age(raw_age)
        except ValueError:
            candidate = None
        if candidate:
            existing_age = candidate
            break

    existing_time = profile.get("birth_time") or user_data.get("birth_time")
    existing_place = profile.get("place_name") or user_data.get("place_name")
    existing_timezone = profile.get("timezone") or user_data.get("timezone")
    existing_lat = profile.get("lat") or user_data.get("lat")
    existing_lon = profile.get("lon") or user_data.get("lon")

    state_payload = {
        "collected": {},
        "existing_birth_time": existing_time,
        "existing_place": existing_place,
        "existing_timezone": existing_timezone,
        "existing_lat": existing_lat,
        "existing_lon": existing_lon,
        "age_candidate": existing_age,
    }

    if existing_birth_date_iso:
        state_payload["existing_birth_date"] = existing_birth_date_iso

    await state.update_data(state_payload)

    if existing_birth_date_iso:
        display_date = format_iso_to_display(existing_birth_date_iso)
        prompt = MessagesData.NATAL_PROFILE_PROMPT_DATE_WITH_EXISTING.format(date=display_date)
    else:
        prompt = MessagesData.NATAL_PROFILE_PROMPT_DATE

    await message.answer(prompt, reply_markup=get_back_to_main_keyboard())
    await state.set_state(NatalProfileStates.waiting_for_birth_date)


@router.message(NatalProfileStates.waiting_for_birth_date)
@catch_errors()
async def handle_birth_date(message: Message, state: FSMContext):
    text = message.text.strip()
    if _should_exit(text):
        await message.answer(MessagesData.NATAL_PROFILE_EXIT, reply_markup=get_back_to_main_keyboard())
        await state.clear()
        return

    try:
        birth_date_iso = validate_birth_date(text)
    except ValueError:
        await message.answer(MessagesData.NATAL_PROFILE_PROMPT_DATE)
        return

    display_date = format_iso_to_display(birth_date_iso)
    await _update_collected(state, birth_date=birth_date_iso, birth_date_display=display_date)
    await message.answer(MessagesData.NATAL_PROFILE_DATE_SAVED.format(date=display_date))

    data = await state.get_data()
    age_candidate = data.get("age_candidate")
    if age_candidate:
        await message.answer(
            MessagesData.NATAL_PROFILE_CONFIRM_AGE.format(age=age_candidate),
            reply_markup=get_yes_no_keyboard(),
        )
        await state.set_state(NatalProfileStates.confirm_age)
    else:
        await _prompt_age(message, state)


@router.callback_query(NatalProfileStates.confirm_age, F.data == CallbackData.YES)
@catch_errors()
async def confirm_age_yes(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    age = data.get("age_candidate")
    if age is None:
        await callback.message.edit_text(MessagesData.NATAL_PROFILE_REQUEST_AGE)
        await state.set_state(NatalProfileStates.waiting_for_age)
        return

    await _update_collected(state, age=age)
    await callback.message.edit_text(MessagesData.NATAL_PROFILE_AGE_CONFIRMED.format(age=age))
    await _prompt_birth_time(callback.message, state)


@router.callback_query(NatalProfileStates.confirm_age, F.data == CallbackData.NO)
@catch_errors()
async def confirm_age_no(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(MessagesData.NATAL_PROFILE_REQUEST_AGE)
    await state.set_state(NatalProfileStates.waiting_for_age)


@router.message(NatalProfileStates.waiting_for_age)
@catch_errors()
async def handle_age(message: Message, state: FSMContext):
    text = message.text.strip()
    if _should_exit(text):
        await message.answer(MessagesData.NATAL_PROFILE_EXIT, reply_markup=get_back_to_main_keyboard())
        await state.clear()
        return

    try:
        age = validate_age(text)
    except ValueError:
        await message.answer(MessagesData.NATAL_PROFILE_INVALID_AGE)
        return

    await _update_collected(state, age=age)
    await message.answer(MessagesData.NATAL_PROFILE_AGE_CONFIRMED.format(age=age))
    await _prompt_birth_time(message, state)


@router.message(NatalProfileStates.waiting_for_birth_time)
@catch_errors()
async def handle_birth_time(message: Message, state: FSMContext):
    text = message.text.strip()
    if _should_exit(text):
        await message.answer(MessagesData.NATAL_PROFILE_EXIT, reply_markup=get_back_to_main_keyboard())
        await state.clear()
        return

    lowered = text.lower()
    if lowered in {"нет", "не знаю", "не помню"}:
        await _update_collected(state, birth_time=None)
        await message.answer(MessagesData.NATAL_PROFILE_TIME_SKIPPED)
        await _prompt_place(message, state)
        return

    try:
        birth_time = validate_birth_time(text)
    except ValueError:
        await message.answer(MessagesData.NATAL_PROFILE_INVALID_TIME)
        return

    await _update_collected(state, birth_time=birth_time)
    await message.answer(MessagesData.NATAL_PROFILE_TIME_SAVED.format(time=birth_time))
    await _prompt_place(message, state)


@router.message(StateFilter(NatalProfileStates.waiting_for_place, NatalProfileStates.confirm_place))
@catch_errors()
async def handle_place(message: Message, state: FSMContext):
    text = message.text.strip()
    if _should_exit(text):
        await message.answer(MessagesData.NATAL_PROFILE_EXIT, reply_markup=get_back_to_main_keyboard())
        await state.clear()
        return

    if len(text) < 3:
        await message.answer(MessagesData.NATAL_PROFILE_PLACE_NOT_FOUND)
        return

    try:
        candidates = geocode_candidates(text, limit=5)
    except Exception as exc:  # noqa: BLE001 - хотим показать понятную ошибку
        logger.error("Ошибка геокодирования: %s", exc)
        await message.answer(MessagesData.NATAL_PROFILE_PLACE_NOT_FOUND)
        return

    if not candidates:
        await message.answer(MessagesData.NATAL_PROFILE_PLACE_NOT_FOUND)
        return

    if len(candidates) == 1:
        result = candidates[0]
        await _update_collected(
            state,
            place_name=result.display_name,
            lat=result.lat,
            lon=result.lon,
        )
        await state.update_data(existing_place=result.display_name)
        await message.answer(
            MessagesData.NATAL_PROFILE_PLACE_SAVED.format(
                place=result.display_name,
                lat=result.lat,
                lon=result.lon,
            )
        )
        await _prompt_timezone(message, state)
        return

    options = candidates[:3]
    options_text = "\n".join(
        f"{index}. {candidate.display_name}" for index, candidate in enumerate(options, start=1)
    )

    await state.update_data(place_candidates=_serialize_candidates(options))
    await message.answer(
        MessagesData.NATAL_PROFILE_PLACE_OPTIONS.format(options=options_text),
        reply_markup=_build_place_options_keyboard(len(options)),
    )
    await state.set_state(NatalProfileStates.confirm_place)


@router.callback_query(
    NatalProfileStates.confirm_place,
    F.data.startswith(CallbackData.NATAL_PLACE_PREFIX),
)
@catch_errors()
async def handle_place_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    raw_candidates = data.get("place_candidates") or []
    candidates = _deserialize_candidates(raw_candidates)

    try:
        index = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.message.answer(MessagesData.NATAL_PROFILE_PLACE_CHOICE_INVALID)
        await _prompt_place(callback.message, state)
        return

    if index < 0 or index >= len(candidates):
        await callback.message.answer(MessagesData.NATAL_PROFILE_PLACE_CHOICE_INVALID)
        await _prompt_place(callback.message, state)
        return

    result = candidates[index]
    await _update_collected(
        state,
        place_name=result.display_name,
        lat=result.lat,
        lon=result.lon,
    )
    await state.update_data(existing_place=result.display_name, place_candidates=None)
    await callback.message.edit_text(
        MessagesData.NATAL_PROFILE_PLACE_CHOICE_CONFIRMED.format(
            place=result.display_name,
            lat=result.lat,
            lon=result.lon,
        )
    )
    await _prompt_timezone(callback.message, state)


@router.callback_query(NatalProfileStates.confirm_place, F.data == CallbackData.NATAL_PLACE_REENTER)
@catch_errors()
async def handle_place_reenter(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(MessagesData.NATAL_PROFILE_PROMPT_PLACE)
    await state.set_state(NatalProfileStates.waiting_for_place)


@router.callback_query(NatalProfileStates.waiting_for_timezone, F.data == CallbackData.NATAL_TIMEZONE_MANUAL)
@catch_errors()
async def handle_timezone_manual(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_reply_markup(None)
    await callback.message.answer(MessagesData.NATAL_PROFILE_TIMEZONE_MANUAL_PROMPT)


@router.callback_query(
    NatalProfileStates.waiting_for_timezone,
    F.data.startswith(CallbackData.NATAL_TIMEZONE_PREFIX),
)
@catch_errors()
async def handle_timezone_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    timezone = callback.data[len(CallbackData.NATAL_TIMEZONE_PREFIX) :]
    try:
        timezone = validate_timezone(timezone)
    except ValueError:
        await callback.message.answer(MessagesData.NATAL_PROFILE_INVALID_TIMEZONE)
        return

    await callback.message.edit_reply_markup(None)
    await _apply_timezone(callback.message, state, timezone)


@router.message(NatalProfileStates.waiting_for_timezone)
@catch_errors()
async def handle_timezone(message: Message, state: FSMContext):
    text = message.text.strip()
    if _should_exit(text):
        await message.answer(MessagesData.NATAL_PROFILE_EXIT, reply_markup=get_back_to_main_keyboard())
        await state.clear()
        return

    try:
        timezone = validate_timezone(text)
    except ValueError:
        await message.answer(MessagesData.NATAL_PROFILE_INVALID_TIMEZONE)
        return

    await _apply_timezone(message, state, timezone)


