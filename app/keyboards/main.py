"""
Клавиатуры главного меню
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает главное меню бота (MVP структура)
    """
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        keyboard=[
            [KeyboardButton(text="🧮 Рассчитать Число Судьбы")],
            [KeyboardButton(text="💑 Проверить Совместимость")],
            [KeyboardButton(text="📊 Мой Профиль")],
            [KeyboardButton(text="ℹ️ О боте")],
            [KeyboardButton(text="📔 Дневник наблюдений")],
            [KeyboardButton(text="📝 Оставить отзыв")],
        ],
    )
    return keyboard
