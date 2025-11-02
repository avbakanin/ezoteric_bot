"""Дневник наблюдений."""

import asyncio
import datetime

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.shared.decorators import catch_errors
from app.shared.formatters import format_datetime_iso
from app.shared.helpers import (
    check_base_achievements,
    check_daily_challenge_completion,
    check_streak_achievements,
    get_achievement_info,
    get_personalized_recommendation,
    update_user_activity,
)
from app.shared.keyboards import (
    get_back_to_main_keyboard,
    get_diary_category_keyboard,
    get_diary_history_keyboard,
    get_diary_result_keyboard,
)
from app.shared.keyboards.categories import get_main_menu_keyboard_categorized
from app.shared.messages import CallbackData, DiaryMessages, MessagesData, TextCommandsData
from app.shared.security import security_validator
from app.shared.state import UserStates
from app.shared.storage import user_storage

router = Router()

CATEGORY_LABELS = {
    "feeling": "Чувство",
    "event": "Событие",
    "idea": "Идея",
    "goal": "Цель/Достижение",
    "insight": "Инсайт/Знак",
    "gratitude": "Благодарность",
}


async def _enter_diary(state: FSMContext, send_func, bot, chat_id):
    start_time = datetime.now().timestamp()
    await state.update_data(diary_category=None, diary_started_at=start_time)
    await send_func(
        DiaryMessages.PROMPT,
        reply_markup=get_diary_category_keyboard(),
    )
    await state.set_state(UserStates.waiting_for_diary_category)
    asyncio.create_task(_schedule_diary_reminder(state, bot, chat_id, start_time))
    asyncio.create_task(_schedule_diary_timeout(state, bot, chat_id, start_time))


async def _schedule_diary_reminder(state: FSMContext, bot, chat_id: int, start_time: float):
    await asyncio.sleep(300)
    data = await state.get_data()
    if data.get("diary_started_at") != start_time:
        return
    current_state = await state.get_state()
    if current_state not in {
        UserStates.waiting_for_diary_category.state,
        UserStates.waiting_for_diary_observation.state,
    }:
        return
    await bot.send_message(
        chat_id,
        DiaryMessages.REMINDER,
        reply_markup=get_diary_category_keyboard(),
    )


async def _schedule_diary_timeout(state: FSMContext, bot, chat_id: int, start_time: float):
    await asyncio.sleep(1800)
    data = await state.get_data()
    if data.get("diary_started_at") != start_time:
        return
    current_state = await state.get_state()
    if current_state not in {
        UserStates.waiting_for_diary_category.state,
        UserStates.waiting_for_diary_observation.state,
    }:
        return
    await state.clear()
    await bot.send_message(
        chat_id,
        DiaryMessages.TIMEOUT,
    )
    await bot.send_message(
        chat_id,
        MessagesData.SELECT_ACTION,
        reply_markup=get_main_menu_keyboard_categorized(),
    )


@router.callback_query(F.data == CallbackData.DIARY_OBSERVATION)
async def diary_observation_from_inline(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await _enter_diary(state, callback_query.message.edit_text, callback_query.bot, callback_query.message.chat.id)


@router.message(F.text == TextCommandsData.DIARY_OBSERVATION, StateFilter("*"))
async def diary_observation_from_menu(message: Message, state: FSMContext):
    await state.clear()
    await _enter_diary(state, message.answer, message.bot, message.chat.id)


@router.callback_query(StateFilter(UserStates.waiting_for_diary_category), F.data.startswith("diary_category:"))
async def diary_category_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    _, payload = callback_query.data.split(":", 1)

    if payload == "cancel":
        await state.clear()
        await callback_query.message.edit_text(
            DiaryMessages.CANCELLED,
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    await state.set_state(UserStates.waiting_for_diary_observation)

    if payload == "skip":
        await callback_query.message.edit_text(
            DiaryMessages.CATEGORY_SKIPPED,
            reply_markup=None,
        )
        return

    category_label = CATEGORY_LABELS.get(payload, "Без темы")
    await state.update_data(diary_category=category_label)
    await callback_query.message.edit_text(
        DiaryMessages.CATEGORY_CONFIRMED.format(category=category_label),
        reply_markup=None,
    )


@router.message(UserStates.waiting_for_diary_observation)
@catch_errors()
async def handle_diary_observation(message: Message, state: FSMContext):
    observation_text = message.text.strip()
    user_id = message.from_user.id

    if not security_validator.rate_limit_check(user_id, "diary"):
        await message.answer(
            MessagesData.ERROR_DIARY_LIMIT_EXCEEDED,
            reply_markup=get_back_to_main_keyboard(),
        )
        await state.clear()
        return

    sanitized_text = security_validator.sanitize_text(observation_text)
    user_data = user_storage.get_user(user_id)
    data = await state.get_data()
    category = data.get("diary_category") or "Без темы"

    if "diary_observations" not in user_data:
        user_data["diary_observations"] = []

    observation = {
        "text": sanitized_text,
        "date": format_datetime_iso(),
        "number": user_data.get("life_path_number", "неизвестно"),
        "category": category,
    }
    user_data["diary_observations"].append(observation)
    user_storage._save_data()
    
    # Обновляем стрик и статистику
    streak = update_user_activity(user_id, "diary")
    user_storage.increment_stat(user_id, "total_diary_entries", "diary")
    unlocked_streak = check_streak_achievements(user_id, streak)
    unlocked_base = check_base_achievements(user_id)
    unlocked = unlocked_streak + unlocked_base

    result_text = (
        f"📝 Наблюдение сохранено!\n"
        f"Ваше число судьбы: {observation['number']}\n"
        f"Тема: {category}\n"
        f"Дата: {observation['date']}"
    )
    await message.answer(result_text, reply_markup=get_diary_result_keyboard())
    
    # Показываем достижения, если разблокированы
    if unlocked:
        from app.shared.messages import MessagesData
        for achievement_id in unlocked:
            name, desc = get_achievement_info(achievement_id)
            achievement_text = MessagesData.STREAK_ACHIEVEMENT_UNLOCKED.format(
                achievement_name=name,
                achievement_description=desc
            )
            await message.answer(achievement_text, reply_markup=get_back_to_main_keyboard())
    
    # Проверяем выполнение ежедневного задания
    is_completed, challenge_data = check_daily_challenge_completion(user_id, "diary")
    if is_completed and challenge_data:
        from app.shared.formatters import pluralize_days
        from app.shared.messages import MessagesData
        challenges = user_storage.get_daily_challenges(user_id)
        streak = challenges.get("streak", 0)
        days_word = pluralize_days(streak)
        completion_text = MessagesData.DAILY_CHALLENGE_COMPLETED.format(
            reward=challenge_data.get("reward", "Отлично!"),
            streak=streak,
            days_word=days_word
        )
        await message.answer(completion_text)
    
    # Показываем персонализированную рекомендацию
    recommendation = get_personalized_recommendation(user_id, "diary")
    if recommendation:
        from app.shared.keyboards import get_recommendation_keyboard
        rec_text, rec_action = recommendation
        await message.answer(rec_text, reply_markup=get_recommendation_keyboard(rec_action))
    
    await state.clear()


@router.callback_query(F.data == "diary_history:last3")
@catch_errors()
async def diary_history_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    user_data = user_storage.get_user(user_id)
    entries = user_data.get("diary_observations", [])
    is_premium = user_data.get("subscription", {}).get("active", False)

    if not entries:
        await callback_query.message.answer(
            DiaryMessages.HISTORY_EMPTY,
            reply_markup=get_diary_history_keyboard(is_premium),
        )
        return

    lines = []
    for obs in entries[-3:][::-1]:
        lines.append(
            "• {date} ({category})\n  {text}".format(
                date=obs.get("date", "-"),
                category=obs.get("category", "Без темы"),
                text=obs.get("text", ""),
            )
        )

    history_text = DiaryMessages.HISTORY_TITLE.format(entries="\n\n".join(lines))
    if not is_premium:
        history_text = f"{history_text}\n\n{DiaryMessages.HISTORY_PREMIUM_PROMO}"
    await callback_query.message.answer(
        history_text,
        reply_markup=get_diary_history_keyboard(is_premium),
    )

