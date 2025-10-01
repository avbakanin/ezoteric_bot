"""
Общие переиспользуемые клавиатуры
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
