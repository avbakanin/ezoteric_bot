"""
Обработчик обратной связи
"""

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from decorators import catch_errors
from keyboards import get_back_to_main_keyboard, get_feedback_keyboard
from messages import CallbackData, CommandsData, MessagesData, TextCommandsData
from security import security_validator
from state import UserStates

router = Router()


@router.callback_query(
    F.data.in_(
        [
            CallbackData.FEEDBACK,
            CallbackData.SUGGESTION,
            CallbackData.REPORT_BUG,
            CallbackData.LEAVE_FEEDBACK,
        ]
    )
)
async def feedback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.edit_text(MessagesData.FEEDBACK_CB)
    await state.set_state(UserStates.waiting_for_feedback)


async def feedback_base_handler(message: types.Message, state: FSMContext):
    await message.answer(MessagesData.FEEDBACK, reply_markup=get_feedback_keyboard())
    await state.set_state(UserStates.waiting_for_feedback)


@router.message(Command(CommandsData.FEEDBACK))
@catch_errors()
async def feedback_command(message: types.Message, state: FSMContext):
    feedback_base_handler(message=message, state=state)


@router.message(F.text == TextCommandsData.FEEDBACK)
@catch_errors()
async def feedback_button_command(message: types.Message, state: FSMContext):
    feedback_base_handler(message=message, state=state)


@router.message(UserStates.waiting_for_feedback)
@catch_errors()
async def handle_feedback(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if not security_validator.rate_limit_check(user_id, "feedback"):
        await message.answer(
            MessagesData.ERROR_FEEDBACK_LIMIT, reply_markup=get_back_to_main_keyboard()
        )
        await state.clear()
        return

    # Сохранение в базу или отправка админу
    # feedback_text = message.text.strip()  # Будет использовано при реализации сохранения
    await message.answer(MessagesData.FEEDBACK_SUCCESS, reply_markup=get_feedback_keyboard())
    await state.clear()
