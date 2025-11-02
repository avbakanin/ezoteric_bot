"""
Клавиатуры для профиля пользователя
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..messages import CallbackData


def get_profile_keyboard(
    has_calculated: bool = False,
    notifications_enabled: bool = False,
    subscription_active: bool = False,
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для профиля пользователя
    """
    toggle_text = (
        "🔕 Выключить уведомления" if notifications_enabled else "🔔 Включить уведомления"
    )

    rows = [
            [
                InlineKeyboardButton(
                    text="🧮 Рассчитать число", callback_data=CallbackData.LIFE_PATH_NUMBER
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Расширенная статистика", callback_data=CallbackData.PROFILE_STATS
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_text, callback_data=CallbackData.NOTIFICATIONS_TOGGLE
                )
            ],
    ]

    if not subscription_active:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💎 Узнать про Premium",
                    callback_data=CallbackData.PREMIUM_INFO,
                )
            ]
        )

    rows.append(
        [InlineKeyboardButton(text="↩️ В главное меню", callback_data=CallbackData.BACK_MAIN)]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)
