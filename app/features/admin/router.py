"""Административные команды."""

import logging
from typing import List, Tuple

from aiogram import Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.decorators import catch_errors
from app.shared.messages import CommandsData, MessagesData
from app.shared.security import is_admin
from app.shared.storage import user_storage

logger = logging.getLogger(__name__)

router = Router()

_ALLOWED_ACTIONS = {"on", "off", "toggle", "status"}


def _extract_action_and_target(args: List[str], default_user_id: int) -> Tuple[str, int]:
    action = None
    target_id = None

    for token in args:
        clean = token.strip()
        if not clean:
            continue

        if clean.startswith("@"):
            continue

        normalized = clean.lower().strip(",.")

        if normalized in _ALLOWED_ACTIONS and action is None:
            action = normalized
            continue

        numeric_candidate = clean.strip(",.")
        if numeric_candidate.lstrip("+").isdigit() and target_id is None:
            try:
                target_id = int(numeric_candidate)
            except ValueError:
                continue

    if action is None:
        action = "toggle"
    if target_id is None:
        target_id = default_user_id

    return action, target_id


@router.message(Command(CommandsData.PREMIUM_ADMIN), StateFilter("*"))
@catch_errors("Ошибка обработки команды администратора.")
async def premium_admin_command(message: Message, state: FSMContext):
    await state.clear()

    if not is_admin(message.from_user.id):
        await message.answer(MessagesData.ADMIN_ACCESS_DENIED)
        return

    parts = [part for part in message.text.split() if part]
    args = parts[1:]

    if args and args[0].lower() in {"help", "?"}:
        await message.answer(MessagesData.ADMIN_PREMIUM_USAGE)
        return

    action, target_user_id = _extract_action_and_target(args, message.from_user.id)

    if action not in _ALLOWED_ACTIONS:
        await message.answer(MessagesData.ADMIN_PREMIUM_USAGE)
        return

    user_data = user_storage.get_user(target_user_id)
    subscription = user_data.get("subscription", {})
    current_active = bool(subscription.get("active"))
    status_text = "💎 активен" if current_active else "🆓 выключен"
    expires = subscription.get("expires") or "не задан"

    if action == "status":
        await message.answer(
            MessagesData.ADMIN_PREMIUM_STATUS.format(
                user_id=target_user_id,
                status=f"{status_text} (до {expires})" if current_active else status_text,
            )
        )
        return

    desired_state = (
        True
        if action == "on"
        else False
        if action == "off"
        else not current_active
    )

    if desired_state == current_active:
        await message.answer(
            MessagesData.ADMIN_PREMIUM_STATUS.format(
                user_id=target_user_id,
                status=f"{status_text} (до {expires})" if current_active else status_text,
            )
        )
        return

    user_storage.set_subscription(target_user_id, active=desired_state)
    new_status_text = "💎 активен" if desired_state else "🆓 выключен"

    logger.info(
        "Администратор %s изменил статус Premium пользователя %s на %s",
        message.from_user.id,
        target_user_id,
        new_status_text,
    )

    await message.answer(
        MessagesData.ADMIN_PREMIUM_UPDATED.format(
            user_id=target_user_id,
            status=new_status_text,
        )
    )

