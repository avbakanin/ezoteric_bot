"""
Клавиатуры для персонализированных рекомендаций.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ..messages import CallbackData, TextCommandsData


def get_recommendation_keyboard(action_callback: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для рекомендации с кнопкой действия.
    
    Args:
        action_callback: Callback data для действия (например, "diary_observation", "tarot")
    
    Returns:
        InlineKeyboardMarkup с кнопкой действия
    """
    # Маппинг callback -> текст кнопки
    button_texts = {
        "diary_observation": "📝 Записать в дневник",
        "tarot": "🔮 Получить карту",
        "compatibility": "💑 Проверить совместимость",
        "natal_profile": "🌌 Заполнить профиль",
        "natal_chart": "🌌 Натальная карта",
        "lunar_planner": "🌙 Планировщик",
    }
    
    button_text = button_texts.get(action_callback, "Попробовать")
    
    # Преобразуем action_callback в правильный callback_data
    from ..messages import CommandsData
    callback_mapping = {
        "diary_observation": CallbackData.DIARY_OBSERVATION,
        "tarot": CallbackData.TAROT_SELECT_SPREAD,
        "compatibility": TextCommandsData.COMPATIBILITY,
        "natal_profile": CommandsData.NATAL_PROFILE,
        "natal_chart": TextCommandsData.NATAL_CHART,
        "lunar_planner": TextCommandsData.LUNAR_PLANNER,
    }
    
    callback_data = callback_mapping.get(action_callback, CallbackData.BACK_MAIN)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=callback_data,
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩️ В главное меню",
                    callback_data=CallbackData.BACK_MAIN,
                )
            ],
        ]
    )
    return keyboard

