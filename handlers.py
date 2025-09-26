"""
Обработчики команд и сообщений бота
"""

import json
import logging
import random
from datetime import datetime
from typing import Optional

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from calculations import (
    calculate_life_path_number, 
    calculate_soul_number, 
    calculate_daily_number,
    validate_date
)
from keyboards import (
    get_main_menu_keyboard,
    get_result_keyboard,
    get_compatibility_result_keyboard,
    get_profile_keyboard,
    get_about_keyboard,
    get_premium_info_keyboard,
    get_feedback_keyboard,
    get_back_to_main_keyboard,
    get_yes_no_keyboard
)
from storage import user_storage
from security import security_validator

logger = logging.getLogger(__name__)


class UserStates(StatesGroup):
    """
    Состояния пользователя для FSM
    """
    waiting_for_birth_date = State()
    waiting_for_first_date = State()
    waiting_for_second_date = State()
    waiting_for_feedback = State()
    waiting_for_diary_observation = State()


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


async def start_command(message: types.Message):
    """
    Обработчик команды /start
    """
    try:
        user_id = message.from_user.id
        user_data = user_storage.get_user(user_id)
        
        logger.info(f"Пользователь {user_id} запустил бота")
        
        welcome_text = (
            "🔮 Добро пожаловать в нумерологический бот!\n\n"
            "Это ваш личный помощник в мире чисел и энергий.\n\n"
            "✨ БЕСПЛАТНО:\n"
            "• Рассчитайте ваше Число Судьбы\n"
            "• Проверьте совместимость с партнёром\n\n"
            "🚀 PREMIUM (СКОРО):\n"
            "• Полные и детальные расшифровки\n"
            "• Число дня и ежедневные прогнозы\n"
            "• Анализ сильных сторон и кармических задач\n\n"
            "Используйте кнопки ниже, чтобы начать!"
        )
        
        await message.answer(welcome_text, reply_markup=get_main_menu_keyboard())
        
    except Exception as e:
        logger.error(f"Ошибка в start_command: {e}")
        await message.answer(
            "Произошла ошибка при запуске бота. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )


async def calculate_number_command(message: types.Message, state: FSMContext):
    """
    Обработчик команды "🧮 Рассчитать Число Судьбы"
    """
    try:
        user_id = message.from_user.id
        logger.info(f"Пользователь {user_id} запросил расчет числа судьбы")
        
        await message.answer(
            "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\n"
            "(например, 15.05.1990)",
            reply_markup=get_back_to_main_keyboard()
        )
        await state.set_state(UserStates.waiting_for_birth_date)
        
    except Exception as e:
        logger.error(f"Ошибка в calculate_number_command: {e}")
        await message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_back_to_main_keyboard()
        )


async def handle_birth_date(message: types.Message, state: FSMContext):
    """
    Обработчик ввода даты рождения
    """
    try:
        user_id = message.from_user.id
        birth_date = message.text.strip()
        
        logger.info(f"Пользователь {user_id} ввел дату рождения: {birth_date}")
        
        # Проверяем rate limit
        if not security_validator.rate_limit_check(user_id, "birth_date", limit=5, window=300):
            await message.answer(
                "⏰ Слишком много запросов. Подождите 5 минут и попробуйте снова.",
                reply_markup=get_back_to_main_keyboard()
            )
            return
        
        # Валидируем ввод
        if not security_validator.validate_user_input(birth_date, max_length=20):
            await message.answer(
                "❌ Некорректный ввод. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ",
                reply_markup=get_back_to_main_keyboard()
            )
            return
        
        if not validate_date(birth_date):
            await message.answer(
                "❌ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n"
                "Например: 15.03.1990"
            )
        return
    
        # Сохраняем дату рождения
        user_storage.set_birth_date(user_id, birth_date)
        
        # Вычисляем число судьбы
        life_path = calculate_life_path_number(birth_date)
        text = get_text(life_path, "life_path", user_id)
        
        result_text = (
            f"🔮 ВАШЕ ЧИСЛО СУДЬБЫ: {life_path}\n\n"
            f"{text}"
        )
        
        await message.answer(result_text, reply_markup=get_result_keyboard())
        await state.clear()
        
        logger.info(f"Число судьбы {life_path} рассчитано для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_birth_date: {e}")
        await message.answer(
            "Произошла ошибка при обработке даты рождения. Попробуйте позже.",
            reply_markup=get_back_to_main_keyboard()
        )
        await state.clear()


async def compatibility_command(message: types.Message, state: FSMContext):
    """
    Обработчик команды "💑 Проверить Совместимость"
    """
    await message.answer(
        "Введите первую дату рождения (ДД.ММ.ГГГГ):",
        reply_markup=get_back_to_main_keyboard()
    )
    await state.set_state(UserStates.waiting_for_first_date)


async def handle_first_date(message: types.Message, state: FSMContext):
    """
    Обработчик ввода первой даты для совместимости
    """
    first_date = message.text.strip()
    
    if not validate_date(first_date):
        await message.answer(
            "❌ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n"
            "Например: 15.03.1990"
        )
        return
    
    # Сохраняем первую дату в состоянии
    await state.update_data(first_date=first_date)
    
    await message.answer(
        "Введите вторую дату рождения (ДД.ММ.ГГГГ):",
        reply_markup=get_back_to_main_keyboard()
    )
    await state.set_state(UserStates.waiting_for_second_date)


async def handle_second_date(message: types.Message, state: FSMContext):
    """
    Обработчик ввода второй даты для совместимости
    """
    second_date = message.text.strip()
    
    if not validate_date(second_date):
        await message.answer(
            "❌ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n"
            "Например: 15.03.1990"
        )
        return
    
    # Получаем первую дату из состояния
    data = await state.get_data()
    first_date = data.get("first_date")
    
    # Вычисляем числа судьбы
    first_number = calculate_life_path_number(first_date)
    second_number = calculate_life_path_number(second_date)
    
    # Простая совместимость
    compatibility_score = abs(first_number - second_number)
    if compatibility_score == 0:
        score = 9
        description = "Идеальная совместимость! Вы очень похожи по характеру и жизненным целям."
    elif compatibility_score <= 2:
        score = 7
        description = "Хорошая совместимость. Вы дополняете друг друга и можете создать гармоничные отношения."
    elif compatibility_score <= 4:
        score = 5
        description = "Средняя совместимость. Вам потребуется больше понимания и компромиссов."
    else:
        score = 3
        description = "Низкая совместимость. Потребуется много усилий для построения отношений."
    
    result_text = (
        f"💑 СОВМЕСТИМОСТЬ: {first_number} и {second_number}\n\n"
        f"Оценка совместимости: {score}/9\n\n"
        f"{description}"
    )
    
    await message.answer(result_text, reply_markup=get_compatibility_result_keyboard())
    await state.finish()


async def profile_command(message: types.Message):
    """
    Обработчик команды "📊 Мой Профиль"
    """
    user_id = message.from_user.id
    user_data = user_storage.get_user(user_id)
    
    birth_date = user_data.get("birth_date", "не указана")
    life_path_number = user_data.get("life_path_number", "не рассчитано")
    
    profile_text = (
        f"📊 ВАШ ПРОФИЛЬ:\n\n"
        f"🆔 Ваш ID: {user_id}\n"
        f"🔢 Ваше Число Судьбы: {life_path_number}\n"
        f"💎 Статус: Бесплатный аккаунт"
    )
    
    has_calculated = birth_date != "не указана"
    await message.answer(profile_text, reply_markup=get_profile_keyboard(has_calculated))


async def about_command(message: types.Message):
    """
    Обработчик команды "ℹ️ О боте"
    """
    about_text = (
        "Это нумерологический бот — ваш личный помощник в мире чисел!\n\n"
        "✨ БЕСПЛАТНО:\n"
        "• Рассчитайте ваше Число Судьбы\n"
        "• Проверьте совместимость с партнёром\n\n"
        "🚀 PREMIUM (СКОРО):\n"
        "• Полные и детальные расшифровки\n"
        "• Число дня и ежедневные прогнозы\n"
        "• Анализ сильных сторон и кармических задач\n\n"
        "Используйте кнопки ниже, чтобы начать!"
    )
    
    await message.answer(about_text, reply_markup=get_about_keyboard())


async def menu_command(message: types.Message):
    """
    Обработчик команды /menu
    """
    await message.answer(
        "🔮 Главное меню",
        reply_markup=get_main_menu_keyboard()
    )


async def premium_info_command(message: types.Message):
    """
    Обработчик команды /premium_info
    """
    premium_text = (
        "💎 PREMIUM ПОДПИСКА\n\n"
        "🚀 Что входит в Premium:\n"
        "• Полные и детальные расшифровки чисел\n"
        "• Число дня и ежедневные прогнозы\n"
        "• Анализ сильных сторон и кармических задач\n"
        "• Персональные рекомендации\n"
        "• Приоритетная поддержка\n\n"
        "💰 Стоимость: 299₽/месяц\n\n"
        "Скоро будет доступно!"
    )
    
    await message.answer(premium_text, reply_markup=get_premium_info_keyboard())


async def feedback_command(message: types.Message):
    """
    Обработчик команды /feedback
    """
    feedback_text = (
        "📝 ОТЗЫВЫ И ПРЕДЛОЖЕНИЯ\n\n"
        "Ваше мнение очень важно для нас!\n"
        "Поделитесь своими мыслями о боте:"
    )
    
    await message.answer(feedback_text, reply_markup=get_feedback_keyboard())


async def handle_callback_query(callback_query: CallbackQuery):
    """
    Обработчик callback запросов
    """
    await callback_query.answer()
    
    if callback_query.data == "back_main":
        await callback_query.message.edit_text(
            "🔮 Главное меню"
        )
        await callback_query.message.answer(
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
    elif callback_query.data == "back_about":
        await callback_query.message.edit_text(
            "Это нумерологический бот — ваш личный помощник в мире чисел!\n\n"
            "✨ БЕСПЛАТНО:\n"
            "• Рассчитайте ваше Число Судьбы\n"
            "• Проверьте совместимость с партнёром\n\n"
            "🚀 PREMIUM (СКОРО):\n"
            "• Полные и детальные расшифровки\n"
            "• Число дня и ежедневные прогнозы\n"
            "• Анализ сильных сторон и кармических задач\n\n"
            "Используйте кнопки ниже, чтобы начать!",
            reply_markup=get_about_keyboard()
        )
    elif callback_query.data == "premium_full":
        await callback_query.message.edit_text(
            "🔒 ПОЛНАЯ РАСШИФРОВКА (PREMIUM)\n\n"
            "Эта функция доступна только в Premium подписке.\n\n"
            "В полной расшифровке вы получите:\n"
            "• Детальный анализ вашего числа судьбы\n"
            "• Кармические задачи и уроки\n"
            "• Рекомендации по развитию\n"
            "• Анализ сильных и слабых сторон\n\n"
            "Скоро будет доступно!",
            reply_markup=get_back_to_main_keyboard()
        )
    elif callback_query.data == "premium_compatibility":
        await callback_query.message.edit_text(
            "🔒 ДЕТАЛЬНЫЙ РАЗБОР СОВМЕСТИМОСТИ (PREMIUM)\n\n"
            "Эта функция доступна только в Premium подписке.\n\n"
            "В детальном разборе вы получите:\n"
            "• Анализ совместимости по всем аспектам\n"
            "• Рекомендации по улучшению отношений\n"
            "• Потенциальные конфликты и их решения\n"
            "• Советы по развитию партнерства\n\n"
            "Скоро будет доступно!",
            reply_markup=get_back_to_main_keyboard()
        )
    elif callback_query.data == "calculate_number":
        await callback_query.message.edit_text(
            "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\n"
            "(например, 15.05.1990)",
            reply_markup=get_back_to_main_keyboard()
        )
        await state.set_state(UserStates.waiting_for_birth_date)
    elif callback_query.data == "recalculate":
        await callback_query.message.edit_text(
            "Введите вашу дату рождения в формате ДД.ММ.ГГГГ\n"
            "(например, 15.05.1990)",
            reply_markup=get_back_to_main_keyboard()
        )
        await state.set_state(UserStates.waiting_for_birth_date)
    elif callback_query.data == "premium_info":
        await callback_query.message.edit_text(
            "💎 PREMIUM ПОДПИСКА\n\n"
            "🚀 Что входит в Premium:\n"
            "• Полные и детальные расшифровки чисел\n"
            "• Число дня и ежедневные прогнозы\n"
            "• Анализ сильных сторон и кармических задач\n"
            "• Персональные рекомендации\n"
            "• Приоритетная поддержка\n\n"
            "💰 Стоимость: 299₽/месяц\n\n"
            "Скоро будет доступно!",
            reply_markup=get_premium_info_keyboard()
        )
    elif callback_query.data == "premium_features":
        await callback_query.message.edit_text(
            "📋 ЧТО ВХОДИТ В PREMIUM:\n\n"
            "🔮 Полные расшифровки:\n"
            "• Детальный анализ числа судьбы\n"
            "• Кармические задачи и уроки\n"
            "• Рекомендации по развитию\n\n"
            "📅 Ежедневные прогнозы:\n"
            "• Число дня и его влияние\n"
            "• Персональные советы\n"
            "• Автоматические уведомления\n\n"
            "💕 Расширенная совместимость:\n"
            "• Детальный анализ отношений\n"
            "• Рекомендации по улучшению\n"
            "• Потенциальные конфликты\n\n"
            "Скоро будет доступно!",
            reply_markup=get_back_to_main_keyboard()
        )
    elif callback_query.data == "subscribe":
        await callback_query.message.edit_text(
            "💎 ОФОРМЛЕНИЕ PREMIUM ПОДПИСКИ\n\n"
            "Подписка Premium: 299₽/месяц\n\n"
            "Для оформления подписки обратитесь к администратору: @admin\n\n"
            "Скоро будет доступно!",
            reply_markup=get_back_to_main_keyboard()
        )
    elif callback_query.data == "feedback":
        await callback_query.message.edit_text(
            "📝 ОТЗЫВЫ И ПРЕДЛОЖЕНИЯ\n\n"
            "Ваше мнение очень важно для нас!\n"
            "Поделитесь своими мыслями о боте:",
            reply_markup=get_feedback_keyboard()
        )
    elif callback_query.data == "leave_feedback":
        await callback_query.message.edit_text(
            "⭐ ОСТАВИТЬ ОТЗЫВ\n\n"
            "Напишите ваш отзыв о боте:",
            reply_markup=get_back_to_main_keyboard()
        )
        await state.set_state(UserStates.waiting_for_feedback)
    elif callback_query.data == "suggestion":
        await callback_query.message.edit_text(
            "💬 ПРЕДЛОЖЕНИЕ\n\n"
            "Напишите ваше предложение по улучшению бота:",
            reply_markup=get_back_to_main_keyboard()
        )
        await state.set_state(UserStates.waiting_for_feedback)
    elif callback_query.data == "report_bug":
        await callback_query.message.edit_text(
            "🐛 СООБЩИТЬ ОБ ОШИБКЕ\n\n"
            "Опишите проблему, с которой вы столкнулись:",
            reply_markup=get_back_to_main_keyboard()
        )
        await state.set_state(UserStates.waiting_for_feedback)
    elif callback_query.data == "diary_observation":
        await callback_query.message.edit_text(
            "📔 ДНЕВНИК НАБЛЮДЕНИЙ\n\n"
            "Записывайте свои наблюдения о том, как ваше число судьбы проявляется в жизни.\n"
            "Это поможет лучше понять себя и свой жизненный путь.\n\n"
            "Напишите ваше наблюдение:",
            reply_markup=get_back_to_main_keyboard()
        )
        await state.set_state(UserStates.waiting_for_diary_observation)


async def handle_feedback(message: types.Message, state: FSMContext):
    """
    Обработчик ввода отзыва/предложения
    """
    try:
        feedback_text = message.text.strip()
        user_id = message.from_user.id
        
        logger.info(f"Пользователь {user_id} отправил отзыв")
        
        # Проверяем rate limit
        if not security_validator.rate_limit_check(user_id, "feedback", limit=3, window=3600):
            await message.answer(
                "⏰ Слишком много отзывов. Подождите час и попробуйте снова.",
                reply_markup=get_back_to_main_keyboard()
            )
            await state.clear()
            return
        
        # Валидируем ввод
        if not security_validator.validate_user_input(feedback_text, max_length=2000):
            await message.answer(
                "❌ Некорректный ввод. Пожалуйста, проверьте текст отзыва.",
                reply_markup=get_back_to_main_keyboard()
            )
            await state.clear()
            return
        
        # Очищаем текст
        sanitized_text = security_validator.sanitize_text(feedback_text)
        
        # Здесь можно сохранить отзыв в базу данных или отправить администратору
        # Пока просто подтверждаем получение
        
        await message.answer(
            "✅ Спасибо за ваш отзыв!\n\n"
            "Ваше мнение очень важно для нас. Мы обязательно учтем ваши предложения.",
            reply_markup=get_back_to_main_keyboard()
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_feedback: {e}")
        await message.answer(
            "Произошла ошибка при обработке отзыва. Попробуйте позже.",
            reply_markup=get_back_to_main_keyboard()
        )
        await state.clear()


async def handle_diary_observation(message: types.Message, state: FSMContext):
    """
    Обработчик ввода наблюдения в дневник
    """
    try:
        observation_text = message.text.strip()
        user_id = message.from_user.id
        
        logger.info(f"Пользователь {user_id} добавил наблюдение в дневник")
        
        # Проверяем rate limit
        if not security_validator.rate_limit_check(user_id, "diary", limit=10, window=3600):
            await message.answer(
                "⏰ Слишком много записей в дневник. Подождите час и попробуйте снова.",
                reply_markup=get_back_to_main_keyboard()
            )
            await state.clear()
            return
        
        # Валидируем ввод
        if not security_validator.validate_user_input(observation_text, max_length=2000):
            await message.answer(
                "❌ Некорректный ввод. Пожалуйста, проверьте текст наблюдения.",
                reply_markup=get_back_to_main_keyboard()
            )
            await state.clear()
        return

        # Очищаем текст
        sanitized_text = security_validator.sanitize_text(observation_text)
        
        # Сохраняем наблюдение пользователя
        user_data = user_storage.get_user(user_id)
        if "diary_observations" not in user_data:
            user_data["diary_observations"] = []
        
        # Добавляем новое наблюдение с датой
        observation = {
            "text": sanitized_text,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "number": user_data.get("life_path_number", "неизвестно")
        }
        
        user_data["diary_observations"].append(observation)
        user_storage._save_data()
        
        await message.answer(
            "📝 Наблюдение сохранено!\n\n"
            f"Ваше число судьбы: {observation['number']}\n"
            f"Дата: {observation['date']}\n\n"
            "Продолжайте вести дневник для лучшего понимания себя!",
            reply_markup=get_back_to_main_keyboard()
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка в handle_diary_observation: {e}")
        await message.answer(
            "Произошла ошибка при сохранении наблюдения. Попробуйте позже.",
            reply_markup=get_back_to_main_keyboard()
        )
        await state.clear()


async def help_command(message: types.Message):
    """
    Обработчик команды /help
    """
    help_text = (
        "❓ ПОМОЩЬ\n\n"
        "🔮 Число судьбы — ваш жизненный путь и характер\n"
        "💑 Совместимость — гармония в отношениях\n"
        "📊 Профиль — ваши данные и настройки\n"
        "ℹ️ О боте — информация и отзывы\n\n"
        "Используйте кнопки меню для навигации!"
    )
    
    await message.answer(help_text)


async def unknown_message(message: types.Message):
    """
    Обработчик неизвестных сообщений
    """
    await message.answer(
        "❓ Не понимаю эту команду. Используйте меню или команду /help для справки."
    )