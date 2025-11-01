"""Клавиатура для блока аффирмаций."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..messages import CallbackData


def get_affirmation_keyboard(is_premium: bool) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="📔 Записать ощущение", callback_data=CallbackData.DIARY_OBSERVATION)]
    ]

    if is_premium:
        buttons.append(
            [InlineKeyboardButton(text="🔁 Новая аффирмация", callback_data=CallbackData.AFFIRMATION_NEW)]
        )
    else:
        buttons.append(
            [InlineKeyboardButton(text="💎 Оформить Premium", callback_data=CallbackData.SUBSCRIBE)]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)

