"""Команда для просмотра ретроградных предупреждений."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.astro import retrograde_service
from app.shared.birth_profiles import birth_profile_storage
from app.shared.decorators import catch_errors
from app.shared.keyboards import get_back_to_main_keyboard
from app.shared.messages import CommandsData, MessagesData, TextCommandsData
from app.shared.storage import user_storage

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


router = Router()


def _is_premium(user_id: int) -> bool:
    user = user_storage.get_user(user_id)
    subscription = user.get("subscription", {})
    return bool(subscription.get("active"))


def _get_user_timezone(user_id: int) -> str:
    profile = birth_profile_storage.get_profile(user_id)
    if profile and profile.get("timezone"):
        return profile["timezone"]
    user = user_storage.get_user(user_id)
    return user.get("timezone") or "UTC"


@router.message(Command(CommandsData.RETRO_ALERTS), StateFilter("*"))
@router.message(F.text == TextCommandsData.RETRO_ALERTS, StateFilter("*"))
@catch_errors()
async def retro_alerts_command(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    is_premium = _is_premium(user_id)

    tz_name = _get_user_timezone(user_id)
    today_local = _get_today_local(tz_name)

    periods = retrograde_service.get_periods(today_local, today_local + timedelta(days=120))
    allowed_planets = retrograde_service.tracked_planets if is_premium else ("Mercury",)

    blocks: list[str] = []
    for planet in allowed_planets:
        planet_periods = periods.get(planet, [])
        next_period = retrograde_service.get_next_period(planet, planet_periods, today_local)
        if not next_period:
            continue
        blocks.append(retrograde_service.format_summary(next_period, is_premium, today_local))

    if not blocks:
        await message.answer(
            MessagesData.RETRO_ALERTS_EMPTY,
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    if not is_premium and any(planet != "Mercury" for planet in retrograde_service.tracked_planets):
        blocks.append(MessagesData.RETRO_ALERTS_PREMIUM_PROMO)

    await message.answer("\n\n".join(blocks), reply_markup=get_back_to_main_keyboard())


def _get_today_local(tz_name: str) -> date:
    if ZoneInfo is None:
        return date.today()
    try:
        tz = ZoneInfo(tz_name)
        return datetime.now(tz).date()
    except Exception:
        return date.today()


