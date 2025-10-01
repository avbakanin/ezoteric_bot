# ===========================
# Совместимость
# ===========================
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from calculations import calculate_life_path_number, validate_date
from decorators import catch_errors
from keyboards import get_back_to_main_keyboard, get_compatibility_result_keyboard
from messages import MessagesData, TextCommandsData
from state import UserStates

router = Router()


@router.message(F.text == TextCommandsData.COMPATIBILITY)
@catch_errors()
async def compatibility_command(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите первую дату рождения (ДД.ММ.ГГГГ):", reply_markup=get_back_to_main_keyboard()
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
        "Введите вторую дату рождения (ДД.ММ.ГГГГ):", reply_markup=get_back_to_main_keyboard()
    )
    await state.set_state(UserStates.waiting_for_second_date)


@router.message(UserStates.waiting_for_second_date)
@catch_errors()
async def handle_second_date(message: types.Message, state: FSMContext):
    second_date = message.text.strip()
    if not validate_date(second_date):
        await message.answer(MessagesData.ERROR_INVALID_DATE)
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
    await message.answer(result_text, reply_markup=get_compatibility_result_keyboard())
    await state.clear()
