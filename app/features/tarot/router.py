"""Роутер для карт Таро."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.shared.decorators import catch_errors
from app.shared.formatters import format_today_iso
from app.shared.helpers import (
    check_base_achievements,
    check_daily_challenge_completion,
    check_streak_achievements,
    get_achievement_info,
    get_personalized_recommendation,
    is_premium,
    update_user_activity,
)
from app.shared.keyboards import (
    get_back_to_main_keyboard,
    get_back_to_tarot_keyboard,
    get_premium_info_keyboard,
    get_spreads_keyboard,
    get_tarot_question_keyboard,
)
from app.shared.messages import CallbackData, CommandsData, MessagesData, TextCommandsData
from app.shared.security import security_validator
from app.shared.state import UserStates
from app.shared.storage import user_storage
from app.shared.tarot_service import (
    TarotCard,
    detect_context_from_question,
    draw_random_cards,
    format_yes_no_answer,
    get_available_spreads,
    get_card_interpretation,
    get_spread_info,
    interpret_spread,
)

logger = logging.getLogger(__name__)
router = Router()


async def _show_spreads_selection(send_func, user_id: int):
    """Показывает выбор раскладов."""
    is_premium_user = is_premium(user_id)
    available_spreads = get_available_spreads(is_premium=is_premium_user)

    if not available_spreads:
        await send_func(
            "⚠️ Расклады временно недоступны. Попробуйте позже.",
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    keyboard = get_spreads_keyboard(available_spreads, is_premium=is_premium_user)
    await send_func(MessagesData.TAROT_INTRO, reply_markup=keyboard)


@router.message(Command(CommandsData.TAROT), StateFilter("*"))
@catch_errors()
async def tarot_command(message: Message, state: FSMContext):
    """Обработчик команды /tarot."""
    await state.clear()
    await _show_spreads_selection(message.answer, message.from_user.id)


@router.message(F.text == TextCommandsData.TAROT, StateFilter("*"))
@catch_errors()
async def tarot_button(message: Message, state: FSMContext):
    """Обработчик кнопки Таро."""
    await state.clear()
    await _show_spreads_selection(message.answer, message.from_user.id)


@router.callback_query(F.data == CallbackData.TAROT_SELECT_SPREAD)
@catch_errors()
async def tarot_select_spread_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик возврата к выбору расклада."""
    await state.clear()
    user_id = callback.from_user.id
    is_premium_user = is_premium(user_id)
    available_spreads = get_available_spreads(is_premium=is_premium_user)
    keyboard = get_spreads_keyboard(available_spreads, is_premium=is_premium_user)
    await callback.message.edit_text(MessagesData.TAROT_INTRO, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == CallbackData.TAROT_PREMIUM_SPREADS)
@catch_errors()
async def tarot_premium_spreads_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик нажатия на Premium расклады."""
    user_id = callback.from_user.id
    is_premium_user = is_premium(user_id)

    if not is_premium_user:
        await callback.message.answer(
            MessagesData.TAROT_PREMIUM_REQUIRED,
            reply_markup=get_premium_info_keyboard(),
        )
        await callback.answer("Этот расклад доступен в Premium", show_alert=True)
        return

    # Показываем Premium расклады
    available_spreads = get_available_spreads(is_premium=True)
    premium_spreads = {
        k: v for k, v in available_spreads.items() if v.get("premium_only", False)
    }

    keyboard = get_spreads_keyboard(premium_spreads, is_premium=True)
    await callback.message.edit_text(
        "💎 PREMIUM РАСКЛАДЫ\n\nВыберите расклад для детального анализа:",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CallbackData.TAROT_SPREAD_PREFIX))
@catch_errors()
async def spread_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора конкретного расклада - запрашивает вопрос."""
    user_id = callback.from_user.id
    is_premium_user = is_premium(user_id)

    spread_key = callback.data.replace(CallbackData.TAROT_SPREAD_PREFIX, "", 1)
    spread_info = get_spread_info(spread_key)

    if not spread_info:
        await callback.answer("Расклад не найден.", show_alert=True)
        return

    # Проверка Premium
    if spread_info.get("premium_only") and not is_premium_user:
        await callback.message.answer(
            MessagesData.TAROT_PREMIUM_REQUIRED,
            reply_markup=get_premium_info_keyboard(),
        )
        await callback.answer("Этот расклад доступен в Premium", show_alert=True)
        return

    # Для расклада Да/Нет сразу выполняем без вопроса
    if spread_key == "yes_no":
        await callback.answer()
        await _perform_spread(callback.message.answer, user_id, spread_key, spread_info, None)
        return

    # Сохраняем выбранный расклад в состояние и просим вопрос
    await state.update_data(selected_spread_key=spread_key)
    await state.set_state(UserStates.waiting_for_tarot_question)
    
    keyboard = get_tarot_question_keyboard()
    
    spread_name = spread_info.get("name", "Расклад")
    await callback.message.edit_text(
        f"🎴 Выбран расклад: **{spread_name}**\n\n"
        f"{MessagesData.TAROT_QUESTION_PROMPT}",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == CallbackData.TAROT_QUESTION_SKIP)
@catch_errors()
async def tarot_question_skip(callback: CallbackQuery, state: FSMContext):
    """Обработчик пропуска вопроса."""
    user_data = await state.get_data()
    spread_key = user_data.get("selected_spread_key")
    
    if not spread_key:
        await callback.answer("Ошибка: расклад не выбран.", show_alert=True)
        await state.clear()
        return
    
    spread_info = get_spread_info(spread_key)
    if not spread_info:
        await callback.answer("Расклад не найден.", show_alert=True)
        await state.clear()
        return
    
    await state.clear()
    await callback.answer()
    await _perform_spread(callback.message.answer, callback.from_user.id, spread_key, spread_info, None)


@router.message(UserStates.waiting_for_tarot_question)
@catch_errors()
async def handle_tarot_question(message: Message, state: FSMContext):
    """Обработчик вопроса для расклада."""
    question = message.text.strip()
    
    if not question or not security_validator.validate_user_input(question):
        await message.answer("❌ Некорректный вопрос. Попробуйте еще раз или нажмите кнопку 'Пропустить'.")
        return
    
    user_data = await state.get_data()
    spread_key = user_data.get("selected_spread_key")
    
    if not spread_key:
        await message.answer("❌ Ошибка: расклад не выбран. Начните заново.")
        await state.clear()
        return
    
    spread_info = get_spread_info(spread_key)
    if not spread_info:
        await message.answer("❌ Расклад не найден.")
        await state.clear()
        return
    
    sanitized_question = security_validator.sanitize_text(question)
    await state.clear()
    await _perform_spread(message.answer, message.from_user.id, spread_key, spread_info, sanitized_question)


async def _perform_spread(send_func, user_id: int, spread_key: str, spread_info: dict, question: str | None):

    # Кэширование для раскладов, которые должны быть одинаковыми в течение дня
    today = format_today_iso()
    cacheable_spreads = ["single_card", "daily_three"]  # Расклады, которые кэшируются на день

    # Проверяем кэш для кэшируемых раскладов
    cached_result = None
    if spread_key in cacheable_spreads:
        cache = user_storage.get_tarot_cache(user_id, spread_key)
        if cache and cache.get("date") == today:
            cached_result = cache

    # Выбираем карты
    card_count = spread_info.get("card_count", 1)
    use_only_major = spread_info.get("use_only_major", False)

    try:
        # Если есть кэш, используем его
        if cached_result:
            # Восстанавливаем карты из кэша (упрощенная версия - только для отображения)
            cards_data = cached_result.get("cards", [])
            cards = []
            for card_data in cards_data:
                cards.append(
                    TarotCard(
                        key=card_data["key"],
                        name=card_data["name"],
                        emoji=card_data["emoji"],
                        card_type=card_data["card_type"],
                        suit=card_data.get("suit"),
                        is_reversed=card_data["is_reversed"],
                    )
                )
            interpretations_data = cached_result.get("interpretations", [])
        else:
            cards = draw_random_cards(card_count, use_only_major=use_only_major)

        if not cards:
            await send_func("❌ Ошибка при выборе карт. Попробуйте позже.", reply_markup=get_back_to_tarot_keyboard())
            return

        # Формируем результат
        spread_name = spread_info.get("name", "Расклад")
        result_text = MessagesData.TAROT_RESULT_HEADER.format(spread_name=spread_name)

        # Определяем контекст интерпретации из вопроса
        context = detect_context_from_question(question)
        
        # Интерпретируем расклад (если не из кэша)
        if cached_result:
            # Используем интерпретации из кэша
            interpretations = interpretations_data
        else:
            # Используем контекст для интерпретации
            interpretations = interpret_spread(cards, spread_key, context=context)
            # Сохраняем в кэш для кэшируемых раскладов
            if spread_key in cacheable_spreads:
                cards_data = [
                    {
                        "key": card.key,
                        "name": card.name,
                        "emoji": card.emoji,
                        "card_type": card.card_type,
                        "suit": card.suit,
                        "is_reversed": card.is_reversed,
                    }
                    for card in cards
                ]
                # Сохраняем интерпретации как словари (без объектов TarotCard)
                interpretations_for_cache = []
                for item in interpretations:
                    interpretations_for_cache.append({
                        "position_name": item["position_name"],
                        "position_meaning": item.get("position_meaning", ""),
                        "card": {
                            "key": item["card"].key,
                            "name": item["card"].name,
                            "emoji": item["card"].emoji,
                            "card_type": item["card"].card_type,
                            "suit": item["card"].suit,
                            "is_reversed": item["card"].is_reversed,
                        },
                        "interpretation": item["interpretation"],
                    })
                user_storage.set_tarot_cache(
                    user_id,
                    spread_key,
                    today,
                    {
                        "cards": cards_data,
                        "interpretations": interpretations_for_cache,
                    },
                )

        # Специальная обработка для расклада Да/Нет
        if spread_key == "yes_no":
            card = cards[0]
            answer, explanation = format_yes_no_answer(card)
            direction = " (перевернутая)" if card.is_reversed else ""
            result_text += (
                f"🃏 Выпала карта: {card.emoji} {card.name}{direction}\n\n"
                f"{MessagesData.TAROT_YES_NO_ANSWER.format(answer=answer, explanation=explanation)}"
            )
        # Специальная обработка для карты дня
        elif spread_key == "single_card":
            item = interpretations[0] if interpretations else None
            if item:
                card_data = item.get("card") if isinstance(item.get("card"), dict) else item["card"]
                if isinstance(card_data, dict):
                    card = TarotCard(
                        key=card_data["key"],
                        name=card_data["name"],
                        emoji=card_data["emoji"],
                        card_type=card_data["card_type"],
                        suit=card_data.get("suit"),
                        is_reversed=card_data["is_reversed"],
                    )
                else:
                    card = card_data
                direction = "перевернутая" if card.is_reversed else "прямая"
                interpretation = item.get("interpretation", "")
                
                if not interpretation:
                    # Если интерпретация отсутствует, получаем её заново
                    context = detect_context_from_question(question)
                    interpretation = get_card_interpretation(card, context=context)
                
                result_text += (
                    f"{MessagesData.TAROT_CARD_DAY.format(card_name=card.name, card_emoji=card.emoji)}\n"
                    f"Положение: {direction}\n\n"
                    f"{interpretation}"
                )
        # Обычный расклад
        else:
            for i, item in enumerate(interpretations):
                card_data = item.get("card") if isinstance(item.get("card"), dict) else item["card"]
                if isinstance(card_data, dict):
                    card = TarotCard(
                        key=card_data["key"],
                        name=card_data["name"],
                        emoji=card_data["emoji"],
                        card_type=card_data["card_type"],
                        suit=card_data.get("suit"),
                        is_reversed=card_data["is_reversed"],
                    )
                else:
                    card = card_data
                direction = "перевернутая" if card.is_reversed else "прямая"
                interpretation = item.get("interpretation", "")
                
                # Если интерпретация отсутствует или пустая, получаем её заново
                if not interpretation:
                    context = detect_context_from_question(question)
                    interpretation = get_card_interpretation(card, context=context)
                
                result_text += (
                    f"\n📌 {item['position_name']}\n"
                    f"🃏 {card.emoji} {card.name} ({direction})\n"
                )
                if item.get("position_meaning"):
                    result_text += f"💫 {item['position_meaning']}\n"
                result_text += f"{interpretation}\n\n"

        # Добавляем вопрос в результат, если был задан
        if question:
            result_text = f"💭 Ваш вопрос: {question}\n\n" + result_text

        # Сохраняем в историю
        cards_for_history = [
            {
                "key": card.key,
                "name": card.name,
                "emoji": card.emoji,
                "card_type": card.card_type,
                "suit": card.suit,
                "is_reversed": card.is_reversed,
            }
            for card in cards
        ]
        interpretations_for_history = [
            {
                "position_name": item["position_name"],
                "position_meaning": item.get("position_meaning", ""),
                "card": {
                    "key": item["card"].key if hasattr(item["card"], "key") else item["card"].get("key"),
                    "name": item["card"].name if hasattr(item["card"], "name") else item["card"].get("name"),
                },
                "interpretation": item["interpretation"],
            }
            for item in interpretations
        ]
        user_storage.add_tarot_reading(
            user_id,
            spread_key,
            question,
            cards_for_history,
            interpretations_for_history,
        )
        
        # Обновляем стрик и статистику
        streak = update_user_activity(user_id, "tarot")
        user_storage.increment_stat(user_id, "total_tarot_readings", "tarot")
        unlocked_streak = check_streak_achievements(user_id, streak)
        unlocked_base = check_base_achievements(user_id)
        unlocked = unlocked_streak + unlocked_base

        keyboard = get_back_to_tarot_keyboard()
        await send_func(result_text, reply_markup=keyboard)
        
        # Показываем достижения, если разблокированы
        if unlocked:
            from app.shared.keyboards import get_back_to_main_keyboard
            from app.shared.messages import MessagesData
            for achievement_id in unlocked:
                name, desc = get_achievement_info(achievement_id)
                achievement_text = MessagesData.STREAK_ACHIEVEMENT_UNLOCKED.format(
                    achievement_name=name,
                    achievement_description=desc
                )
                await send_func(achievement_text, reply_markup=get_back_to_main_keyboard())
        
        # Проверяем выполнение ежедневного задания
        is_completed, challenge_data = check_daily_challenge_completion(user_id, "tarot")
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
            await send_func(completion_text)
        
        # Показываем персонализированную рекомендацию
        recommendation = get_personalized_recommendation(user_id, "tarot")
        if recommendation:
            from app.shared.keyboards import get_recommendation_keyboard
            rec_text, rec_action = recommendation
            await send_func(rec_text, reply_markup=get_recommendation_keyboard(rec_action))

    except Exception as e:
        logger.error("Ошибка при выполнении расклада: %s", e, exc_info=True)
        await send_func("❌ Произошла ошибка при выполнении расклада. Попробуйте позже.", reply_markup=get_back_to_tarot_keyboard())


@router.callback_query(F.data == CallbackData.TAROT_HISTORY)
@catch_errors()
async def tarot_history_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик просмотра истории раскладов."""
    await state.clear()
    user_id = callback.from_user.id
    
    history = user_storage.get_tarot_history(user_id, limit=20)
    
    if not history:
        await callback.message.answer(
            MessagesData.TAROT_HISTORY_EMPTY,
            reply_markup=get_back_to_tarot_keyboard(),
        )
        await callback.answer()
        return
    
    # Формируем текст истории
    result_text = MessagesData.TAROT_HISTORY_TITLE.format(count=len(history))
    
    for reading in reversed(history):  # Показываем от новых к старым
        spread_key = reading.get("spread_key", "unknown")
        spread_info = get_spread_info(spread_key)
        spread_name = spread_info.get("name", "Расклад") if spread_info else spread_key
        
        date = reading.get("date", "")
        question = reading.get("question")
        cards = reading.get("cards", [])
        
        cards_text = ", ".join([f"{c.get('emoji', '🃏')} {c.get('name', '?')}" for c in cards[:3]])
        if len(cards) > 3:
            cards_text += f" +{len(cards) - 3}"
        
        question_line = ""
        if question:
            question_line = MessagesData.TAROT_HISTORY_QUESTION.format(question=question)
        
        result_text += MessagesData.TAROT_HISTORY_ITEM.format(
            date=date,
            spread_name=spread_name,
            question_line=question_line,
            cards=cards_text,
        )
    
    await callback.message.answer(result_text, reply_markup=get_back_to_tarot_keyboard())
    await callback.answer()


