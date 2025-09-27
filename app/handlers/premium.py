from aiogram import Router
from aiogram.types import CallbackQuery
from keyboards import get_back_to_main_keyboard
from messages import MESSAGES

router = Router()


@router.callback_query(lambda c: c.data in ["premium_full", "premium_compatibility"])
async def premium_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    data = callback_query.data.upper()  # приводим к верхнему регистру

    await callback_query.message.edit_text(MESSAGES[data], reply_markup=get_back_to_main_keyboard())


@router.callback_query(lambda c: c.data == "premium_info")
async def premium_info_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        MESSAGES["PREMIUM_INFO_TEXT"], reply_markup=get_back_to_main_keyboard()
    )


@router.callback_query(lambda c: c.data == "subscribe")
async def subscribe_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "💎 ОФОРМЛЕНИЕ PREMIUM ПОДПИСКИ\n\nСкоро будет доступно!",
        reply_markup=get_back_to_main_keyboard(),
    )
