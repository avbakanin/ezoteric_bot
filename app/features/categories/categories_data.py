"""
Константы для категоризированного меню.
"""

from app.shared.keyboards.categories import (
    get_astrology_menu_keyboard,
    get_numerology_menu_keyboard,
    get_practices_menu_keyboard,
    get_profile_menu_keyboard,
)

# Обработчики текстовых команд категорий
CATEGORY_HANDLERS = {
    "🧮 Нумерология": ("category:numerology", get_numerology_menu_keyboard),
    "🌌 Астрология": ("category:astrology", get_astrology_menu_keyboard),
    "🔮 Практики": ("category:practices", get_practices_menu_keyboard),
    "📊 Профиль": ("category:profile", get_profile_menu_keyboard),
}

