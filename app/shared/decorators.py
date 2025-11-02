import logging
from functools import wraps

from aiogram import types

from .keyboards import get_back_to_main_keyboard

logger = logging.getLogger(__name__)


def catch_errors(default_message: str = "Произошла ошибка. Попробуйте позже."):
    """
    Декоратор для обработки ошибок в хендлерах.
    Поддерживает как Message, так и CallbackQuery.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
                
                # Пытаемся получить объект Message или CallbackQuery для ответа
                for arg in args:
                    if isinstance(arg, types.Message):
                        await arg.answer(default_message, reply_markup=get_back_to_main_keyboard())
                        break
                    elif isinstance(arg, types.CallbackQuery):
                        try:
                            await arg.answer(default_message, show_alert=True)
                        except Exception:
                            # Если не удалось показать alert, пытаемся отправить сообщение
                            try:
                                await arg.message.answer(default_message, reply_markup=get_back_to_main_keyboard())
                            except Exception:
                                pass
                        break
                # Если не найдено ни Message, ни CallbackQuery, просто логируем
                return None

        return wrapper

    return decorator
