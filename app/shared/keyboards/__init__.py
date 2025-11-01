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

# Главное меню
from .main import get_main_menu_keyboard

# Навигация
from .navigation import get_back_to_main_keyboard

# Premium
from .premium import get_premium_info_keyboard

# Профиль
from .profile import get_profile_keyboard

# Результаты
from .results import get_compatibility_result_keyboard, get_result_keyboard

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
]
