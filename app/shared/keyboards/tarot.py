"""Клавиатуры для Таро."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..messages import CallbackData


def get_spreads_keyboard(available_spreads: dict, is_premium: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора расклада.

    Args:
        available_spreads: Словарь доступных раскладов {key: spread_info}
        is_premium: Является ли пользователь Premium

    Returns:
        InlineKeyboardMarkup с кнопками раскладов
    """
    buttons = []

    # Сначала бесплатные расклады
    free_spreads = []
    premium_spreads = []

    for key, spread in available_spreads.items():
        name = spread.get("name", key)
        emoji = "🔮"
        if "да/нет" in name.lower() or "yes" in key.lower():
            emoji = "❓"
        elif "день" in name.lower() or "daily" in key.lower():
            emoji = "📅"
        elif "три" in name.lower() or "three" in key.lower():
            emoji = "🎴"
        elif "кельт" in name.lower() or "celtic" in key.lower():
            emoji = "⛪"
        elif "отнош" in name.lower() or "relationship" in key.lower():
            emoji = "💑"
        elif "карьер" in name.lower() or "career" in key.lower():
            emoji = "💼"

        if spread.get("free", False):
            free_spreads.append((key, name, emoji))
        else:
            premium_spreads.append((key, name, emoji))

    # Добавляем бесплатные
    for key, name, emoji in sorted(free_spreads):
        buttons.append([InlineKeyboardButton(text=f"{emoji} {name}", callback_data=f"{CallbackData.TAROT_SPREAD_PREFIX}{key}")])

    # Добавляем Premium
    if premium_spreads:
        buttons.append([InlineKeyboardButton(text="💎 Premium расклады", callback_data=CallbackData.TAROT_PREMIUM_SPREADS)])
        if is_premium:
            for key, name, emoji in sorted(premium_spreads):
                buttons.append([InlineKeyboardButton(text=f"{emoji} {name}", callback_data=f"{CallbackData.TAROT_SPREAD_PREFIX}{key}")])

    # Кнопка истории и назад
    buttons.append([InlineKeyboardButton(text="📜 История раскладов", callback_data=CallbackData.TAROT_HISTORY)])
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data=CallbackData.BACK_MAIN)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_to_tarot_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой возврата к выбору расклада."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔮 Выбрать другой расклад", callback_data=CallbackData.TAROT_SELECT_SPREAD)],
            [InlineKeyboardButton(text="📜 История раскладов", callback_data=CallbackData.TAROT_HISTORY)],
            [InlineKeyboardButton(text="↩️ Назад в меню", callback_data=CallbackData.BACK_MAIN)],
        ]
    )


def get_tarot_question_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для вопроса перед раскладом."""
    from ..messages import MessagesData
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=MessagesData.TAROT_QUESTION_SKIP, callback_data=CallbackData.TAROT_QUESTION_SKIP)],
            [InlineKeyboardButton(text="↩️ Назад", callback_data=CallbackData.TAROT_SELECT_SPREAD)],
        ]
    )

