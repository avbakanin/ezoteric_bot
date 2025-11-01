"""Клавиатуры для дневника наблюдений."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..messages import CallbackData, DiaryMessages


def get_diary_category_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✨ Чувство", callback_data="diary_category:feeling")],
        [InlineKeyboardButton(text="📅 Событие", callback_data="diary_category:event")],
        [InlineKeyboardButton(text="💡 Идея", callback_data="diary_category:idea")],
        [InlineKeyboardButton(text="➡️ Пропустить", callback_data="diary_category:skip")],
        [InlineKeyboardButton(text="↩️ Выйти", callback_data="diary_category:cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_diary_result_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=DiaryMessages.HISTORY_BUTTON, callback_data="diary_history:last3")],
        [InlineKeyboardButton(text="↩️ В главное меню", callback_data=CallbackData.BACK_MAIN)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_diary_history_keyboard(is_premium: bool) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="↩️ В главное меню", callback_data=CallbackData.BACK_MAIN)]]
    if not is_premium:
        buttons.insert(0, [InlineKeyboardButton(text="💎 Оформить Premium", callback_data=CallbackData.SUBSCRIBE)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

