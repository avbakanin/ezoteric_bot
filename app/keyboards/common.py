"""
Общие переиспользуемые клавиатуры
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from messages import CallbackData


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками "Да" и "Нет"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=CallbackData.YES),
                InlineKeyboardButton(text="❌ Нет", callback_data=CallbackData.NO),
            ]
        ]
    )
    return keyboard
