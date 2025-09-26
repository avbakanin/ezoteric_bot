"""
Основной файл нумерологического бота
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

from settings import config
from handlers import (
    start_command,
    handle_birth_date,
    calculate_number_command,
    compatibility_command,
    handle_first_date,
    handle_second_date,
    profile_command,
    about_command,
    menu_command,
    premium_info_command,
    feedback_command,
    handle_feedback,
    handle_diary_observation,
    handle_callback_query,
    help_command,
    unknown_message,
    UserStates
)
from scheduler import get_scheduler


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация диспетчера
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


def register_handlers():
    """
    Регистрация обработчиков
    """
    # Команды
    dp.message.register(start_command, Command('start'))
    dp.message.register(menu_command, Command('menu'))
    dp.message.register(premium_info_command, Command('premium_info'))
    dp.message.register(feedback_command, Command('feedback'))
    dp.message.register(help_command, Command('help'))
    
    # Обработчики состояний
    dp.message.register(handle_birth_date, UserStates.waiting_for_birth_date)
    dp.message.register(handle_first_date, UserStates.waiting_for_first_date)
    dp.message.register(handle_second_date, UserStates.waiting_for_second_date)
    dp.message.register(handle_feedback, UserStates.waiting_for_feedback)
    dp.message.register(handle_diary_observation, UserStates.waiting_for_diary_observation)
    
    # Обработчики текстовых команд (главное меню)
    dp.message.register(calculate_number_command, lambda m: m.text == "🧮 Рассчитать Число Судьбы")
    dp.message.register(compatibility_command, lambda m: m.text == "💑 Проверить Совместимость")
    dp.message.register(profile_command, lambda m: m.text == "📊 Мой Профиль")
    dp.message.register(about_command, lambda m: m.text == "ℹ️ О боте")
    
    # Callback обработчики
    dp.callback_query.register(handle_callback_query)
    
    # Обработчик неизвестных сообщений
    dp.message.register(unknown_message)


# Удаляем старые функции, теперь используем NotificationScheduler


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
        register_handlers()
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


if __name__ == '__main__':
    main()