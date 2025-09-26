"""
Основной файл нумерологического бота
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

from config import API_TOKEN
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
    handle_callback_query,
    help_command,
    unknown_message,
    UserStates
)
from scheduler import get_scheduler


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


def register_handlers():
    """
    Регистрация обработчиков
    """
    # Команды
    dp.register_message_handler(start_command, commands=['start'])
    dp.register_message_handler(menu_command, commands=['menu'])
    dp.register_message_handler(premium_info_command, commands=['premium_info'])
    dp.register_message_handler(feedback_command, commands=['feedback'])
    dp.register_message_handler(help_command, commands=['help'])
    
    # Обработчики состояний
    dp.register_message_handler(handle_birth_date, state=UserStates.waiting_for_birth_date)
    dp.register_message_handler(handle_first_date, state=UserStates.waiting_for_first_date)
    dp.register_message_handler(handle_second_date, state=UserStates.waiting_for_second_date)
    dp.register_message_handler(handle_feedback, state=UserStates.waiting_for_feedback)
    
    # Обработчики текстовых команд (главное меню)
    dp.register_message_handler(calculate_number_command, text="🧮 Рассчитать Число Судьбы")
    dp.register_message_handler(compatibility_command, text="💑 Проверить Совместимость")
    dp.register_message_handler(profile_command, text="📊 Мой Профиль")
    dp.register_message_handler(about_command, text="ℹ️ О боте")
    
    # Callback обработчики
    dp.register_callback_query_handler(handle_callback_query)
    
    # Обработчик неизвестных сообщений
    dp.register_message_handler(unknown_message)


# Удаляем старые функции, теперь используем NotificationScheduler


async def on_startup(dp):
    """
    Функция, выполняемая при запуске бота
    """
    logger.info("Бот запущен!")
    
    # Запускаем планировщик уведомлений
    notification_scheduler = get_scheduler(bot)
    asyncio.create_task(notification_scheduler.start())
    
    # Очищаем старые данные (старше 30 дней)
    from storage import user_storage
    user_storage.cleanup_old_data(30)


async def on_shutdown(dp):
    """
    Функция, выполняемая при остановке бота
    """
    logger.info("Бот остановлен!")
    
    # Останавливаем планировщик уведомлений
    notification_scheduler = get_scheduler(bot)
    notification_scheduler.stop()


def main():
    """
    Главная функция
    """
    register_handlers()
    
    # Запуск бота
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )


if __name__ == '__main__':
    main()