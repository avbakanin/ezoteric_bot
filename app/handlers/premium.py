from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from calculations import calculate_daily_number
from keyboards import get_back_to_main_keyboard
from messages import MESSAGES
from storage import user_storage

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


from calculations import calculate_daily_number


@router.callback_query(lambda c: c.data == "daily_number")
async def daily_number_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    user_data = user_storage.get_user(user_id)

    # Проверка кэша
    cached = user_storage.get_cached_result(user_id)
    if cached and cached.get("daily_number_result"):
        daily_number = cached["daily_number_result"]
    else:
        daily_number = calculate_daily_number()
        # Сохраняем в кэш без перезаписи life_path
        if cached:
            cached["daily_number_result"] = daily_number
            user_storage._save_data()

    await callback_query.message.edit_text(f"🔢 Ваше число дня: {daily_number}")
