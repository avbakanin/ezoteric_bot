"""
Клавиатуры для бота
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает главное меню бота (MVP структура)
    """
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        keyboard=[
            [KeyboardButton("🧮 Рассчитать Число Судьбы")],
            [KeyboardButton("💑 Проверить Совместимость")],
            [KeyboardButton("📊 Мой Профиль"), KeyboardButton("ℹ️ О боте")]
        ]
    )
    return keyboard


def get_result_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для результата расчета
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🔒 Полная расшифровка (Премиум)", callback_data="premium_full")],
            [InlineKeyboardButton("↩️ В главное меню", callback_data="back_main")]
        ]
    )
    return keyboard


def get_compatibility_result_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для результата совместимости
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🔒 Детальный разбор (Премиум)", callback_data="premium_compatibility")],
            [InlineKeyboardButton("↩️ В главное меню", callback_data="back_main")]
        ]
    )
    return keyboard


def get_profile_keyboard(has_calculated: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для профиля пользователя
    """
    if has_calculated:
        button_text = "🔄 Рассчитать заново"
        callback_data = "recalculate"
    else:
        button_text = "🧮 Рассчитать моё число"
        callback_data = "calculate_number"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(button_text, callback_data=callback_data)],
            [InlineKeyboardButton("↩️ В главное меню", callback_data="back_main")]
        ]
    )
    return keyboard


def get_about_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для страницы "О боте"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("💎 Узнать о Premium", callback_data="premium_info")],
            [InlineKeyboardButton("📝 Оставить отзыв", callback_data="feedback")],
            [InlineKeyboardButton("📔 Дневник наблюдений", callback_data="diary_observation")],
            [InlineKeyboardButton("↩️ В главное меню", callback_data="back_main")]
        ]
    )
    return keyboard


def get_premium_info_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для информации о Premium
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("💎 Оформить Premium", callback_data="subscribe")],
            [InlineKeyboardButton("📋 Что входит в Premium", callback_data="premium_features")],
            [InlineKeyboardButton("↩️ Назад", callback_data="back_about")]
        ]
    )
    return keyboard


def get_feedback_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для отзывов
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("⭐ Оставить отзыв", callback_data="leave_feedback")],
            [InlineKeyboardButton("💬 Предложение", callback_data="suggestion")],
            [InlineKeyboardButton("🐛 Сообщить об ошибке", callback_data="report_bug")],
            [InlineKeyboardButton("↩️ Назад", callback_data="back_about")]
        ]
    )
    return keyboard


def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """
    Создает простую клавиатуру с кнопкой "В главное меню"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("↩️ В главное меню", callback_data="back_main")]
        ]
    )
    return keyboard


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками "Да" и "Нет"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("✅ Да", callback_data="yes"), 
             InlineKeyboardButton("❌ Нет", callback_data="no")]
        ]
    )
    return keyboard