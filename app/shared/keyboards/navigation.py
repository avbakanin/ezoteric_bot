"""
Навигационные клавиатуры
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..messages import CallbackData


def get_back_to_main_keyboard() -> InlineKeyboardMarkup:
    """
    Создает простую клавиатуру с кнопкой "В главное меню"
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="↩️ В главное меню", callback_data=CallbackData.BACK_MAIN)]
        ]
    )
    return keyboard
