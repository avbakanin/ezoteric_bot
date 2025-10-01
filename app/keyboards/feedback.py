"""
Клавиатуры для обратной связи
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_feedback_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для отзывов и обратной связи
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data="leave_feedback")],
            [InlineKeyboardButton(text="💬 Предложение", callback_data="suggestion")],
            [InlineKeyboardButton(text="🐛 Сообщить об ошибке", callback_data="report_bug")],
            [InlineKeyboardButton(text="↩️ Назад", callback_data="back_about")],
        ]
    )
    return keyboard
