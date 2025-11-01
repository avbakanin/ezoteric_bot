"""Премиум-заглушки."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.shared.keyboards import get_back_to_main_keyboard, get_premium_info_keyboard
from app.shared.messages import CallbackData, CommandsData, MessagesData, TextCommandsData

router = Router()


@router.callback_query(F.data.in_([CallbackData.PREMIUM_FULL, CallbackData.PREMIUM_COMPATIBILITY]))
async def premium_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    data = callback_query.data.upper()
    await callback_query.message.edit_text(
        MessagesData[data],
        reply_markup=get_back_to_main_keyboard(),
    )


@router.callback_query(F.data == CallbackData.PREMIUM_INFO)
async def premium_info_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        MessagesData.PREMIUM_INFO_TEXT,
        reply_markup=get_premium_info_keyboard(),
    )


@router.callback_query(F.data == CallbackData.PREMIUM_FEATURES)
async def premium_features_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        MessagesData.PREMIUM_INFO_TEXT,
        reply_markup=get_premium_info_keyboard(),
    )


@router.callback_query(F.data == CallbackData.SUBSCRIBE)
async def subscribe_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        MessagesData.PREMIUM_SOON,
        reply_markup=get_back_to_main_keyboard(),
    )


@router.message(Command(CommandsData.PREMIUM_INFO))
@router.message(F.text == TextCommandsData.PREMIUM)
async def premium_info_message(message: Message):
    await message.answer(
        MessagesData.PREMIUM_INFO_TEXT,
        reply_markup=get_premium_info_keyboard(),
    )

