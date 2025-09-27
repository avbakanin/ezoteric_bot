"""
Клавиатуры для бота
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает главное меню бота (MVP структура)
    """
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        keyboard=[
            [KeyboardButton(text="🧮 Рассчитать Число Судьбы")],
            [KeyboardButton(text="💑 Проверить Совместимость")],
            [KeyboardButton(text="✨ Сгенерировать аффирмацию")],
            [KeyboardButton(text="🔮 Гадание Да/Нет")],
            [KeyboardButton(text="📊 Мой Профиль"), KeyboardButton(text="ℹ️ О боте")],
        ],
    )
    return keyboard


def get_result_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для результата расчета
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 Полная расшифровка (Премиум)", callback_data="premium_full"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💑 Проверить совместимость", callback_data="compatibility_from_result"
                )
            ],
            [InlineKeyboardButton(text="✨ Аффирмация на день", callback_data="daily_affirmation")],
            [InlineKeyboardButton(text="📋 Посмотреть снова", callback_data="view_again")],
            [InlineKeyboardButton(text="↩️ В главное меню", callback_data="back_main")],
        ]
    )
    return keyboard


def get_compatibility_result_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для результата совместимости
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 Детальный разбор (Премиум)", callback_data="premium_compatibility"
                )
            ],
            [InlineKeyboardButton(text="↩️ В главное меню", callback_data="back_main")],
        ]
    )
    return keyboard


def get_profile_keyboard(has_calculated: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для профиля пользователя
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧮 Рассчитать число", callback_data="calculate_number")],
            [InlineKeyboardButton(text="↩️ В главное меню", callback_data="back_main")],
        ]
    )
    return keyboard


def get_about_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для страницы "О боте"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Узнать о Premium", callback_data="premium_info")],
            [InlineKeyboardButton(text="📝 Оставить отзыв", callback_data="feedback")],
            [InlineKeyboardButton(text="📔 Дневник наблюдений", callback_data="diary_observation")],
            [InlineKeyboardButton(text="↩️ В главное меню", callback_data="back_main")],
        ]
    )
    return keyboard


def get_premium_info_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для информации о Premium
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Оформить Premium", callback_data="subscribe")],
            [InlineKeyboardButton(text="📋 Что входит в Premium", callback_data="premium_features")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back_about")],
        ]
    )
    return keyboard


def get_feedback_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для отзывов
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="leave_feedback")],
            [InlineKeyboardButton(text="💬 Предложение", callback_data="suggestion")],
            [InlineKeyboardButton(text="🐛 Сообщить об ошибке", callback_data="report_bug")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back_about")],
        ]
    )
    return keyboard


def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """
    Создает простую клавиатуру с кнопкой "В главное меню"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="↩️ В главное меню", callback_data="back_main")]]
    )
    return keyboard


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками "Да" и "Нет"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="no"),
            ]
        ]
    )
    return keyboard


def get_affirmations_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌅 Аффирмация на сегодня")],
            [KeyboardButton(text="📖 Мои аффирмации")],
            [KeyboardButton(text="✨ Случайная аффирмация")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )


def get_affirmation_action_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💾 Сохранить в историю")],
            [KeyboardButton(text="🔄 Другая аффирмация")],
            [KeyboardButton(text="📖 Все аффирмации")],
            [KeyboardButton(text="🔙 Назад")],
        ],
        resize_keyboard=True,
    )
