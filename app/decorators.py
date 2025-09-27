import logging
from functools import wraps

from aiogram import types
from keyboards import get_back_to_main_keyboard

logger = logging.getLogger(__name__)


def catch_errors(default_message: str = "Произошла ошибка. Попробуйте позже."):
    """
    Декоратор для обработки ошибок в хендлерах
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
                # Пытаемся получить объект Message для ответа
                for arg in args:
                    if isinstance(arg, types.Message):
                        await arg.answer(default_message, reply_markup=get_back_to_main_keyboard())
                        break
                # Если нет Message, просто логируем
                return None

        return wrapper

    return decorator
