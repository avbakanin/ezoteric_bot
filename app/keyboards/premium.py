"""
Клавиатуры для Premium функций
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
