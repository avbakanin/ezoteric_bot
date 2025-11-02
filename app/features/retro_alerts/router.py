"""Команда для просмотра ретроградных предупреждений."""

from __future__ import annotations

from datetime import timedelta

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.shared.astro import retrograde_service
from app.shared.decorators import catch_errors
from app.shared.helpers import get_today_local, get_user_timezone, is_premium
from app.shared.keyboards import get_back_to_main_keyboard, get_premium_info_keyboard
from app.shared.messages import CommandsData, MessagesData, TextCommandsData

router = Router()


@router.message(Command(CommandsData.RETRO_ALERTS), StateFilter("*"))
@router.message(F.text == TextCommandsData.RETRO_ALERTS, StateFilter("*"))
@catch_errors()
async def retro_alerts_command(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    is_premium_user = is_premium(user_id)

    tz_name = get_user_timezone(user_id)
    today_local = get_today_local(tz_name)

    periods = retrograde_service.get_periods(today_local, today_local + timedelta(days=120))
    # Free получают только Меркурий, Premium - все отслеживаемые планеты
    allowed_planets = retrograde_service.tracked_planets if is_premium_user else retrograde_service.base_planets

    blocks: list[str] = []
    for planet in allowed_planets:
        planet_periods = periods.get(planet, [])
        next_period = retrograde_service.get_next_period(planet, planet_periods, today_local)
        if not next_period:
            continue
        blocks.append(retrograde_service.format_summary(next_period, is_premium_user, today_local))

    if not blocks:
        await message.answer(
            MessagesData.RETRO_ALERTS_EMPTY,
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    reply_markup = get_back_to_main_keyboard()

    if not is_premium_user and len(retrograde_service.tracked_planets) > len(retrograde_service.base_planets):
        blocks.extend(
            [
                MessagesData.RETRO_ALERTS_PREMIUM_PROMO,
                MessagesData.RETRO_ALERTS_PREMIUM_CTA,
            ]
        )
        reply_markup = get_premium_info_keyboard()
    elif is_premium_user:
        blocks.append(MessagesData.RETRO_ALERTS_PREMIUM_THANKS)

    await message.answer("\n\n".join(blocks), reply_markup=reply_markup)


