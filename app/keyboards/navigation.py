"""
Навигационные клавиатуры
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """
    Создает простую клавиатуру с кнопкой "В главное меню"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="↩️ В главное меню", callback_data="back_main")]]
    )
    return keyboard
