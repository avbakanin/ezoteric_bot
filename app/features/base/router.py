"""Базовые команды и fallback."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.decorators import catch_errors
from app.shared.helpers import (
    check_streak_achievements,
    generate_daily_challenge,
    get_achievement_info,
    update_user_activity,
)
from app.shared.keyboards import get_about_keyboard, get_back_to_main_keyboard
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
    
    # Обновляем стрик и проверяем достижения
    streak = update_user_activity(user_id, "start")
    unlocked = check_streak_achievements(user_id, streak)
    
    await message.answer(MessagesData.START, reply_markup=get_main_menu_keyboard_categorized())
    
    # Генерируем ежедневное задание, если его еще нет
    challenge = generate_daily_challenge(user_id)
    if challenge:
        from app.shared.storage import user_storage
        challenge_id, challenge_data = challenge
        user_storage.set_daily_challenge(user_id, challenge_id, challenge_data)
        
        challenge_text = MessagesData.DAILY_CHALLENGE_NEW.format(
            title=challenge_data["title"],
            description=challenge_data["description"],
            reward=challenge_data["reward"]
        )
        await message.answer(challenge_text)
    
    # Показываем уведомление о достижении, если разблокировано
    if unlocked:
        for achievement_id in unlocked:
            name, desc = get_achievement_info(achievement_id)
            achievement_text = MessagesData.STREAK_ACHIEVEMENT_UNLOCKED.format(
                achievement_name=name,
                achievement_description=desc
            )
            await message.answer(achievement_text, reply_markup=get_back_to_main_keyboard())


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

