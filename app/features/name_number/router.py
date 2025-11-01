"""Расчёт числа имени."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.calculations import calculate_name_number, get_name_number_description
from app.shared.decorators import catch_errors
from app.shared.keyboards import get_back_to_main_keyboard
from app.shared.messages import (
    CommandsData,
    MessagesData,
    TextCommandsData,
    format_name_number_response,
)
from app.shared.security import security_validator
from app.shared.state import UserStates
from app.shared.storage import user_storage

router = Router()


async def _enter_name_number_flow(message: Message, state: FSMContext):
    await message.answer(MessagesData.NAME_NUMBER_PROMPT, reply_markup=get_back_to_main_keyboard())
    await state.set_state(UserStates.waiting_for_name_number)


@router.message(Command(CommandsData.NAME_NUMBER), StateFilter("*"))
@catch_errors()
async def name_number_command(message: Message, state: FSMContext):
    await state.clear()
    await _enter_name_number_flow(message, state)


@router.message(F.text == TextCommandsData.NAME_NUMBER, StateFilter("*"))
@catch_errors()
async def name_number_menu(message: Message, state: FSMContext):
    await state.clear()
    await _enter_name_number_flow(message, state)


@router.message(UserStates.waiting_for_name_number)
@catch_errors()
async def handle_name_number(message: Message, state: FSMContext):
    raw_name = message.text.strip()

    if not raw_name:
        await message.answer(MessagesData.NAME_NUMBER_EMPTY)
        return

    if not security_validator.validate_user_input(raw_name):
        await message.answer(MessagesData.NAME_NUMBER_EMPTY)
        return

    normalized_name = " ".join(raw_name.split())
    number = calculate_name_number(normalized_name)

    if number == 0:
        await message.answer(MessagesData.NAME_NUMBER_NO_LETTERS)
        return

    if not user_storage.can_make_request(message.from_user.id):
        await message.answer(
            MessagesData.ERROR_LIMIT_EXCEEDED,
            reply_markup=get_back_to_main_keyboard(),
        )
        await state.clear()
        return

    description = get_name_number_description(number)

    await message.answer(
        format_name_number_response(normalized_name, number, description),
        reply_markup=get_back_to_main_keyboard(),
    )
    await state.clear()

