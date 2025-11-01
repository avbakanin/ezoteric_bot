"""Дневник наблюдений."""

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.shared.decorators import catch_errors
from app.shared.keyboards import get_back_to_main_keyboard
from app.shared.messages import CallbackData, MessagesData, TextCommandsData
from app.shared.security import security_validator
from app.shared.state import UserStates
from app.shared.storage import user_storage

router = Router()


async def _enter_diary(state: FSMContext, send_func):
    await send_func(MessagesData.DIARY_PROMPT)
    await state.set_state(UserStates.waiting_for_diary_observation)


@router.callback_query(F.data == CallbackData.DIARY_OBSERVATION)
async def diary_observation_from_inline(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await _enter_diary(state, callback_query.message.edit_text)


@router.message(F.text == TextCommandsData.DIARY_OBSERVATION, StateFilter("*"))
async def diary_observation_from_menu(message: Message, state: FSMContext):
    await state.clear()
    await _enter_diary(state, message.answer)


@router.message(UserStates.waiting_for_diary_observation)
@catch_errors()
async def handle_diary_observation(message: Message, state: FSMContext):
    observation_text = message.text.strip()
    user_id = message.from_user.id

    if not security_validator.rate_limit_check(user_id, "diary"):
        await message.answer(
            MessagesData.ERROR_DIARY_LIMIT_EXCEEDED,
            reply_markup=get_back_to_main_keyboard(),
        )
        await state.clear()
        return

    sanitized_text = security_validator.sanitize_text(observation_text)
    user_data = user_storage.get_user(user_id)
    if "diary_observations" not in user_data:
        user_data["diary_observations"] = []

    observation = {
        "text": sanitized_text,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "number": user_data.get("life_path_number", "неизвестно"),
    }
    user_data["diary_observations"].append(observation)
    user_storage._save_data()

    result_text = (
        f"📝 Наблюдение сохранено!\n"
        f"Ваше число судьбы: {observation['number']}\n"
        f"Дата: {observation['date']}"
    )
    await message.answer(result_text, reply_markup=get_back_to_main_keyboard())
    await state.clear()

