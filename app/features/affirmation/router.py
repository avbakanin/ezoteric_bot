"""Аффирмации."""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.shared.calculations import get_affirmation
from app.shared.keyboards import get_affirmation_keyboard
from app.shared.messages import CallbackData, get_affirmation_text

router = Router()


@router.callback_query(F.data == CallbackData.AFFIRMATION)
async def affirmation_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    result = get_affirmation(user_id)
    await callback_query.message.edit_text(
        get_affirmation_text(result),
        reply_markup=get_affirmation_keyboard(result.is_premium_user),
    )


@router.callback_query(F.data == CallbackData.AFFIRMATION_NEW)
async def affirmation_new_handler(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    current_result = get_affirmation(user_id)
    if not current_result.is_premium_user:
        await callback_query.answer(
            "Дополнительные аффирмации доступны в Premium.", show_alert=True
        )
        return

    result = get_affirmation(user_id, force_new=True)
    await callback_query.answer()
    await callback_query.message.edit_text(
        get_affirmation_text(result),
        reply_markup=get_affirmation_keyboard(result.is_premium_user),
    )

