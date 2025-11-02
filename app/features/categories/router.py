"""
Обработчики категоризированного меню.
"""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.decorators import catch_errors
from app.shared.keyboards.categories import (
    get_astrology_menu_keyboard,
    get_category_description_text,
    get_numerology_menu_keyboard,
    get_practices_menu_keyboard,
    get_profile_menu_keyboard,
)
from app.shared.messages import MessagesData

router = Router()

# Обработчики текстовых команд категорий
CATEGORY_HANDLERS = {
    "🧮 Нумерология": ("category:numerology", get_numerology_menu_keyboard),
    "🌌 Астрология": ("category:astrology", get_astrology_menu_keyboard),
    "🔮 Практики": ("category:practices", get_practices_menu_keyboard),
    "📊 Профиль": ("category:profile", get_profile_menu_keyboard),
}


@router.message(F.text.in_(CATEGORY_HANDLERS.keys()), StateFilter("*"))
@catch_errors()
async def category_menu_handler(message: Message, state: FSMContext):
    """Обработчик выбора категории из главного меню."""
    await state.clear()
    category_text = message.text
    _, keyboard_func = CATEGORY_HANDLERS[category_text]
    description = get_category_description_text(category_text)
    
    await message.answer(description, reply_markup=keyboard_func())


@router.message(F.text == "↩️ В главное меню", StateFilter("*"))
@catch_errors()
async def back_to_main_menu_handler(message: Message, state: FSMContext):
    """Обработчик возврата в главное меню."""
    await state.clear()
    from app.shared.keyboards.categories import get_main_menu_keyboard_categorized
    
    await message.answer(
        MessagesData.MAIN_MENU,
        reply_markup=get_main_menu_keyboard_categorized(),
    )



