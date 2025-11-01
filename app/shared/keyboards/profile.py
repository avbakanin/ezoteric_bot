"""
Клавиатуры для профиля пользователя
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..messages import CallbackData


def get_profile_keyboard(
    has_calculated: bool = False,
    notifications_enabled: bool = False,
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для профиля пользователя
    """
    toggle_text = (
        "🔕 Выключить уведомления" if notifications_enabled else "🔔 Включить уведомления"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧮 Рассчитать число", callback_data=CallbackData.LIFE_PATH_NUMBER
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_text, callback_data=CallbackData.NOTIFICATIONS_TOGGLE
                )
            ],
            [InlineKeyboardButton(text="↩️ В главное меню", callback_data=CallbackData.BACK_MAIN)],
        ]
    )
    return keyboard
