from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """
    Состояния пользователя для FSM
    """

    waiting_for_birth_date = State()
    waiting_for_first_date = State()
    waiting_for_second_date = State()
    waiting_for_feedback = State()
    waiting_for_diary_observation = State()
    waiting_for_diary_category = State()
    waiting_for_yes_no_question = State()
    waiting_for_name_number = State()
    waiting_for_tarot_question = State()


class NatalProfileStates(StatesGroup):
    """Состояния диалога сбора натальных данных."""

    confirm_age = State()
    waiting_for_age = State()
    waiting_for_birth_date = State()
    waiting_for_birth_time = State()
    waiting_for_place = State()
    confirm_place = State()
    waiting_for_timezone = State()
