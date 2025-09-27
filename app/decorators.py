"""
Декораторы для обработки ошибок в handlers
"""

import logging
from functools import wraps

from aiogram.types import CallbackQuery, Message
from user_storage import user_storage

logger = logging.getLogger(__name__)


def catch_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в обработчике {func.__name__}: {e}", exc_info=True)
            for arg in args:
                if isinstance(arg, (Message, CallbackQuery)):
                    await arg.answer("❌ Произошла ошибка. Попробуйте позже.")
                    break

    return wrapper


def subscription_required(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        user = user_storage.get_user(message.from_user.id)
        if not user["subscription"]["active"]:
            await message.answer("Эта функция доступна только для подписчиков премиум.")
            return
        return await func(message, *args, **kwargs)

    return wrapper


def daily_limit(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if not user_storage.can_make_request(message.from_user.id):
            await message.answer("Лимит бесплатных запросов исчерпан.")
            return
        return await func(message, *args, **kwargs)

    return wrapper
