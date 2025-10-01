from datetime import datetime

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from calculations import get_affirmation
from decorators import catch_errors
from keyboards import get_back_to_main_keyboard
from messages import CallbackData, MessagesData, get_affirmation_text
from security import security_validator
from state import UserStates
from storage import user_storage

router = Router()


@router.callback_query(lambda c: c.data == CallbackData.AFFIRMATION)
async def affirmation_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    _, text = get_affirmation(user_id)
    await callback_query.message.edit_text(get_affirmation_text(text))


@router.callback_query(
    lambda c: c.data
    in [
        CallbackData.FEEDBACK,
        CallbackData.LEAVE_FEEDBACK,
        CallbackData.SUGGESTION,
        CallbackData.REPORT_BUG,
    ]
)
async def feedback_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.edit_text(MessagesData.FEEDBACK_CB)
    await state.set_state(UserStates.waiting_for_feedback)


@router.callback_query(lambda c: c.data == CallbackData.DIARY_OBSERVATION)
async def diary_observation_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.edit_text(MessagesData.DIARY_PROMPT)
    await state.set_state(UserStates.waiting_for_diary_observation)


# ===========================
# Дневник наблюдений - запись по датам наблюдений человек(бесплатно 3 в день)
# ===========================


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


@router.callback_query(lambda c: c.data == CallbackData.CALCULATE_NUMBER)
async def calculate_number_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    cached_result = user_storage.get_cached_result(user_id)

    # Лимиты и кэш
    if (
        cached_result
        and cached_result.get("life_path_result")
        and user_storage.can_view_cached_result(user_id)
    ):
        life_path = cached_result["life_path_result"]
        text = f"Ваше число судьбы: {life_path}"  # можно вызвать get_text
        await callback_query.message.edit_text(text)
        user_storage.increment_repeat_view(user_id)
        return

    if not user_storage.can_make_request(user_id):
        await callback_query.message.edit_text(MessagesData.ERROR_LIMIT_EXCEEDED)
        return

    # Нет сохраненной даты
    await callback_query.message.edit_text(MessagesData.BASE_BIRTH_DATE_PROMPT)
    await state.set_state(UserStates.waiting_for_birth_date)
