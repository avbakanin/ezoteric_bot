"""
Клавиатуры для информационных страниц
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
