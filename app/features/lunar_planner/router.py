"""Команда для лунного планировщика дел."""

from __future__ import annotations

from datetime import date
from typing import List, Sequence

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

from app.shared.astro import daily_transit_service
from app.shared.astro.lunar_planner import (
    ACTIONS,
    ActionDefinition,
    ActionSuggestion,
    DayContext,
    PhaseAdvice,
    get_house_interpretation,
    lunar_planner_service,
)
from app.shared.decorators import catch_errors
from app.shared.formatters import format_date_label, pluralize_days
from app.shared.helpers import get_today_local, get_user_timezone, is_premium
from app.shared.keyboards import get_lunar_actions_keyboard
from app.shared.messages import CallbackData, CommandsData, MessagesData, TextCommandsData

router = Router()


@router.message(Command(CommandsData.LUNAR_PLANNER), StateFilter("*"))
@router.message(F.text == TextCommandsData.LUNAR_PLANNER, StateFilter("*"))
@catch_errors()
async def lunar_planner_command(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    is_premium_user = is_premium(user_id)
    tz_name = get_user_timezone(user_id)
    today = get_today_local(tz_name)

    # Получаем натальную карту для персонализации (только для Premium)
    natal_chart = None
    if is_premium_user:
        forecast = daily_transit_service.generate_for_user(user_id, target_date=today)
        if forecast.ok and forecast.natal_chart:
            natal_chart = forecast.natal_chart

    days_count = 6 if is_premium_user else 4
    window = lunar_planner_service.build_window(start=today, tz_name=tz_name, days=days_count, natal_chart=natal_chart)

    suggestions_map = {
        ctx.date: lunar_planner_service.select_actions(
            day=ctx,
            is_premium=is_premium_user,
            limit=5 if is_premium_user else 3,
        )
        for ctx in window
    }

    overview_text = _build_overview_text(
        window=window,
        suggestions_map=suggestions_map,
        tz_name=tz_name,
        is_premium=is_premium_user,
        has_natal_profile=bool(natal_chart),
    )

    display_actions = _collect_display_actions(window, is_premium_user, limit=12 if is_premium_user else 8)
    buttons = [(action.slug, f"{action.emoji} {action.title}") for action in display_actions]

    extra_buttons: List[InlineKeyboardButton] = []
    if not is_premium_user:
        extra_buttons.append(
            InlineKeyboardButton(text="💎 Расширить", callback_data=CallbackData.PREMIUM_INFO)
        )

    keyboard = get_lunar_actions_keyboard(
        buttons,
        include_back=True,
        extra_buttons=extra_buttons,
    )

    await message.answer(overview_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CallbackData.LUNAR_ACTION_PREFIX))
@catch_errors()
async def lunar_planner_action_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    is_premium_user = is_premium(user_id)
    tz_name = get_user_timezone(user_id)
    today = get_today_local(tz_name)

    slug = callback.data.replace(CallbackData.LUNAR_ACTION_PREFIX, "", 1)
    action = lunar_planner_service.get_action(slug)
    if not action:
        await callback.answer("Сценарий не найден.", show_alert=True)
        return
    if action.premium_only and not is_premium_user:
        await callback.answer("Сценарий доступен в Premium.", show_alert=True)
        return

    # Получаем натальную карту для персонализации (только для Premium)
    natal_chart = None
    if is_premium_user:
        forecast = daily_transit_service.generate_for_user(user_id, target_date=today)
        if forecast.ok and forecast.natal_chart:
            natal_chart = forecast.natal_chart

    window = lunar_planner_service.build_window(start=today, tz_name=tz_name, days=7 if is_premium_user else 5, natal_chart=natal_chart)

    details_text = _build_action_details(action, window)

    display_actions = _collect_display_actions(window, is_premium_user, limit=12 if is_premium_user else 8)
    buttons = [(item.slug, f"{item.emoji} {item.title}") for item in display_actions]

    extra_buttons: List[InlineKeyboardButton] = []
    if not is_premium_user:
        extra_buttons.append(
            InlineKeyboardButton(text="💎 Расширить", callback_data=CallbackData.PREMIUM_INFO)
        )

    keyboard = get_lunar_actions_keyboard(
        buttons,
        include_back=True,
        extra_buttons=extra_buttons,
    )

    await callback.message.answer(details_text, reply_markup=keyboard)
    await callback.answer()


def _build_overview_text(
    *,
    window: Sequence[DayContext],
    suggestions_map: dict[date, Sequence[ActionSuggestion]],
    tz_name: str,
    is_premium: bool,
    has_natal_profile: bool = False,
) -> str:
    days_count = len(window)
    parts: List[str] = [
        MessagesData.LUNAR_PLANNER_INTRO.format(
            days=days_count,
            days_word=pluralize_days(days_count),
        ),
        f"Часовой пояс: {tz_name}",
    ]

    for idx, ctx in enumerate(window):
        suggestions = suggestions_map.get(ctx.date, [])
        parts.append(_format_day_section(window, idx, suggestions, has_natal_profile=has_natal_profile))

    parts.append(MessagesData.LUNAR_PLANNER_ACTION_HINT)

    if is_premium:
        parts.append(MessagesData.LUNAR_PLANNER_PREMIUM_THANKS)
    else:
        parts.extend(
            [
                MessagesData.LUNAR_PLANNER_PREMIUM_PROMO,
                MessagesData.LUNAR_PLANNER_PREMIUM_CTA,
            ]
        )

    return "\n\n".join(parts)


def _format_day_section(
    window: Sequence[DayContext],
    index: int,
    suggestions: Sequence[ActionSuggestion],
    has_natal_profile: bool = False,
) -> str:
    ctx = window[index]
    date_label = format_date_label(ctx.date)
    span = _calculate_sign_span(window, index)
    lines = [
        f"{ctx.phase.emoji} {date_label} — {ctx.phase.title}",
        ctx.phase.description,
        f"Энергия: {ctx.phase.energy.capitalize()}.",
        f"Луна в {ctx.moon_sign.emoji} {ctx.moon_sign.title} {_format_sign_duration(span)}",
        f"Фокус: {ctx.moon_sign.focus}",
        f"Влияние: {ctx.moon_sign.vibe}",
        f"Рекомендуется: {ctx.moon_sign.recommended}",
        f"Предупреждение: {ctx.moon_sign.caution}",
    ]
    
    # Персональная информация о доме (компактно, только для Premium с профилем)
    # Интегрируем естественно в раздел "Рекомендуется" или добавляем одну строку
    if has_natal_profile and ctx.natal_house:
        house_interpretation = get_house_interpretation(ctx.natal_house)
        if house_interpretation:
            # Добавляем как дополнительную рекомендацию, но без лишних эмодзи
            lines.append(f"Персональный акцент: {house_interpretation}")

    if suggestions:
        lines.append("Лучшие дела:")
        for suggestion in suggestions:
            marker = "🔥" if suggestion.advice.rating == "great" else "✅"
            lines.append(
                f"{marker} {suggestion.action.emoji} {suggestion.action.title} — {suggestion.advice.text}"
            )
    else:
        lines.append("Пока нет ярких сценариев — сфокусируйтесь на базовых задачах и отдыхе.")

    return "\n".join(lines)


def _build_action_details(action: ActionDefinition, window: Sequence[DayContext]) -> str:
    header = MessagesData.LUNAR_PLANNER_ACTION_DETAILS_TITLE.format(
        emoji=action.emoji,
        title=action.title,
        summary=action.summary,
    )

    best: List[tuple] = []
    good: List[tuple] = []
    avoid: List[tuple] = []

    for ctx in window:
        phase_advice = action.phase_advice.get(ctx.phase.key)
        if phase_advice is None:
            continue
        if phase_advice.score >= 3:
            best.append((ctx, phase_advice))
        elif phase_advice.score == 2:
            good.append((ctx, phase_advice))
        elif phase_advice.score == 0:
            avoid.append((ctx, phase_advice))

    lines: List[str] = [header]

    if best:
        lines.append(MessagesData.LUNAR_PLANNER_ACTION_DETAILS_BEST)
        lines.extend(_format_action_day_line(ctx, adv) for ctx, adv in best)
    if good:
        lines.append(MessagesData.LUNAR_PLANNER_ACTION_DETAILS_GOOD)
        lines.extend(_format_action_day_line(ctx, adv) for ctx, adv in good)
    if avoid:
        lines.append(MessagesData.LUNAR_PLANNER_ACTION_DETAILS_AVOID)
        lines.extend(_format_action_day_line(ctx, adv, include_caution=True) for ctx, adv in avoid)

    if len(lines) == 1:
        lines.append(MessagesData.LUNAR_PLANNER_ACTION_DETAILS_EMPTY)

    return "\n".join(lines)


def _format_action_day_line(ctx, advice: PhaseAdvice, include_caution: bool = False) -> str:
    label = format_date_label(ctx.date)
    line = (
        f"• {ctx.phase.emoji} {label} — {ctx.phase.title}. "
        f"Луна в {ctx.moon_sign.emoji} {ctx.moon_sign.title}: {advice.text}"
    )
    if include_caution and advice.caution:
        line = f"{line}\n   ⚠️ {advice.caution}"
    return line


def _collect_display_actions(
    window: Sequence[DayContext],
    is_premium: bool,
    *,
    limit: int,
) -> List[ActionDefinition]:
    result: List[ActionDefinition] = []
    seen: set[str] = set()
    for ctx in window:
        suggestions = lunar_planner_service.select_actions(
            day=ctx,
            is_premium=is_premium,
            limit=6 if is_premium else 4,
        )
        for suggestion in suggestions:
            slug = suggestion.action.slug
            if slug in seen:
                continue
            result.append(suggestion.action)
            seen.add(slug)
            if len(result) >= limit:
                return result

    for action in ACTIONS:
        if action.premium_only and not is_premium:
            continue
        if action.slug in seen:
            continue
        result.append(action)
        seen.add(action.slug)
        if len(result) >= limit:
            break

    return result


def _calculate_sign_span(window: Sequence[DayContext], index: int) -> int:
    current = window[index].moon_sign.key
    count = 1
    for idx in range(index + 1, len(window)):
        if window[idx].moon_sign.key != current:
            break
        count += 1
    return count


def _format_sign_duration(span: int) -> str:
    if span <= 1:
        return "только сегодня"
    return f"в ближайшие {span} {pluralize_days(span)}"






