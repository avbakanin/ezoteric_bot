"""
Основной файл нумерологического бота
"""

import asyncio
import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from scheduler import get_scheduler
from settings import config

from handlers.back import router as back_router
from handlers.features import router as features_router
from handlers.handlers import router as handlers_router
from handlers.premium import router as premium_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Инициализация диспетчера
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


async def on_startup(dp):
    """
    Функция, выполняемая при запуске бота
    """
    logger.info("Бот запущен!")

    try:
        # Запускаем планировщик уведомлений
        bot_instance = Bot(token=config.BOT_TOKEN)
        notification_scheduler = get_scheduler(bot_instance)
        asyncio.create_task(notification_scheduler.start())
        logger.info("Планировщик уведомлений запущен")

        # Очищаем старые данные (старше 30 дней)
        from storage import user_storage

        cleaned_count = user_storage.cleanup_old_data(30)
        logger.info(f"Очищено {cleaned_count} старых записей")

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")


async def on_shutdown(dp):
    """
    Функция, выполняемая при остановке бота
    """
    logger.info("Бот остановлен!")

    try:
        # Останавливаем планировщик уведомлений
        bot_instance = Bot(token=config.BOT_TOKEN)
        notification_scheduler = get_scheduler(bot_instance)
        notification_scheduler.stop()
        logger.info("Планировщик уведомлений остановлен")

    except Exception as e:
        logger.error(f"Ошибка при остановке бота: {e}")


def main():
    """
    Главная функция
    """
    try:

        dp.include_router(handlers_router)
        dp.include_router(back_router)
        dp.include_router(features_router)
        dp.include_router(premium_router)
        logger.info("Обработчики зарегистрированы")

        # Запуск бота
        bot_instance = Bot(token=config.BOT_TOKEN)

        async def main_async():
            await on_startup(dp)
            try:
                await dp.start_polling(bot_instance, skip_updates=True)
            finally:
                await on_shutdown(dp)

        asyncio.run(main_async())

    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise


if __name__ == "__main__":
    main()
