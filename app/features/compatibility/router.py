"""Проверка совместимости."""

from aiogram import F, Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from app.shared.calculations import calculate_life_path_number, validate_date
from app.shared.decorators import catch_errors
from app.shared.helpers import (
    check_base_achievements,
    check_streak_achievements,
    get_achievement_info,
    update_user_activity,
)
from app.shared.keyboards import get_back_to_main_keyboard, get_compatibility_result_keyboard
from app.shared.messages import MessagesData, TextCommandsData
from app.shared.state import UserStates
from app.shared.storage import user_storage

router = Router()


@router.message(F.text == TextCommandsData.COMPATIBILITY, StateFilter("*"))
@catch_errors()
async def compatibility_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Введите первую дату рождения (ДД.ММ.ГГГГ):",
        reply_markup=get_back_to_main_keyboard(),
    )
    await state.set_state(UserStates.waiting_for_first_date)


@router.message(UserStates.waiting_for_first_date)
@catch_errors()
async def handle_first_date(message: types.Message, state: FSMContext):
    first_date = message.text.strip()
    if not validate_date(first_date):
        await message.answer(MessagesData.ERROR_INVALID_DATE)
        return

    await state.update_data(first_date=first_date)
    await message.answer(
        "Введите вторую дату рождения (ДД.ММ.ГГГГ):",
        reply_markup=get_back_to_main_keyboard(),
    )
    await state.set_state(UserStates.waiting_for_second_date)


@router.message(UserStates.waiting_for_second_date)
@catch_errors()
async def handle_second_date(message: types.Message, state: FSMContext):
    second_date = message.text.strip()
    if not validate_date(second_date):
        await message.answer(MessagesData.ERROR_INVALID_DATE)
        return

    user_id = message.from_user.id

    if not user_storage.can_check_compatibility(user_id):
        await message.answer(
            MessagesData.ERROR_LIMIT_EXCEEDED,
            reply_markup=get_back_to_main_keyboard(),
        )
        await state.clear()
        return

    data = await state.get_data()
    first_date = data.get("first_date")
    first_number = calculate_life_path_number(first_date)
    second_number = calculate_life_path_number(second_date)

    score = 3
    description = "Низкая совместимость. Потребуется много усилий."
    diff = abs(first_number - second_number)
    if diff == 0:
        score, description = 9, "Идеальная совместимость! Вы очень похожи по характеру."
    elif diff <= 2:
        score, description = 7, "Хорошая совместимость. Вы дополняете друг друга."
    elif diff <= 4:
        score, description = 5, "Средняя совместимость. Требуется понимание и компромиссы."

    result_text = (
        f"💑 СОВМЕСТИМОСТЬ: {first_number} и {second_number}\nОценка: {score}/9\n{description}"
    )
    
    # Обновляем стрик и проверяем достижения
    streak = update_user_activity(user_id, "compatibility")
    user_storage.increment_usage(user_id, "compatibility")
    unlocked_streak = check_streak_achievements(user_id, streak)
    unlocked_base = check_base_achievements(user_id)
    unlocked = unlocked_streak + unlocked_base
    
    await message.answer(result_text, reply_markup=get_compatibility_result_keyboard())
    
    # Показываем достижения, если разблокированы
    if unlocked:
        for achievement_id in unlocked:
            name, desc = get_achievement_info(achievement_id)
            achievement_text = MessagesData.STREAK_ACHIEVEMENT_UNLOCKED.format(
                achievement_name=name,
                achievement_description=desc
            )
            await message.answer(achievement_text, reply_markup=get_back_to_main_keyboard())
    
    await state.clear()

