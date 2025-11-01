"""
Клавиатуры для обратной связи
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..messages import CallbackData


def get_feedback_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для отзывов и обратной связи
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оставить отзыв", callback_data=CallbackData.LEAVE_FEEDBACK)],
            [InlineKeyboardButton(text="💬 Предложение", callback_data=CallbackData.SUGGESTION)],
            [InlineKeyboardButton(text="🐛 Сообщить об ошибке", callback_data=CallbackData.REPORT_BUG)],
            [InlineKeyboardButton(text="↩️ Назад", callback_data=CallbackData.BACK_ABOUT)],
        ]
    )
    return keyboard
