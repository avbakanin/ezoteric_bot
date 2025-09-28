from aiogram import Router
from aiogram.types import CallbackQuery
from messages import MESSAGES

router = Router()


from aiogram.fsm.context import FSMContext
from calculations import get_affirmation
from state import UserStates
from storage import user_storage


@router.callback_query(lambda c: c.data == "affirmation")
async def affirmation_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    _, text = get_affirmation(user_id)
    await callback_query.message.edit_text(f"✨ Твоя аффирмация:\n{text}")


@router.callback_query(lambda c: c.data in ["feedback", "leave_feedback", "suggestion", "report_bug"])
async def feedback_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.edit_text(MESSAGES["FEEDBACK"])
    await state.set_state(UserStates.waiting_for_feedback)


@router.callback_query(lambda c: c.data == "diary_observation")
async def diary_observation_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.edit_text("📔 Дневник наблюдений — напишите ваше наблюдение:")
    await state.set_state(UserStates.waiting_for_diary_observation)


@router.callback_query(lambda c: c.data == "calculate_number")
async def calculate_number_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    user_data = user_storage.get_user(user_id)
    saved_birth_date = user_data.get("birth_date")
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
        await callback_query.message.edit_text(MESSAGES["ERROR_LIMIT_EXCEEDED"])
        return

    # Нет сохраненной даты
    await callback_query.message.edit_text(MESSAGES["BASE_BIRTH_DATE_PROMPT"])
    await state.set_state(UserStates.waiting_for_birth_date)
