"""Аспект дня (общий транзитный аспект)."""

from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.astro import aspect_of_day_service
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


def _get_timezone(user_id: int) -> str:
    profile = birth_profile_storage.get_profile(user_id)
    if profile and profile.get("timezone"):
        return profile["timezone"]
    user = user_storage.get_user(user_id)
    return user.get("timezone") or "UTC"


def _local_today(tz_name: str):
    if ZoneInfo is None:
        return datetime.utcnow().date()
    try:
        return datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        return datetime.utcnow().date()


@router.message(Command(CommandsData.ASPECT_OF_DAY), StateFilter("*"))
@router.message(F.text == TextCommandsData.ASPECT_OF_DAY, StateFilter("*"))
@catch_errors()
async def aspect_of_day_command(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    is_premium = _is_premium(user_id)

    tz_name = _get_timezone(user_id)
    today = _local_today(tz_name)

    aspects = aspect_of_day_service.get_top(today, count=2 if is_premium else 1)
    text = aspect_of_day_service.format_message(aspects, is_premium)

    if not is_premium:
        text = "\n\n".join([text, MessagesData.ASPECT_OF_DAY_PREMIUM_PROMO])

    await message.answer(text, reply_markup=get_back_to_main_keyboard())
