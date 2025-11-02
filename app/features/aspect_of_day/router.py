"""Аспект дня (общий транзитный аспект)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.astro import aspect_of_day_service
from app.shared.decorators import catch_errors
from app.shared.helpers import get_today_local, get_user_timezone, is_premium
from app.shared.keyboards import get_back_to_main_keyboard, get_premium_info_keyboard
from app.shared.messages import CommandsData, MessagesData, TextCommandsData

router = Router()


@router.message(Command(CommandsData.ASPECT_OF_DAY), StateFilter("*"))
@router.message(F.text == TextCommandsData.ASPECT_OF_DAY, StateFilter("*"))
@catch_errors()
async def aspect_of_day_command(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    is_premium_user = is_premium(user_id)

    tz_name = get_user_timezone(user_id)
    today = get_today_local(tz_name)

    aspects = aspect_of_day_service.get_top(today, count=2 if is_premium_user else 1)
    text = aspect_of_day_service.format_message(aspects, is_premium_user)

    reply_markup = get_back_to_main_keyboard()

    if not is_premium_user:
        text = "\n\n".join([text, MessagesData.ASPECT_OF_DAY_PREMIUM_PROMO, MessagesData.ASPECT_OF_DAY_PREMIUM_CTA])
        reply_markup = get_premium_info_keyboard()
    else:
        text = "\n\n".join([text, MessagesData.ASPECT_OF_DAY_PREMIUM_THANKS])

    await message.answer(text, reply_markup=reply_markup)
