"""
Обработчики команд и сообщений бота через роутер
"""

import json
import logging
import random
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from calculations import calculate_life_path_number, calculate_soul_number, validate_date
from decorators import catch_errors
from keyboards import (
    get_about_keyboard,
    get_back_to_main_keyboard,
    get_main_menu_keyboard,
    get_premium_info_keyboard,
    get_profile_keyboard,
    get_result_keyboard,
)
from messages import (
    CommandsData,
    MessagesData,
    TextCommandsData,
    get_format_life_path_result,
    get_profile_text,
)
from state import UserStates
from storage import user_storage

logger = logging.getLogger(__name__)

router = Router()

# Путь к файлу с числами
NUMBERS_FILE = Path(__file__).parent.parent.parent / "numbers.json"

# Кэш для текстов чисел
_number_texts_cache = None


def get_number_texts():
    global _number_texts_cache
    if _number_texts_cache is None:
        try:
            with open(NUMBERS_FILE, "r", encoding="utf-8") as f:
                _number_texts_cache = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке numbers.json: {e}")
            _number_texts_cache = {}
    return _number_texts_cache


def get_text(number: int, context: str, user_id: int) -> str:
    try:
        number_texts = get_number_texts()
        if str(number) not in number_texts or context not in number_texts[str(number)]:
            return "Информация временно недоступна."
        options = number_texts[str(number)][context]
        shown = user_storage.get_text_history(user_id)
        unused = [t for t in options if t not in shown]
        if not unused:
            unused = options
            # очищаем историю показанных текстов
            user_storage.update_user(user_id, text_history=[])
        chosen = random.choice(unused)
        user_storage.add_text_to_history(user_id, chosen)
        return chosen
    except Exception as e:
        logger.error(f"Ошибка в get_text: {e}")
        return "Произошла ошибка. Попробуйте позже."


# ===========================
# Основные команды
# ===========================


@router.message(Command(CommandsData.START))
@catch_errors("Ошибка при запуске бота.")
async def start_command(message: Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запустил бота")
    await message.answer(MessagesData.START, reply_markup=get_main_menu_keyboard())


# ===========================
# Обработка даты рождения
# ===========================


@router.message(UserStates.waiting_for_birth_date)
@catch_errors()
async def handle_birth_date(message: Message, state: FSMContext):
    user_id = message.from_user.id
    birth_date = message.text.strip()

    # Rate limiting убран для birth_date - пользователь может ошибиться при вводе
    # Защита от спама есть на уровне лимита расчетов (2 в день)

    if not validate_date(birth_date):
        await message.answer(MessagesData.ERROR_INVALID_DATE)
        return

    cached_result = user_storage.get_cached_result(user_id)

    # Проверяем, хочет ли пользователь использовать сохраненную дату (точное совпадение)
    if cached_result and cached_result.get("birth_date") == birth_date:
        if user_storage.can_view_cached_result(user_id):
            life_path = cached_result["life_path_result"]
            # Используем сохраненный текст из кэша или генерируем новый
            text = cached_result.get("text")
            if not text:
                text = get_text(life_path, "life_path", user_id)
            result_text = get_format_life_path_result(life_path, text, birth_date)
            await message.answer(result_text, reply_markup=get_result_keyboard())
            user_storage.increment_repeat_view(user_id)
            await state.clear()
            return
        else:
            await message.answer(
                MessagesData.ERROR_VIEW_LIMIT_EXCEEDED, reply_markup=get_back_to_main_keyboard()
            )
            await state.clear()
            return

    # Если дата новая, сохраняем и рассчитываем
    user_storage.set_birth_date(user_id, birth_date)
    life_path = calculate_life_path_number(birth_date)
    soul_number = calculate_soul_number(birth_date)

    # Генерируем текст ОДИН раз и сохраняем в кэш
    text = get_text(life_path, "life_path", user_id)
    user_storage.save_daily_result(user_id, birth_date, life_path, soul_number, text)

    result_text = f"🔮 ВАШЕ ЧИСЛО СУДЬБЫ: {life_path}\n{text}\n📅 Дата: {birth_date}"
    await message.answer(result_text, reply_markup=get_result_keyboard())
    await state.clear()


# ===========================
# Профиль и инфо
# ===========================


@router.message(F.text == TextCommandsData.PROFILE)
@catch_errors()
async def profile_command(message: Message):
    user_id = message.from_user.id
    user_data = user_storage.get_user(user_id)
    usage_stats = user_storage.get_usage_stats(user_id)
    subscription_status = "Premium" if user_data["subscription"]["active"] else "Бесплатный"
    cached_result = user_storage.get_cached_result(user_id)
    has_cached = cached_result is not None
    profile_text = get_profile_text(
        user_id=user_id,
        life_path_number=user_data.get("life_path_number", "не рассчитано"),
        subscription_status=subscription_status,
        usage_stats=usage_stats,
        has_cached=bool(has_cached),
    )
    has_calculated = user_data.get("birth_date") is not None
    await message.answer(profile_text, reply_markup=get_profile_keyboard(has_calculated))


@router.message(F.text == TextCommandsData.ABOUT)
@catch_errors()
async def about_command(message: Message):
    await message.answer(MessagesData.ABOUT_DESCRIPTION, reply_markup=get_about_keyboard())


@router.message(Command(CommandsData.MENU))
@catch_errors()
async def menu_command(message: Message):
    await message.answer(MessagesData.MAIN_MENU, reply_markup=get_main_menu_keyboard())


@router.message(Command(CommandsData.HELP))
@catch_errors()
async def help_command(message: Message):
    await message.answer(MessagesData.HELP)


@router.message()
@catch_errors()
async def unknown_message(message: Message):
    await message.answer(MessagesData.UNKNOWN)


@router.message(Command(CommandsData.PREMIUM_INFO))
@catch_errors()
async def premium_info_command(message: Message):
    await message.answer(MessagesData.PREMIUM_INFO_TEXT, reply_markup=get_premium_info_keyboard())
