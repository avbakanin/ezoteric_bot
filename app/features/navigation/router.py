"""Навигационные callback-и."""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.shared.keyboards import get_about_keyboard, get_main_menu_keyboard
from app.shared.messages import CallbackData, MessagesData

router = Router()


@router.callback_query(F.data == CallbackData.BACK_MAIN)
async def back_main_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(MessagesData.MAIN_MENU)
    await callback_query.message.answer(
        MessagesData.SELECT_ACTION,
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == CallbackData.BACK_ABOUT)
async def back_about_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        MessagesData.ABOUT_DESCRIPTION,
        reply_markup=get_about_keyboard(),
    )

