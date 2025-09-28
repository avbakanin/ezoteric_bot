"""
Обработчики команд и сообщений бота через роутер
"""

import json
import logging
import random

from aiogram import Bot, F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from calculations import calculate_life_path_number, calculate_soul_number, validate_date
from decorators import catch_errors
from keyboards import (
    get_about_keyboard,
    get_back_to_main_keyboard,
    get_compatibility_result_keyboard,
    get_feedback_keyboard,
    get_main_menu_keyboard,
    get_premium_info_keyboard,
    get_profile_keyboard,
    get_result_keyboard,
)
from messages import MESSAGES, get_format_life_path_result, get_profile_text
from security import security_validator
from state import UserStates
from storage import user_storage

logger = logging.getLogger(__name__)

router = Router()

# Кэш для текстов чисел
_number_texts_cache = None


def get_number_texts():
    global _number_texts_cache
    if _number_texts_cache is None:
        try:
            with open("numbers.json", "r", encoding="utf-8") as f:
                _number_texts_cache = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке numbers.json: {e}")
            _number_texts_cache = {}
    return _number_texts_cache


def get_text(number: int, context: str, user_id: int) -> str:
    try:
        number_texts = get_number_texts()
        if str(number) not in number_texts or context not in number_texts[str(number)]:
            return "Информация временно недоступна."
        options = number_texts[str(number)][context]
        shown = user_storage.get_text_history(user_id)
        unused = [t for t in options if t not in shown]
        if not unused:
            unused = options
            # очищаем историю показанных текстов
            user_storage.update_user(user_id, text_history=[])
        chosen = random.choice(unused)
        user_storage.add_text_to_history(user_id, chosen)
        return chosen
    except Exception as e:
        logger.error(f"Ошибка в get_text: {e}")
        return "Произошла ошибка. Попробуйте позже."


# ===========================
# Основные команды
# ===========================


@router.message(Command("start"))
@catch_errors("Ошибка при запуске бота.")
async def start_command(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запустил бота")
    await message.answer(MESSAGES["START"], reply_markup=get_main_menu_keyboard())


# Общая функция для расчета (вынесена — вызывается и из команды, и из callback)
async def process_calculate_number(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    user_data = user_storage.get_user(user_id)
    saved_birth_date = user_data.get("birth_date")
    cached_result = user_storage.get_cached_result(user_id)

    # Если есть кэш и лимит просмотра позволяет — показываем сразу результат
    if saved_birth_date and cached_result and cached_result.get("birth_date") == saved_birth_date:
        if user_storage.can_view_cached_result(user_id):
            life_path = cached_result["life_path_result"]
            text = get_text(life_path, "life_path", user_id)
            result_text = get_format_life_path_result(life_path, text, saved_birth_date)
            await bot.send_message(message.chat.id, result_text, reply_markup=get_result_keyboard())
            user_storage.increment_repeat_view(user_id)
            return
        else:
            await bot.send_message(
                message.chat.id,
                MESSAGES["ERROR_VIEW_LIMIT_EXCEEDED"],
                reply_markup=get_back_to_main_keyboard(),
            )
            return

    # Если лимиты запросов превышены
    if not user_storage.can_make_request(user_id):
        await bot.send_message(
            message.chat.id,
            MESSAGES["ERROR_LIMIT_EXCEEDED"],
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    # Ставим состояние ожидания даты
    await bot.send_message(
        message.chat.id,
        MESSAGES["BIRTH_DATE_PROMPT"],
        reply_markup=get_back_to_main_keyboard(),
    )
    await state.set_state(UserStates.waiting_for_birth_date)


# Хэндлер на кнопку "🧮 Рассчитать Число Судьбы"
@router.message(lambda m: m.text == "🧮 Рассчитать Число Судьбы")
@catch_errors()
async def calculate_number_command(message: types.Message, state: FSMContext, bot: Bot):
    await process_calculate_number(message, state, bot)


# Хэндлер на кнопку "📋 Посмотреть снова" — callback_data должен быть "view_again"
@router.callback_query(F.data == "view_soul_number_again")
async def view_again_callback(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    # Перенаправляем на ту же бизнес-логику
    await callback.answer()
    await process_calculate_number(callback.message, state, bot)


# ===========================
# Обработка даты рождения
# ===========================


@router.message(UserStates.waiting_for_birth_date)
@catch_errors()
async def handle_birth_date(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    birth_date = message.text.strip()

    if not security_validator.rate_limit_check(user_id, "birth_date"):
        await message.answer(
            MESSAGES["RATE_LIMIT_BIRTH_DATE_MSG"], reply_markup=get_back_to_main_keyboard()
        )
        return

    if not validate_date(birth_date):
        await message.answer(MESSAGES["ERROR_INVALID_DATE"])
        return

    user_data = user_storage.get_user(user_id)
    cached_result = user_storage.get_cached_result(user_id)

    # Проверяем, хочет ли пользователь использовать сохраненную дату (точное совпадение)
    if cached_result and cached_result.get("birth_date") == birth_date:
        if user_storage.can_view_cached_result(user_id):
            life_path = cached_result["life_path_result"]
            text = get_text(life_path, "life_path", user_id)
            result_text = get_format_life_path_result(life_path, text, birth_date)
            await message.answer(result_text, reply_markup=get_result_keyboard())
            user_storage.increment_repeat_view(user_id)
            await state.clear()
            return
        else:
            await message.answer(
                MESSAGES["ERROR_VIEW_LIMIT_EXCEEDED"], reply_markup=get_back_to_main_keyboard()
            )
            await state.clear()
            return

    # Если дата новая, сохраняем и рассчитываем
    user_storage.set_birth_date(user_id, birth_date)
    life_path = calculate_life_path_number(birth_date)
    soul_number = calculate_soul_number(birth_date)
    # daily_number не используется — ранее убрал вычисление
    user_storage.save_daily_result(user_id, birth_date, life_path, soul_number)

    text = get_text(life_path, "life_path", user_id)
    result_text = f"🔮 ВАШЕ ЧИСЛО СУДЬБЫ: {life_path}\n{text}\n📅 Дата: {birth_date}"
    await message.answer(result_text, reply_markup=get_result_keyboard())
    await state.clear()


# ===========================
# Совместимость
# ===========================


@router.message(lambda m: m.text == "💑 Проверить Совместимость")
@catch_errors()
async def compatibility_command(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите первую дату рождения (ДД.ММ.ГГГГ):", reply_markup=get_back_to_main_keyboard()
    )
    await state.set_state(UserStates.waiting_for_first_date)


@router.message(UserStates.waiting_for_first_date)
@catch_errors()
async def handle_first_date(message: types.Message, state: FSMContext):
    first_date = message.text.strip()
    if not validate_date(first_date):
        await message.answer(MESSAGES["ERROR_INVALID_DATE"])
        return
    await state.update_data(first_date=first_date)
    await message.answer(
        "Введите вторую дату рождения (ДД.ММ.ГГГГ):", reply_markup=get_back_to_main_keyboard()
    )
    await state.set_state(UserStates.waiting_for_second_date)


@router.message(UserStates.waiting_for_second_date)
@catch_errors()
async def handle_second_date(message: types.Message, state: FSMContext):
    second_date = message.text.strip()
    if not validate_date(second_date):
        await message.answer(MESSAGES["ERROR_INVALID_DATE"])
        return

    data = await state.get_data()
    first_date = data.get("first_date")
    first_number = calculate_life_path_number(first_date)
    second_number = calculate_life_path_number(second_date)

    score = 3
    description = "Низкая совместимость. Потребуется много усилий."
    diff = abs(first_number - second_number)
    if diff == 0:
        score, description = 9, "Идеальная совместимость! Вы очень похожи по характеру."
    elif diff <= 2:
        score, description = 7, "Хорошая совместимость. Вы дополняете друг друга."
    elif diff <= 4:
        score, description = 5, "Средняя совместимость. Требуется понимание и компромиссы."

    result_text = (
        f"💑 СОВМЕСТИМОСТЬ: {first_number} и {second_number}\nОценка: {score}/9\n{description}"
    )
    await message.answer(result_text, reply_markup=get_compatibility_result_keyboard())
    await state.clear()


# ===========================
# Профиль и инфо
# ===========================


@router.message(lambda m: m.text == "📊 Мой Профиль")
@catch_errors()
async def profile_command(message: types.Message):
    user_id = message.from_user.id
    user_data = user_storage.get_user(user_id)
    usage_stats = user_storage.get_usage_stats(user_id)
    subscription_status = "Premium" if user_data["subscription"]["active"] else "Бесплатный"
    cached_result = user_storage.get_cached_result(user_id)
    has_cached = cached_result is not None
    profile_text = get_profile_text(
        user_id=user_id,
        life_path_number=user_data.get("life_path_number", "не рассчитано"),
        subscription_status=subscription_status,
        usage_stats=usage_stats,
        has_cached=bool(has_cached),
    )
    has_calculated = user_data.get("birth_date") is not None
    await message.answer(profile_text, reply_markup=get_profile_keyboard(has_calculated))


@router.message(lambda m: m.text == "ℹ️ О боте")
@catch_errors()
async def about_command(message: types.Message):
    await message.answer(MESSAGES["ABOUT_DESCRIPTION"], reply_markup=get_about_keyboard())


@router.message(Command("menu"))
@catch_errors()
async def menu_command(message: types.Message):
    await message.answer("🔮 Главное меню", reply_markup=get_main_menu_keyboard())


@router.message(Command("help"))
@catch_errors()
async def help_command(message: types.Message):
    await message.answer(MESSAGES["HELP"])


@router.message()
@catch_errors()
async def unknown_message(message: types.Message):
    await message.answer(MESSAGES["UNKNOWN"])


@router.message(Command("premium_info"))
@catch_errors()
async def premium_info_command(message: types.Message):
    await message.answer(MESSAGES["PREMIUM_INFO_TEXT"], reply_markup=get_premium_info_keyboard())


@router.message(Command("feedback"))
@catch_errors()
async def feedback_command(message: types.Message, state: FSMContext):
    await message.answer(
        "📝 ОТЗЫВЫ И ПРЕДЛОЖЕНИЯ\nВаше мнение очень важно!", reply_markup=get_feedback_keyboard()
    )
    await state.set_state(UserStates.waiting_for_feedback)


@router.message(lambda m: m.text == "📝 Оставить отзыв")
@catch_errors()
async def feedback_button_command(message: types.Message, state: FSMContext):
    await message.answer(MESSAGES["FEEDBACK_PROMPT"], reply_markup=get_feedback_keyboard())
    await state.set_state(UserStates.waiting_for_feedback)


@router.message(UserStates.waiting_for_feedback)
@catch_errors()
async def handle_feedback(message: types.Message, state: FSMContext):
    feedback_text = message.text.strip()
    user_id = message.from_user.id

    if not security_validator.rate_limit_check(user_id, "feedback"):
        await message.answer(MESSAGES["ERROR_FEEDBACK_LIMIT"], reply_markup=get_back_to_main_keyboard())
        await state.clear()
        return

    sanitized_text = security_validator.sanitize_text(feedback_text)

    # Сохранение в базу или отправка админу
    await message.answer(MESSAGES["FEEDBACK_SUCCESS"], reply_markup=get_feedback_keyboard())
    await state.clear()
