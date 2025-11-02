"""Расчет числа судьбы."""

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.shared.calculations import calculate_life_path_number, calculate_soul_number, validate_date
from app.shared.decorators import catch_errors
from app.shared.helpers import (
    check_base_achievements,
    check_streak_achievements,
    get_achievement_info,
    get_personalized_recommendation,
    update_user_activity,
)
from app.shared.keyboards import get_back_to_main_keyboard, get_result_keyboard
from app.shared.messages import (
    CallbackData,
    MessagesData,
    TextCommandsData,
    get_format_life_path_result,
)
from app.shared.state import UserStates
from app.shared.storage import user_storage
from app.shared.texts import get_text

router = Router()


async def process_life_path_number(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    user_data = user_storage.get_user(user_id)
    saved_birth_date = user_data.get("birth_date")
    cached_result = user_storage.get_cached_result(user_id)

    if saved_birth_date and cached_result and cached_result.get("birth_date") == saved_birth_date:
        if user_storage.can_view_cached_result(user_id):
            life_path = cached_result["life_path_result"]
            text = cached_result.get("text") or get_text(life_path, "life_path", user_id)
            result_text = get_format_life_path_result(life_path, text, saved_birth_date)
            
            # Обновляем стрик и проверяем достижения
            streak = update_user_activity(user_id, "life_path")
            unlocked_streak = check_streak_achievements(user_id, streak)
            unlocked_base = check_base_achievements(user_id)
            unlocked = unlocked_streak + unlocked_base
            
            await bot.send_message(message.chat.id, result_text, reply_markup=get_result_keyboard())
            user_storage.increment_repeat_view(user_id)
            
            # Показываем достижения, если разблокированы
            if unlocked:
                for achievement_id in unlocked:
                    name, desc = get_achievement_info(achievement_id)
                    achievement_text = MessagesData.STREAK_ACHIEVEMENT_UNLOCKED.format(
                        achievement_name=name,
                        achievement_description=desc
                    )
                    await bot.send_message(message.chat.id, achievement_text, reply_markup=get_back_to_main_keyboard())
            
            # Показываем персонализированную рекомендацию
            recommendation = get_personalized_recommendation(user_id, "life_path")
            if recommendation:
                from app.shared.keyboards import get_recommendation_keyboard
                rec_text, rec_action = recommendation
                await bot.send_message(message.chat.id, rec_text, reply_markup=get_recommendation_keyboard(rec_action))
            return

        await bot.send_message(
            message.chat.id,
            MessagesData.ERROR_VIEW_LIMIT_EXCEEDED,
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    if not user_storage.can_make_request(user_id):
        await bot.send_message(
            message.chat.id,
            MessagesData.ERROR_LIMIT_EXCEEDED,
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    await bot.send_message(
        message.chat.id,
        MessagesData.BIRTH_DATE_PROMPT,
        reply_markup=get_back_to_main_keyboard(),
    )
    await state.set_state(UserStates.waiting_for_birth_date)


@router.callback_query(F.data == CallbackData.LIFE_PATH_NUMBER)
async def life_path_callback(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    cached_result = user_storage.get_cached_result(user_id)

    if (
        cached_result
        and cached_result.get("life_path_result")
        and user_storage.can_view_cached_result(user_id)
    ):
        life_path = cached_result["life_path_result"]
        text = f"Ваше число судьбы: {life_path}"
        await callback_query.message.edit_text(text)
        user_storage.increment_repeat_view(user_id)
        return

    if not user_storage.can_make_request(user_id):
        await callback_query.message.edit_text(MessagesData.ERROR_LIMIT_EXCEEDED)
        return

    await callback_query.message.edit_text(MessagesData.BASE_BIRTH_DATE_PROMPT)
    await state.set_state(UserStates.waiting_for_birth_date)


@router.message(F.text == TextCommandsData.LIFE_PATH_NUMBER, StateFilter("*"))
@catch_errors()
async def life_path_command(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await process_life_path_number(message, state, bot)


@router.callback_query(F.data == CallbackData.LIFE_PATH_NUMBER_AGAIN)
async def life_path_again(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    await process_life_path_number(callback.message, state, bot)


@router.message(UserStates.waiting_for_birth_date)
@catch_errors()
async def handle_birth_date(message: Message, state: FSMContext):
    user_id = message.from_user.id
    birth_date = message.text.strip()

    if not validate_date(birth_date):
        await message.answer(MessagesData.ERROR_INVALID_DATE)
        return

    cached_result = user_storage.get_cached_result(user_id)

    if cached_result and cached_result.get("birth_date") == birth_date:
        if user_storage.can_view_cached_result(user_id):
            life_path = cached_result["life_path_result"]
            text = cached_result.get("text") or get_text(life_path, "life_path", user_id)
            result_text = get_format_life_path_result(life_path, text, birth_date)
            await message.answer(result_text, reply_markup=get_result_keyboard())
            user_storage.increment_repeat_view(user_id)
            await state.clear()
            return

        await message.answer(
            MessagesData.ERROR_VIEW_LIMIT_EXCEEDED,
            reply_markup=get_back_to_main_keyboard(),
        )
        await state.clear()
        return

    user_storage.set_birth_date(user_id, birth_date)
    life_path = calculate_life_path_number(birth_date)
    soul_number = calculate_soul_number(birth_date)
    text = get_text(life_path, "life_path", user_id)
    user_storage.save_daily_result(user_id, birth_date, life_path, soul_number, text)

    # Обновляем стрик и проверяем достижения
    streak = update_user_activity(user_id, "life_path")
    unlocked_streak = check_streak_achievements(user_id, streak)
    unlocked_base = check_base_achievements(user_id)
    unlocked = unlocked_streak + unlocked_base

    result_text = f"🔮 ВАШЕ ЧИСЛО СУДЬБЫ: {life_path}\n{text}\n📅 Дата: {birth_date}"
    await message.answer(result_text, reply_markup=get_result_keyboard())
    
    # Показываем достижения, если разблокированы
    if unlocked:
        for achievement_id in unlocked:
            name, desc = get_achievement_info(achievement_id)
            achievement_text = MessagesData.STREAK_ACHIEVEMENT_UNLOCKED.format(
                achievement_name=name,
                achievement_description=desc
            )
            await message.answer(achievement_text, reply_markup=get_back_to_main_keyboard())
    
    # Показываем персонализированную рекомендацию
    recommendation = get_personalized_recommendation(user_id, "life_path")
    if recommendation:
        from app.shared.keyboards import get_recommendation_keyboard
        rec_text, rec_action = recommendation
        await message.answer(rec_text, reply_markup=get_recommendation_keyboard(rec_action))
    
    await state.clear()

