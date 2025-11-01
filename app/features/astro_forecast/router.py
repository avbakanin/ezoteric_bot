"""Персональный астропрогноз (натальный календарь)."""

from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.astro import ForecastResult, daily_transit_service, transit_interpreter
from app.shared.birth_profiles import birth_profile_storage
from app.shared.decorators import catch_errors
from app.shared.keyboards import get_back_to_main_keyboard, get_premium_info_keyboard
from app.shared.messages import CommandsData, MessagesData, TextCommandsData
from app.shared.storage import user_storage

router = Router()


def _is_premium(user_id: int) -> bool:
    user = user_storage.get_user(user_id)
    subscription = user.get("subscription", {})
    return bool(subscription.get("active"))


def _format_iso_to_display(iso_date: str) -> str:
    try:
        return datetime.fromisoformat(iso_date).strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return iso_date or "—"


def _format_missing_fields(result: ForecastResult) -> str:
    mapping = {
        "birth_date": "дата рождения",
        "lat": "координаты",
        "lon": "координаты",
        "timezone": "часовой пояс",
        "profile": "профиль пользователя",
    }
    human = []
    for field in result.missing_fields:
        label = mapping.get(field, field)
        if label not in human:
            human.append(label)
    return ", ".join(human)


def _build_preview(result: ForecastResult) -> ForecastResult:
    return ForecastResult(
        user_id=result.user_id,
        target_date=result.target_date,
        natal_chart=result.natal_chart,
        transit_chart=result.transit_chart,
        aspects=result.aspects[:1],
        missing_fields=[],
    )


@router.message(Command(CommandsData.ASTRO_FORECAST), StateFilter("*"))
@router.message(F.text == TextCommandsData.ASTRO_FORECAST, StateFilter("*"))
@catch_errors()
async def handle_astro_forecast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(MessagesData.ASTRO_FORECAST_PROMPT)

    user_id = message.from_user.id
    forecast = daily_transit_service.generate_for_user(user_id)

    if forecast.missing_fields:
        if forecast.missing_fields == ["profile"]:
            await message.answer(
                MessagesData.ASTRO_FORECAST_MISSING_PROFILE,
                reply_markup=get_back_to_main_keyboard(),
            )
            return

        fields = _format_missing_fields(forecast)
        await message.answer(
            MessagesData.ASTRO_FORECAST_MISSING_FIELDS.format(fields=fields),
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    is_premium = _is_premium(user_id)

    if is_premium:
        text = transit_interpreter.render_forecast(forecast)
        await message.answer(text, reply_markup=get_back_to_main_keyboard())
        birth_profile_storage.save_forecast_text(
            user_id,
            forecast.target_date.isoformat(),
            text,
            is_preview=False,
        )
        return

    preview_forecast = _build_preview(forecast)
    preview_text = transit_interpreter.render_forecast(preview_forecast)
    preview_message = "\n\n".join([preview_text, MessagesData.ASTRO_FORECAST_PREMIUM_PREVIEW])
    await message.answer(
        preview_message,
        reply_markup=get_premium_info_keyboard(),
    )
    await message.answer(MessagesData.ASTRO_FORECAST_PREMIUM_ONLY, reply_markup=get_premium_info_keyboard())
    birth_profile_storage.save_forecast_text(
        user_id,
        forecast.target_date.isoformat(),
        preview_message,
        is_preview=True,
    )


@router.message(Command(CommandsData.ASTRO_FORECAST_HISTORY), StateFilter("*"))
@router.message(F.text == TextCommandsData.ASTRO_FORECAST_HISTORY, StateFilter("*"))
@catch_errors()
async def handle_astro_forecast_history(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    record = birth_profile_storage.get_last_forecast(user_id)
    if not record:
        await message.answer(
            MessagesData.ASTRO_FORECAST_HISTORY_EMPTY,
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    date_str = record.get("date")
    display_date = _format_iso_to_display(date_str) if date_str else "—"
    lines = [
        MessagesData.ASTRO_FORECAST_HISTORY_TITLE.format(date=display_date),
        record.get("text", ""),
    ]

    if record.get("is_preview"):
        lines.append(MessagesData.ASTRO_FORECAST_HISTORY_PREVIEW_NOTE)

    await message.answer("\n\n".join(lines), reply_markup=get_back_to_main_keyboard())


