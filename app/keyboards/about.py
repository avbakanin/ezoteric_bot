"""
Клавиатуры для информационных страниц
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from messages import CallbackData


def get_about_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для страницы "О боте"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Узнать о Premium", callback_data=CallbackData.PREMIUM_INFO)],
            [InlineKeyboardButton(text="📝 Оставить отзыв", callback_data=CallbackData.FEEDBACK)],
            [
                InlineKeyboardButton(
                    text="📔 Дневник наблюдений", callback_data=CallbackData.DIARY_OBSERVATION
                )
            ],
            [InlineKeyboardButton(text="↩️ В главное меню", callback_data=CallbackData.BACK_MAIN)],
        ]
    )
    return keyboard
