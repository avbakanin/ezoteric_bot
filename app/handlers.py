"""
Обработчики команд и сообщений бота с поддержкой FSM и UserStorage
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from calculations import calculate_daily_number, calculate_life_path_number, calculate_soul_number
from decorators import error_handler
from messages import MESSAGES

from app.user_storage import user_storage

logger = logging.getLogger(__name__)
router = Router()


class UserStates(StatesGroup):
    """Состояния пользователя для FSM"""

    waiting_for_birth_date = State()
    waiting_for_other_date = State()


# ------------------- Обработчики команд -------------------


@router.message(Command("start"))
@error_handler(MESSAGES.ERROR_START)
async def start_command(message: Message):
    user_id = message.from_user.id
    user_storage.get_user(user_id)  # инициализация пользователя
    await message.answer(MESSAGES.START)


@router.message(Command("help"))
async def help_command(message: Message):
    await message.answer(MESSAGES.HELP)


@router.message(Command("subscription"))
async def subscription_command(message: Message):
    user_id = message.from_user.id
    subscription = user_storage.get_user(user_id).get("subscription", {})

    if subscription.get("active"):
        expires = subscription.get("expires", "неизвестно")
        sub_type = subscription.get("type", "standard")
        await message.answer(f"✅ У тебя активная подписка ({sub_type}), действует до: {expires}")
    else:
        await message.answer("❌ У тебя нет активной подписки. Доступ ограничен.")


# ------------------- Путь жизни -------------------


@router.message(Command("life_path"))
@error_handler(MESSAGES.ERROR_LIFE_PATH)
async def life_path_command(message: Message):
    user_id = message.from_user.id

    if not user_storage.can_make_request(user_id):
        await message.answer(MESSAGES.LIMIT_REACHED)
        return

    cache = user_storage.get_cached_result(user_id)
    if cache and cache.get("life_path_result") and user_storage.can_view_cached_result(user_id):
        user_storage.increment_repeat_view(user_id)
        await message.answer(f"♻️ Сегодняшний результат:\n{cache['life_path_result']}")
        return

    birth_date = user_storage.get_user(user_id).get("birth_date")
    if not birth_date:
        await message.answer(MESSAGES.NO_BIRTHDATE)
        await message.answer("Введите дату рождения в формате ДД.MM.ГГГГ")
        await message.bot.set_state(user_id, UserStates.waiting_for_birth_date)
        return

    await calculate_and_send_life_path(user_id, message)


async def calculate_and_send_life_path(user_id: int, message: Message):
    birth_date = user_storage.get_user(user_id).get("birth_date")
    life_path = calculate_life_path_number(birth_date)
    soul_number = calculate_soul_number(birth_date)

    user_storage.save_daily_result(user_id, birth_date, life_path, soul_number)
    user_storage.increment_usage(user_id, "daily")

    await message.answer(f"🌟 Твой путь жизни: {life_path}")


@router.message(UserStates.waiting_for_birth_date)
async def input_birth_date(message: Message, state: FSMContext):
    user_id = message.from_user.id
    birth_date = message.text.strip()

    if not birth_date or not birth_date.count(".") == 2:
        await message.answer(MESSAGES.INVALID_DATE)
        return

    try:
        user_storage.set_birth_date(user_id, birth_date)
    except Exception:
        await message.answer(MESSAGES.INVALID_DATE)
        return

    await state.clear()
    await calculate_and_send_life_path(user_id, message)


# ------------------- Совместимость -------------------


@router.message(Command("compatibility"))
@error_handler(MESSAGES.ERROR_COMPATIBILITY)
async def compatibility_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not user_storage.can_check_compatibility(user_id):
        await message.answer(MESSAGES.COMPATIBILITY_LIMIT)
        return

    birth_date = user_storage.get_user(user_id).get("birth_date")
    if not birth_date:
        await message.answer(MESSAGES.NO_BIRTHDATE)
        await state.set_state(UserStates.waiting_for_birth_date)
        return

    await message.answer("Введите дату рождения другого человека (ДД.MM.ГГГГ):")
    await state.set_state(UserStates.waiting_for_other_date)


@router.message(UserStates.waiting_for_other_date)
async def input_other_birth_date(message: Message, state: FSMContext):
    user_id = message.from_user.id
    other_date = message.text.strip()

    birth_date = user_storage.get_user(user_id).get("birth_date")
    if not birth_date:
        await message.answer(MESSAGES.NO_BIRTHDATE)
        await state.clear()
        return

    try:
        score = calculate_life_path_number(birth_date)  # упрощаем: число судьбы
        other_number = calculate_life_path_number(other_date)
        compatibility = 9 - abs(score - other_number)  # простая метрика совместимости
    except Exception:
        await message.answer(MESSAGES.INVALID_DATE)
        await state.clear()
        return

    user_storage.increment_usage(user_id, "compatibility")
    await message.answer(f"💞 Совместимость: {compatibility}/9")
    await state.clear()


# ------------------- Аффирмации -------------------


@router.message(Command("affirmation"))
@error_handler(MESSAGES.ERROR_AFFIRMATION)
async def affirmation_command(message: Message):
    user_id = message.from_user.id

    todays_aff = user_storage.get_todays_affirmation(user_id)
    if todays_aff:
        await message.answer(f"✨ Твоя аффирмация:\n{todays_aff['text']}")
        return

    number, text = get_random_affirmation()
    user_storage.set_todays_affirmation(user_id, text, number)
    await message.answer(f"✨ Твоя новая аффирмация:\n{text}")


# ------------------- Ежедневное число -------------------


@router.message(Command("daily"))
@error_handler(MESSAGES.ERROR_DAILY_NUMBER)
async def daily_number_command(message: Message):
    user_id = message.from_user.id

    if not user_storage.can_make_request(user_id):
        await message.answer(MESSAGES.LIMIT_REACHED)
        return

    cache = user_storage.get_cached_result(user_id)
    if cache and cache.get("daily_number_result") and user_storage.can_view_cached_result(user_id):
        user_storage.increment_repeat_view(user_id)
        await message.answer(f"♻️ Твое число дня:\n{cache['daily_number_result']}")
        return

    birth_date = user_storage.get_user(user_id).get("birth_date")
    if not birth_date:
        await message.answer(MESSAGES.NO_BIRTHDATE)
        return

    daily_num = calculate_daily_number(birth_date)
    cache_data = user_storage.get_cached_result(user_id) or {}
    cache_data["daily_number_result"] = daily_num
    user_storage.data[str(user_id)]["daily_cache"].update(cache_data)
    user_storage.increment_usage(user_id, "daily")

    await message.answer(f"🔮 Твое число дня: {daily_num}")


# ------------------- Установка даты рождения вручную -------------------


@router.message(Command("set_birthdate"))
@error_handler(MESSAGES.ERROR_SET_BIRTHDATE)
async def set_birthdate_command(message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        await message.answer(MESSAGES.NO_DATE_PROVIDED)
        return

    birth_date = args[1]
    try:
        user_storage.set_birth_date(user_id, birth_date)
    except Exception:
        await message.answer(MESSAGES.INVALID_DATE)
        return

    await message.answer(MESSAGES.BIRTHDATE_SAVED.format(birth_date=birth_date))
