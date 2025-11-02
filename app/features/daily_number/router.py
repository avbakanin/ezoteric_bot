"""Число дня с премиальным прогнозом."""

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.shared.calculations import calculate_daily_number
from app.shared.decorators import catch_errors
from app.shared.helpers import is_premium
from app.shared.keyboards import get_back_to_main_keyboard, get_premium_info_keyboard
from app.shared.messages import (
    CallbackData,
    CommandsData,
    MessagesData,
    TextCommandsData,
    format_daily_number,
)
from app.shared.storage import user_storage
from app.shared.texts import get_number_texts, get_text

router = Router()


async def _send_daily_number(send_func, user_id: int):
    is_premium_user = is_premium(user_id)

    if not is_premium_user:
        await send_func(
            MessagesData.DAILY_NUMBER_PREMIUM_REQUIRED,
            reply_markup=get_premium_info_keyboard(),
        )
        return

    today = datetime.now().strftime("%Y-%m-%d")
    cache = user_storage.get_daily_number_cache(user_id)

    if cache and cache.get("date") == today:
        daily_number = cache.get("number", 0)
        text = cache.get("text", "")
    else:
        daily_number = calculate_daily_number()
        number_texts = get_number_texts()
        contexts = number_texts.get(str(daily_number), {}) if number_texts else {}
        if not isinstance(contexts, dict):
            contexts = {}
        context_key = "premium_daily" if "premium_daily" in contexts else "daily"
        text = get_text(daily_number, context_key, user_id)
        user_storage.set_daily_number_cache(user_id, today, daily_number, text)

    message_text = format_daily_number(today, daily_number, text)
    await send_func(message_text, reply_markup=get_back_to_main_keyboard())


@router.message(Command(CommandsData.DAILY_NUMBER), StateFilter("*"))
@catch_errors()
async def daily_number_command(message: Message, state: FSMContext):
    await state.clear()
    await _send_daily_number(message.answer, message.from_user.id)


@router.message(F.text == TextCommandsData.DAILY_NUMBER, StateFilter("*"))
@catch_errors()
async def daily_number_button(message: Message, state: FSMContext):
    await state.clear()
    await _send_daily_number(message.answer, message.from_user.id)


@router.callback_query(F.data == CallbackData.DAILY_NUMBER)
@catch_errors()
async def daily_number_callback(callback: CallbackQuery):
    await callback.answer()
    await _send_daily_number(callback.message.answer, callback.from_user.id)

