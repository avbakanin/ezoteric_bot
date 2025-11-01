"""Профиль пользователя."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.settings import config
from app.shared.decorators import catch_errors
from app.shared.keyboards import get_premium_info_keyboard, get_profile_keyboard
from app.shared.messages import (
    CallbackData,
    CommandsData,
    MessagesData,
    TextCommandsData,
    get_profile_text,
)
from app.shared.storage import user_storage

router = Router()


def _build_profile_view(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    user_data = user_storage.get_user(user_id)
    usage_stats = user_storage.get_usage_stats(user_id)
    subscription_status = "Premium" if user_data["subscription"]["active"] else "Бесплатный"
    cached_result = user_storage.get_cached_result(user_id)
    notifications = user_data.get("notifications", {})
    notifications_enabled = notifications.get("enabled", False)
    notification_time = notifications.get("time") or config.NOTIFICATION_TIME
    has_calculated = user_data.get("birth_date") is not None

    profile_text = get_profile_text(
        user_id=user_id,
        life_path_number=user_data.get("life_path_number", "не рассчитано"),
        subscription_status=subscription_status,
        usage_stats=usage_stats,
        has_cached=bool(cached_result),
        notifications_enabled=notifications_enabled,
        notification_time=notification_time,
    )
    keyboard = get_profile_keyboard(has_calculated, notifications_enabled)
    return profile_text, keyboard


@router.message(Command(CommandsData.PREMIUM_INFO), StateFilter("*"))
@catch_errors()
async def premium_info_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        MessagesData.PREMIUM_INFO_TEXT,
        reply_markup=get_premium_info_keyboard(),
    )


@router.message(F.text == TextCommandsData.PROFILE, StateFilter("*"))
@catch_errors()
async def profile_command(message: Message, state: FSMContext):
    await state.clear()
    profile_text, keyboard = _build_profile_view(message.from_user.id)
    await message.answer(profile_text, reply_markup=keyboard)


@router.callback_query(F.data == CallbackData.NOTIFICATIONS_TOGGLE)
@catch_errors()
async def notifications_toggle(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = user_storage.get_user(user_id)
    notifications = user_data.get("notifications", {})
    enabled = notifications.get("enabled", False)
    notification_time = notifications.get("time") or config.NOTIFICATION_TIME

    if enabled:
        user_storage.set_notifications(user_id, False, notification_time)
        await callback.answer(MessagesData.NOTIFICATIONS_TOGGLE_OFF, show_alert=True)
    else:
        user_storage.set_notifications(user_id, True, notification_time)
        await callback.answer(
            MessagesData.NOTIFICATIONS_TOGGLE_ON.format(time=notification_time),
            show_alert=True,
        )

    profile_text, keyboard = _build_profile_view(user_id)
    await callback.message.edit_text(profile_text, reply_markup=keyboard)
