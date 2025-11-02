"""Базовые команды и fallback."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.decorators import catch_errors
from app.shared.keyboards import get_about_keyboard
from app.shared.keyboards.categories import get_main_menu_keyboard_categorized
from app.shared.messages import CommandsData, MessagesData, TextCommandsData

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command(CommandsData.START), StateFilter("*"))
@catch_errors("Ошибка при запуске бота.")
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info("Пользователь %s запустил бота", user_id)
    await state.clear()
    await message.answer(MessagesData.START, reply_markup=get_main_menu_keyboard_categorized())


@router.message(Command(CommandsData.MENU), StateFilter("*"))
@catch_errors()
async def menu_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(MessagesData.MAIN_MENU, reply_markup=get_main_menu_keyboard_categorized())


@router.message(Command(CommandsData.HELP), StateFilter("*"))
@catch_errors()
async def help_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(MessagesData.HELP)


@router.message(F.text == TextCommandsData.ABOUT, StateFilter("*"))
@catch_errors()
async def about_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(MessagesData.ABOUT_DESCRIPTION, reply_markup=get_about_keyboard())


@router.message(StateFilter(None))
@catch_errors()
async def unknown_message(message: Message):
    await message.answer(MessagesData.UNKNOWN)

