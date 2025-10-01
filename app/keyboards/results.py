"""
Клавиатуры для отображения результатов
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_result_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для результата расчета
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔒 Полная расшифровка (Премиум)", callback_data="premium_full")],
            [InlineKeyboardButton(text="📋 Посмотреть снова", callback_data="view_soul_number_again")],
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
