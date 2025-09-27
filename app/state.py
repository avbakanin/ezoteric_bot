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
