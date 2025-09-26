"""
Скрипт для тестирования push-уведомлений
"""

import asyncio
import logging
from aiogram import Bot
from scheduler import NotificationScheduler
from storage import user_storage

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота для тестирования (замените на свой)
TEST_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"


async def test_notifications():
    """
    Тестирует систему уведомлений
    """
    bot = Bot(token=TEST_BOT_TOKEN)
    scheduler = NotificationScheduler(bot)
    
    try:
        # Получаем всех пользователей
        users = user_storage.get_all_users()
        
        if not users:
            logger.info("Нет пользователей для тестирования")
            return
        
        logger.info(f"Найдено {len(users)} пользователей")
        
        # Отправляем тестовые уведомления
        for user_data in users[:5]:  # Тестируем только первых 5 пользователей
            user_id = user_data.get("user_id")
            if user_id:
                success = await scheduler.send_test_notification(user_id)
                if success:
                    logger.info(f"Тестовое уведомление отправлено пользователю {user_id}")
                else:
                    logger.error(f"Ошибка отправки уведомления пользователю {user_id}")
                
                # Небольшая задержка между отправками
                await asyncio.sleep(1)
        
        logger.info("Тестирование завершено")
        
    except Exception as e:
        logger.error(f"Ошибка тестирования: {e}")
    
    finally:
        await bot.session.close()


async def test_scheduler():
    """
    Тестирует планировщик уведомлений
    """
    bot = Bot(token=TEST_BOT_TOKEN)
    scheduler = NotificationScheduler(bot)
    
    try:
        logger.info("Запуск тестирования планировщика...")
        
        # Запускаем планировщик на 30 секунд
        task = asyncio.create_task(scheduler.start())
        
        # Ждем 30 секунд
        await asyncio.sleep(30)
        
        # Останавливаем планировщик
        scheduler.stop()
        task.cancel()
        
        logger.info("Тестирование планировщика завершено")
        
    except Exception as e:
        logger.error(f"Ошибка тестирования планировщика: {e}")
    
    finally:
        await bot.session.close()


async def add_test_user():
    """
    Добавляет тестового пользователя
    """
    test_user_id = 123456789  # Замените на реальный user_id
    
    user_storage.set_birth_date(test_user_id, "15.03.1990")
    user_storage.set_notifications(test_user_id, True)
    
    logger.info(f"Тестовый пользователь {test_user_id} добавлен")


if __name__ == "__main__":
    print("Выберите тест:")
    print("1. Тест уведомлений")
    print("2. Тест планировщика")
    print("3. Добавить тестового пользователя")
    
    choice = input("Введите номер (1-3): ")
    
    if choice == "1":
        asyncio.run(test_notifications())
    elif choice == "2":
        asyncio.run(test_scheduler())
    elif choice == "3":
        asyncio.run(add_test_user())
    else:
        print("Неверный выбор")
