"""
Клавиатуры для профиля пользователя
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from messages import CallbackData


def get_profile_keyboard(has_calculated: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для профиля пользователя
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧮 Рассчитать число", callback_data=CallbackData.CALCULATE_NUMBER
                )
            ],
            [InlineKeyboardButton(text="↩️ В главное меню", callback_data=CallbackData.BACK_MAIN)],
        ]
    )
    return keyboard
