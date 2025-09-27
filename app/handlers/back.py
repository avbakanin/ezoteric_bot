from aiogram import Router
from aiogram.types import CallbackQuery
from keyboards import get_about_keyboard, get_main_menu_keyboard
from messages import MESSAGES

router = Router()


@router.callback_query(lambda c: c.data == "back_main")
async def back_main_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text("🔮 Главное меню")
    await callback_query.message.answer("Выберите действие:", reply_markup=get_main_menu_keyboard())


@router.callback_query(lambda c: c.data == "back_about")
async def back_about_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        MESSAGES["ABOUT_DESCRIPTION"],
        reply_markup=get_about_keyboard(),
    )
