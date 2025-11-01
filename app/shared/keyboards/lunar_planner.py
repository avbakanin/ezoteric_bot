"""Клавиатуры для лунного планировщика."""

from __future__ import annotations

from typing import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..messages import CallbackData


def get_lunar_actions_keyboard(
    action_buttons: Sequence[tuple[str, str]],
    *,
    include_back: bool = True,
    extra_buttons: Sequence[InlineKeyboardButton] | None = None,
) -> InlineKeyboardMarkup:
    inline_keyboard: list[list[InlineKeyboardButton]] = []

    for index in range(0, len(action_buttons), 2):
        row_data = action_buttons[index : index + 2]
        row: list[InlineKeyboardButton] = []
        for slug, title in row_data:
            row.append(
                InlineKeyboardButton(
                    text=title,
                    callback_data=f"{CallbackData.LUNAR_ACTION_PREFIX}{slug}",
                )
            )
        inline_keyboard.append(row)

    if extra_buttons:
        for button in extra_buttons:
            inline_keyboard.append([button])

    if include_back:
        inline_keyboard.append(
            [InlineKeyboardButton(text="↩️ В главное меню", callback_data=CallbackData.BACK_MAIN)]
        )

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


