"""
Категоризированные меню для навигации по функциям бота.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from ..messages import TextCommandsData


def get_main_menu_keyboard_categorized() -> ReplyKeyboardMarkup:
    """
    Создает упрощенное главное меню с категориями функций.
    """
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        keyboard=[
            [
                KeyboardButton(text="🧮 Нумерология"),
                KeyboardButton(text="🌌 Астрология"),
            ],
            [
                KeyboardButton(text="🔮 Практики"),
                KeyboardButton(text="📊 Профиль"),
            ],
            [
                KeyboardButton(text=TextCommandsData.ABOUT),
            ],
        ],
    )
    return keyboard


def get_numerology_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Подменю категории "Нумерология"
    Используем Reply-кнопки, чтобы они работали как обычные текстовые команды
    """
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        keyboard=[
            [
                KeyboardButton(text=TextCommandsData.LIFE_PATH_NUMBER),
                KeyboardButton(text=TextCommandsData.NAME_NUMBER),
            ],
            [
                KeyboardButton(text=TextCommandsData.COMPATIBILITY),
                KeyboardButton(text=TextCommandsData.DAILY_NUMBER),
            ],
            [
                KeyboardButton(text="↩️ В главное меню"),
            ],
        ],
    )
    return keyboard


def get_astrology_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Подменю категории "Астрология"
    """
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        keyboard=[
            [
                KeyboardButton(text=TextCommandsData.NATAL_CHART),
                KeyboardButton(text=TextCommandsData.ASPECT_OF_DAY),
            ],
            [
                KeyboardButton(text=TextCommandsData.LUNAR_PLANNER),
                KeyboardButton(text=TextCommandsData.RETRO_ALERTS),
            ],
            [
                KeyboardButton(text=TextCommandsData.NATAL_CHART_HISTORY),
            ],
            [
                KeyboardButton(text="↩️ В главное меню"),
            ],
        ],
    )
    return keyboard


def get_practices_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Подменю категории "Практики"
    """
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        keyboard=[
            [
                KeyboardButton(text=TextCommandsData.TAROT),
                KeyboardButton(text=TextCommandsData.YES_NO),
            ],
            [
                KeyboardButton(text=TextCommandsData.DIARY_OBSERVATION),
            ],
            [
                KeyboardButton(text="↩️ В главное меню"),
            ],
        ],
    )
    return keyboard


def get_profile_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Подменю категории "Профиль"
    """
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        keyboard=[
            [
                KeyboardButton(text=TextCommandsData.PROFILE),
                KeyboardButton(text=TextCommandsData.PREMIUM),
            ],
            [
                KeyboardButton(text=TextCommandsData.FEEDBACK),
            ],
            [
                KeyboardButton(text="↩️ В главное меню"),
            ],
        ],
    )
    return keyboard


def get_category_description_text(category: str) -> str:
    """
    Возвращает описание категории для пользователя.
    """
    descriptions = {
        "🧮 Нумерология": (
            "🧮 НУМЕРОЛОГИЯ\n\n"
            "Работа с числами и их влиянием на вашу жизнь:\n\n"
            "• 🧮 Число Судьбы — ваш основной жизненный путь\n"
            "• 🔤 Число Имени — энергия вашего имени\n"
            "• 💑 Совместимость — анализ совместимости двух людей\n"
            "• 🌞 Число Дня — персональный прогноз на сегодня (Premium)\n\n"
            "Выберите функцию:"
        ),
        "🌌 Астрология": (
            "🌌 АСТРОЛОГИЯ\n\n"
            "Астрологические прогнозы и рекомендации:\n\n"
            "• 🌌 Натальная карта — ваш персональный гороскоп дня\n"
            "• 🌟 Аспект дня — главный транзит сегодня\n"
            "• 🌙 Планировщик — идеи дел по фазам Луны\n"
            "• ♻️ Ретро — оповещения о ретроградных планетах\n"
            "• 🕰 История — архив натальных карт (Premium)\n\n"
            "Выберите функцию:"
        ),
        "🔮 Практики": (
            "🔮 ПРАКТИКИ\n\n"
            "Интуитивные инструменты для самопознания:\n\n"
            "• 🔮 Таро — гадания на картах Таро\n"
            "• 🔮 Да/Нет — быстрые ответы на вопросы\n"
            "• 📔 Дневник — записи наблюдений за жизнью\n\n"
            "Выберите функцию:"
        ),
        "📊 Профиль": (
            "📊 ПРОФИЛЬ\n\n"
            "Управление аккаунтом и подписка:\n\n"
            "• 📊 Профиль — ваши данные и настройки\n"
            "• 💎 Premium — расширенные возможности\n"
            "• 📝 Отзыв — обратная связь и предложения\n\n"
            "Выберите функцию:"
        ),
    }
    return descriptions.get(category, "Выберите функцию:")

