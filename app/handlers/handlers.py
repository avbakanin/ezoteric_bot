"""
Обработчики команд и сообщений бота через роутер
"""

import json
import logging
import random
from datetime import datetime

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from calculations import calculate_life_path_number, calculate_soul_number, validate_date
from decorators import catch_errors
from keyboards import (
    get_about_keyboard,
    get_back_to_main_keyboard,
    get_compatibility_result_keyboard,
    get_feedback_keyboard,
    get_main_menu_keyboard,
    get_premium_info_keyboard,
    get_profile_keyboard,
    get_result_keyboard,
)
from messages import (
    MESSAGES,
    get_format_birth_date_prompt,
    get_format_life_path_result,
    get_profile_text,
)
from security import security_validator
from state import UserStates
from storage import user_storage

logger = logging.getLogger(__name__)

router = Router()

# Кэш для текстов чисел
_number_texts_cache = None


def get_number_texts():
    """
    Получает тексты чисел с кэшированием
    """
    global _number_texts_cache
    if _number_texts_cache is None:
        try:
            with open("numbers.json", "r", encoding="utf-8") as f:
                _number_texts_cache = json.load(f)
        except FileNotFoundError:
            logger.error("Файл numbers.json не найден")
            _number_texts_cache = {}
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга numbers.json: {e}")
            _number_texts_cache = {}
    return _number_texts_cache


def get_text(number: int, context: str, user_id: int) -> str:
    """
    Получает текст для числа с учетом истории показанных текстов
    """
    try:
        number_texts = get_number_texts()

        if str(number) not in number_texts:
            logger.warning(f"Нет текстов для числа {number}")
            return "Информация для этого числа временно недоступна."

        if context not in number_texts[str(number)]:
            logger.warning(f"Нет контекста '{context}' для числа {number}")
            return "Информация для этого числа временно недоступна."

        options = number_texts[str(number)][context]
        if not options:
            logger.warning(f"Пустой список текстов для числа {number}, контекст {context}")
            return "Информация для этого числа временно недоступна."

        shown = user_storage.get_text_history(user_id)

        # Исключаем тексты, которые уже показывали
        unused = [t for t in options if t not in shown]

        # Если все тексты показаны, очищаем историю и используем все варианты
        if not unused:
            unused = options
            user_storage.update_user(user_id, text_history=[])
            shown = []

        # Выбираем случайный текст из неиспользованных
        chosen = random.choice(unused)
        user_storage.add_text_to_history(user_id, chosen)

        return chosen

    except Exception as e:
        logger.error(f"Ошибка в get_text: {e}")
        return "Произошла ошибка при получении текста. Попробуйте позже."


# ===========================
# Основные команды
# ===========================


@router.message(Command("start"))
@catch_errors("Ошибка при запуске бота.")
async def start_command(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запустил бота")

    await message.answer(MESSAGES["START"], reply_markup=get_main_menu_keyboard())


@router.message(lambda m: m.text == "🧮 Рассчитать Число Судьбы")
@catch_errors()
async def calculate_number_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запросил расчет числа судьбы")

    user_data = user_storage.get_user(user_id)
    saved_birth_date = user_data.get("birth_date")
    cached_result = user_storage.get_cached_result(user_id)

    if saved_birth_date and cached_result and cached_result.get("birth_date") == saved_birth_date:
        if user_storage.can_view_cached_result(user_id):
            life_path = cached_result["life_path_result"]
            text = get_text(life_path, "life_path", user_id)
            result_text = get_format_life_path_result(life_path, text, saved_birth_date)

            await message.answer(result_text, reply_markup=get_result_keyboard())
            user_storage.increment_repeat_view(user_id)
            return
        else:
            await message.answer(
                MESSAGES["ERROR_VIEW_LIMIT_EXCEEDED"],
                reply_markup=get_back_to_main_keyboard(),
            )
            return

    if not user_storage.can_make_request(user_id):
        await message.answer(
            MESSAGES["ERROR_LIMIT_EXCEEDED"],
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    if saved_birth_date:
        message_text = get_format_birth_date_prompt(saved_birth_date)
    else:
        message_text = MESSAGES["BIRTH_DATE_PROMPT"]

    await message.answer(message_text, reply_markup=get_back_to_main_keyboard())
    await state.set_state(UserStates.waiting_for_birth_date)


@router.message(UserStates.waiting_for_birth_date)
@catch_errors()
async def handle_birth_date(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    birth_date = message.text.strip()
    logger.info(f"Пользователь {user_id} ввел дату рождения: {birth_date}")

    # rate limit и валидация
    if not security_validator.rate_limit_check(user_id, "birth_date", limit=5, window=300):
        await message.answer(
            MESSAGES["RATE_LIMIT_BIRTH_DATE_MSG"], reply_markup=get_back_to_main_keyboard()
        )
        return
    if not validate_date(birth_date):
        await message.answer(MESSAGES["ERROR_INVALID_DATE"])
        return

    cached_result = user_storage.get_cached_result(user_id)
    if cached_result and cached_result.get("birth_date") == birth_date:
        if user_storage.can_view_cached_result(user_id):
            life_path = cached_result["life_path_result"]
            text = get_text(life_path, "life_path", user_id)
            await message.answer(
                f"🔮 ВАШЕ ЧИСЛО СУДЬБЫ: {life_path}\n\n{text}\n\n📋 Это результат из кэша",
                reply_markup=get_result_keyboard(),
            )
            user_storage.increment_repeat_view(user_id)
            await state.clear()
            return
        else:
            await message.answer(
                MESSAGES["ERROR_VIEW_LIMIT_EXCEEDED"],
                reply_markup=get_back_to_main_keyboard(),
            )
            return

    user_data = user_storage.get_user(user_id)
    if user_data.get("birth_date") != birth_date:
        user_storage.set_birth_date(user_id, birth_date)

    life_path = calculate_life_path_number(birth_date)
    soul_number = calculate_soul_number(birth_date)
    user_storage.save_daily_result(user_id, birth_date, life_path, soul_number)
    user_storage.increment_usage(user_id, "daily")

    text = get_text(life_path, "life_path", user_id)
    date_status = "новая дата" if user_data.get("birth_date") != birth_date else "сохраненная дата"
    result_text = (
        f"🔮 ВАШЕ ЧИСЛО СУДЬБЫ: {life_path}\n\n{text}\n\n📅 Дата: {birth_date} ({date_status})"
    )
    await message.answer(result_text, reply_markup=get_result_keyboard())
    await state.clear()


# ===========================
# Совместимость
# ===========================


@router.message(lambda m: m.text == "💑 Проверить Совместимость")
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
        await message.answer(MESSAGES["ERROR_INVALID_DATE"])
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
        await message.answer(MESSAGES["ERROR_INVALID_DATE"])
        return
    data = await state.get_data()
    first_date = data.get("first_date")
    first_number = calculate_life_path_number(first_date)
    second_number = calculate_life_path_number(second_date)

    # Простая совместимость
    compatibility_score = abs(first_number - second_number)
    if compatibility_score == 0:
        score = 9
        description = "Идеальная совместимость! Вы очень похожи по характеру."
    elif compatibility_score <= 2:
        score = 7
        description = "Хорошая совместимость. Вы дополняете друг друга."
    elif compatibility_score <= 4:
        score = 5
        description = "Средняя совместимость. Требуется понимание и компромиссы."
    else:
        score = 3
        description = "Низкая совместимость. Потребуется много усилий."

    result_text = (
        f"💑 СОВМЕСТИМОСТЬ: {first_number} и {second_number}\n\nОценка: {score}/9\n\n{description}"
    )
    await message.answer(result_text, reply_markup=get_compatibility_result_keyboard())
    await state.clear()


# ===========================
# Профиль и инфо
# ===========================


@router.message(lambda m: m.text == "📊 Мой Профиль")
@catch_errors()
async def profile_command(message: types.Message):
    user_id = message.from_user.id
    user_data = user_storage.get_user(user_id)
    birth_date = user_data.get("birth_date", "не указана")
    life_path_number = user_data.get("life_path_number", "не рассчитано")
    usage_stats = user_storage.get_usage_stats(user_id)
    subscription_status = "Premium" if user_data["subscription"]["active"] else "Бесплатный"
    cached_result = user_storage.get_cached_result(user_id)
    has_cached = cached_result is not None

    profile_text = get_profile_text(
        user_id=user_id,
        life_path_number=life_path_number,
        subscription_status=subscription_status,
        usage_stats=usage_stats,
        has_cached=bool(has_cached),
    )
    has_calculated = birth_date != "не указана"
    await message.answer(profile_text, reply_markup=get_profile_keyboard(has_calculated))


@router.message(lambda m: m.text == "ℹ️ О боте")
@catch_errors()
async def about_command(message: types.Message):
    await message.answer(MESSAGES["ABOUT_DESCRIPTION"], reply_markup=get_about_keyboard())


@router.message(Command("menu"))
@catch_errors()
async def menu_command(message: types.Message):
    await message.answer("🔮 Главное меню", reply_markup=get_main_menu_keyboard())


@router.message(Command("premium_info"))
@catch_errors()
async def premium_info_command(message: types.Message):
    await message.answer(MESSAGES["PREMIUM_INFO_TEXT"], reply_markup=get_premium_info_keyboard())


@router.message(Command("feedback"))
@catch_errors()
async def feedback_command(message: types.Message, state: FSMContext):
    await message.answer(
        "📝 ОТЗЫВЫ И ПРЕДЛОЖЕНИЯ\nВаше мнение очень важно!", reply_markup=get_feedback_keyboard()
    )
    await state.set_state(UserStates.waiting_for_feedback)


@router.message(UserStates.waiting_for_feedback)
@catch_errors()
async def handle_feedback(message: types.Message, state: FSMContext):
    feedback_text = message.text.strip()
    user_id = message.from_user.id

    if not security_validator.rate_limit_check(user_id, "feedback", limit=3, window=3600):
        await message.answer(
            "⏰ Слишком много отзывов. Подождите час.", reply_markup=get_back_to_main_keyboard()
        )
        await state.clear()
        return

    sanitized_text = security_validator.sanitize_text(feedback_text)
    # Сохранение в базу или отправка админу
    await message.answer("✅ Спасибо за ваш отзыв!", reply_markup=get_back_to_main_keyboard())
    await state.clear()


# ===========================
# Дневник наблюдений
# ===========================


@router.message(UserStates.waiting_for_diary_observation)
@catch_errors()
async def handle_diary_observation(message: types.Message, state: FSMContext):
    observation_text = message.text.strip()
    user_id = message.from_user.id

    if not security_validator.rate_limit_check(user_id, "diary", limit=10, window=3600):
        await message.answer(
            "⏰ Слишком много записей в дневник. Подождите час.",
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

    await message.answer(
        f"📝 Наблюдение сохранено!\nВаше число судьбы: {observation['number']}\nДата: {observation['date']}",
        reply_markup=get_back_to_main_keyboard(),
    )
    await state.clear()


# ===========================
# Помощь и неизвестные сообщения
# ===========================


@router.message(Command("help"))
@catch_errors()
async def help_command(message: types.Message):
    await message.answer(MESSAGES["HELP"])


@router.message()
@catch_errors()
async def unknown_message(message: types.Message):
    await message.answer(MESSAGES["UNKNOWN"])
