from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from decorators import catch_errors
from keyboards.navigation import get_back_to_main_keyboard
from keyboards.results import get_result_keyboard
from messages import CallbackData, MessagesData, TextCommandsData, get_format_life_path_result
from state import UserStates
from storage import user_storage

from handlers.handlers import get_text

router = Router()


# ===========================
# Обработка Числа Судьбы - для каждой даты вычисляется всего раз, ответ запоминается и отправляется заново
# Премиум дает расширенное описание
# ===========================


# Общая функция для расчета (вынесена — вызывается и из команды, и из callback)
async def process_life_path_number(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    user_data = user_storage.get_user(user_id)
    saved_birth_date = user_data.get("birth_date")
    cached_result = user_storage.get_cached_result(user_id)

    # Если есть кэш и лимит просмотра позволяет — показываем сразу результат
    if saved_birth_date and cached_result and cached_result.get("birth_date") == saved_birth_date:
        if user_storage.can_view_cached_result(user_id):
            life_path = cached_result["life_path_result"]
            # Используем сохраненный текст из кэша или генерируем новый
            text = cached_result.get("text")
            if not text:
                text = get_text(life_path, "life_path", user_id)
            result_text = get_format_life_path_result(life_path, text, saved_birth_date)
            await bot.send_message(message.chat.id, result_text, reply_markup=get_result_keyboard())
            user_storage.increment_repeat_view(user_id)
            return
        else:
            await bot.send_message(
                message.chat.id,
                MessagesData.ERROR_VIEW_LIMIT_EXCEEDED,
                reply_markup=get_back_to_main_keyboard(),
            )
            return

    # Если лимиты запросов превышены
    if not user_storage.can_make_request(user_id):
        await bot.send_message(
            message.chat.id,
            MessagesData.ERROR_LIMIT_EXCEEDED,
            reply_markup=get_back_to_main_keyboard(),
        )
        return

    # Ставим состояние ожидания даты
    await bot.send_message(
        message.chat.id,
        MessagesData.BIRTH_DATE_PROMPT,
        reply_markup=get_back_to_main_keyboard(),
    )
    await state.set_state(UserStates.waiting_for_birth_date)


@router.callback_query(F.data == CallbackData.LIFE_PATH_NUMBER)
async def LIFE_PATH_NUMBER_handler(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    cached_result = user_storage.get_cached_result(user_id)

    # Лимиты и кэш
    if (
        cached_result
        and cached_result.get("life_path_result")
        and user_storage.can_view_cached_result(user_id)
    ):
        life_path = cached_result["life_path_result"]
        text = f"Ваше число судьбы: {life_path}"  # можно вызвать get_text
        await callback_query.message.edit_text(text)
        user_storage.increment_repeat_view(user_id)
        return

    if not user_storage.can_make_request(user_id):
        await callback_query.message.edit_text(MessagesData.ERROR_LIMIT_EXCEEDED)
        return

    # Нет сохраненной даты
    await callback_query.message.edit_text(MessagesData.BASE_BIRTH_DATE_PROMPT)
    await state.set_state(UserStates.waiting_for_birth_date)


# Хэндлер на кнопку "🧮 Рассчитать Число Судьбы"
@router.message(F.text == TextCommandsData.LIFE_PATH_NUMBER)
@catch_errors()
async def LIFE_PATH_NUMBER_command(message: Message, state: FSMContext, bot: Bot):
    await process_life_path_number(message, state, bot)


# Хэндлер на кнопку "📋 Посмотреть снова" — callback_data должен быть "view_again"
@router.callback_query(F.data == CallbackData.LIFE_PATH_NUMBER_AGAIN)
async def view_again_callback(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # Перенаправляем на ту же бизнес-логику
    await callback.answer()
    await process_life_path_number(callback.message, state, bot)
