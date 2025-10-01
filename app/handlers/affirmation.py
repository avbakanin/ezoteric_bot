from aiogram import F, Router
from aiogram.types import CallbackQuery
from calculations import get_affirmation
from messages import CallbackData, get_affirmation_text

router = Router()


@router.callback_query(F.data == CallbackData.AFFIRMATION)
async def affirmation_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    _, text = get_affirmation(user_id)
    await callback_query.message.edit_text(get_affirmation_text(text))
