"""Гадание Да/Нет."""

import random

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.decorators import catch_errors
from app.shared.keyboards import get_back_to_main_keyboard
from app.shared.messages import CommandsData, MessagesData, TextCommandsData, format_yes_no_response
from app.shared.security import security_validator
from app.shared.state import UserStates

router = Router()

YES_NO_ANSWERS = ["Да", "Нет", "Скорее нет"]


async def _enter_yes_no_flow(message: Message, state: FSMContext):
    await message.answer(MessagesData.YES_NO_PROMPT, reply_markup=get_back_to_main_keyboard())
    await state.set_state(UserStates.waiting_for_yes_no_question)


@router.message(Command(CommandsData.YES_NO), StateFilter("*"))
@catch_errors()
async def yes_no_command(message: Message, state: FSMContext):
    await state.clear()
    await _enter_yes_no_flow(message, state)


@router.message(F.text == TextCommandsData.YES_NO, StateFilter("*"))
@catch_errors()
async def yes_no_menu(message: Message, state: FSMContext):
    await state.clear()
    await _enter_yes_no_flow(message, state)


@router.message(UserStates.waiting_for_yes_no_question)
@catch_errors()
async def handle_yes_no_question(message: Message, state: FSMContext):
    question = message.text.strip()

    if not question:
        await message.answer(MessagesData.YES_NO_EMPTY)
        return

    if not security_validator.validate_user_input(question):
        await message.answer(MessagesData.YES_NO_EMPTY)
        return

    sanitized_question = security_validator.sanitize_text(question)
    answer = random.choice(YES_NO_ANSWERS)

    await message.answer(
        format_yes_no_response(sanitized_question, answer),
        reply_markup=get_back_to_main_keyboard(),
    )
    await state.clear()

