"""
Инициализация модуля клавиатур.
Экспорт всех клавиатур из подмодулей.
"""

# Информация о боте
from .about import get_about_keyboard

# Аффирмации
from .affirmation import get_affirmation_keyboard

# Общие клавиатуры
from .common import get_yes_no_keyboard
from .diary import get_diary_category_keyboard, get_diary_history_keyboard, get_diary_result_keyboard

# Обратная связь
from .feedback import get_feedback_keyboard

# Лунный планировщик
from .lunar_planner import get_lunar_actions_keyboard

# Главное меню
from .main import get_main_menu_keyboard

# Навигация
from .navigation import get_back_to_main_keyboard

# Premium
from .premium import get_premium_info_keyboard

# Профиль
from .profile import get_profile_keyboard

# Рекомендации
from .recommendations import get_recommendation_keyboard

# Результаты
from .results import get_compatibility_result_keyboard, get_result_keyboard

# Таро
from .tarot import get_back_to_tarot_keyboard, get_spreads_keyboard, get_tarot_question_keyboard

__all__ = [
    # Главное меню
    "get_main_menu_keyboard",
    # Навигация
    "get_back_to_main_keyboard",
    # Результаты
    "get_result_keyboard",
    "get_compatibility_result_keyboard",
    # Профиль
    "get_profile_keyboard",
    # Информация
    "get_about_keyboard",
    # Premium
    "get_premium_info_keyboard",
    # Обратная связь
    "get_feedback_keyboard",
    "get_diary_category_keyboard",
    "get_diary_history_keyboard",
    "get_diary_result_keyboard",
    # Общие
    "get_yes_no_keyboard",
    # Аффирмации
    "get_affirmation_keyboard",
    # Лунный планировщик
    "get_lunar_actions_keyboard",
    # Таро
    "get_back_to_tarot_keyboard",
    "get_spreads_keyboard",
    "get_tarot_question_keyboard",
    # Рекомендации
    "get_recommendation_keyboard",
]
