"""
Клавиатуры главного меню
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from ..messages import TextCommandsData


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Создает главное меню бота (MVP структура)
    """
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        keyboard=[
            [KeyboardButton(text=TextCommandsData.LIFE_PATH_NUMBER)],
            [KeyboardButton(text=TextCommandsData.NAME_NUMBER)],
            [KeyboardButton(text=TextCommandsData.YES_NO)],
            [KeyboardButton(text=TextCommandsData.DAILY_NUMBER)],
            [KeyboardButton(text=TextCommandsData.COMPATIBILITY)],
            [KeyboardButton(text=TextCommandsData.PROFILE)],
            [KeyboardButton(text=TextCommandsData.ABOUT)],
            [KeyboardButton(text=TextCommandsData.DIARY_OBSERVATION)],
            [KeyboardButton(text=TextCommandsData.FEEDBACK)],
        ],
    )
    return keyboard
