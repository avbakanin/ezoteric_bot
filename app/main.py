import asyncio
import logging
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.features import setup_routers
from app.scheduler import get_scheduler
from app.settings import config

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


async def on_startup():
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
        from app.shared.storage import user_storage

        cleaned_count = user_storage.cleanup_old_data(30)
        logger.info(f"Очищено {cleaned_count} старых записей")

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")


async def on_shutdown():
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
        setup_routers(dp)

        logger.info("Обработчики зарегистрированы")

        # Запуск бота
        bot_instance = Bot(token=config.BOT_TOKEN)

        async def main_async():
            await on_startup()
            try:
                await dp.start_polling(bot_instance, skip_updates=True)
            finally:
                await on_shutdown()

        asyncio.run(main_async())

    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise


if __name__ == "__main__":
    main()
