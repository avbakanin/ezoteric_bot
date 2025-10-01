"""
Клавиатуры для Premium функций
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from messages import CallbackData


def get_premium_info_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для информации о Premium
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Оформить Premium", callback_data=CallbackData.SUBSCRIBE)],
            [
                InlineKeyboardButton(
                    text="📋 Что входит в Premium", callback_data=CallbackData.PREMIUM_FEATURES
                )
            ],
            [InlineKeyboardButton(text="↩️ Назад", callback_data=CallbackData.BACK_ABOUT)],
        ]
    )
    return keyboard
