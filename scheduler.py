"""
Планировщик для push-уведомлений
"""

import asyncio
import datetime
import logging
from typing import List, Dict, Any

from aiogram import Bot
from calculations import calculate_daily_number
from storage import user_storage

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """
    Класс для управления push-уведомлениями
    """
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.is_running = False
        self.target_hour = 9  # Время отправки уведомлений (9 утра)
        self.last_sent_date = None
    
    async def start(self):
        """
        Запускает планировщик уведомлений
        """
        self.is_running = True
        logger.info("Планировщик уведомлений запущен")
        
        while self.is_running:
            try:
                await self._check_and_send_notifications()
                await asyncio.sleep(20)  # Проверяем каждые 20 секунд
            except Exception as e:
                logger.error(f"Ошибка в планировщике уведомлений: {e}")
                await asyncio.sleep(60)  # При ошибке ждем минуту
    
    def stop(self):
        """
        Останавливает планировщик уведомлений
        """
        self.is_running = False
        logger.info("Планировщик уведомлений остановлен")
    
    async def _check_and_send_notifications(self):
        """
        Проверяет время и отправляет уведомления
        """
        now = datetime.datetime.now()
        today = now.date()
        
        # Проверяем, нужно ли отправлять уведомления
        if (now.hour == self.target_hour and 
            now.minute == 0 and 
            self.last_sent_date != today):
            
            await self._send_daily_notifications()
            self.last_sent_date = today
            
            # Ждем минуту, чтобы не отправлять несколько раз
            await asyncio.sleep(60)
    
    async def _send_daily_notifications(self):
        """
        Отправляет ежедневные уведомления всем пользователям
        """
        users = user_storage.get_users_with_notifications()
        
        if not users:
            logger.info("Нет пользователей для отправки уведомлений")
            return
        
        # Вычисляем число дня один раз для всех
        daily_number = calculate_daily_number()
        
        success_count = 0
        error_count = 0
        
        for user in users:
            try:
                await self._send_notification_to_user(user, daily_number)
                success_count += 1
                
                # Небольшая задержка между отправками
                await asyncio.sleep(0.1)
                
            except Exception as e:
                error_count += 1
                logger.error(f"Ошибка отправки уведомления пользователю {user['user_id']}: {e}")
        
        logger.info(f"Уведомления отправлены: {success_count} успешно, {error_count} ошибок")
    
    async def _send_notification_to_user(self, user: Dict[str, Any], daily_number: int):
        """
        Отправляет уведомление конкретному пользователю
        """
        user_id = user["user_id"]
        
        # Проверяем, можно ли отправить уведомление
        if not user_storage.can_send_daily_notification(user_id):
            logger.info(f"Уведомление уже отправлено пользователю {user_id} сегодня")
            return
        
        text_history = user.get("text_history", [])
        
        # Получаем текст для числа дня
        text = self._get_daily_text(daily_number, text_history)
        
        # Формируем сообщение
        message_text = (
            f"🌅 Доброе утро!\n\n"
            f"📅 Число дня: {daily_number}\n\n"
            f"{text}\n\n"
            f"Хорошего дня! ✨"
        )
        
        # Отправляем сообщение
        await self.bot.send_message(user_id, message_text)
        
        # Добавляем текст в историю и отмечаем отправку
        user_storage.add_text_to_history(user_id, text)
        user_storage.mark_daily_notification_sent(user_id)
        
        logger.info(f"Уведомление отправлено пользователю {user_id}")
    
    def _get_daily_text(self, daily_number: int, text_history: List[str]) -> str:
        """
        Получает текст для числа дня с учетом истории
        """
        # Загружаем тексты для чисел
        import json
        with open("numbers.json", "r", encoding="utf-8") as f:
            number_texts = json.load(f)
        
        if str(daily_number) not in number_texts:
            return "Сегодня особенный день! Доверьтесь своей интуиции."
        
        options = number_texts[str(daily_number)]["daily"]
        
        # Исключаем тексты, которые уже показывали
        unused = [t for t in options if t not in text_history]
        
        # Если все тексты показаны, очищаем историю и используем все варианты
        if not unused:
            unused = options
        
        import random
        return random.choice(unused)
    
    async def send_test_notification(self, user_id: int):
        """
        Отправляет тестовое уведомление пользователю
        """
        try:
            daily_number = calculate_daily_number()
            user_data = user_storage.get_user(user_id)
            text_history = user_data.get("text_history", [])
            
            text = self._get_daily_text(daily_number, text_history)
            
            message_text = (
                f"🧪 Тестовое уведомление\n\n"
                f"📅 Число дня: {daily_number}\n\n"
                f"{text}\n\n"
                f"Это тестовое сообщение для проверки уведомлений."
            )
            
            await self.bot.send_message(user_id, message_text)
            user_storage.add_text_to_history(user_id, text)
            # Не отмечаем как отправленное ежедневное уведомление для теста
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки тестового уведомления: {e}")
            return False
    
    def set_notification_time(self, hour: int):
        """
        Устанавливает время отправки уведомлений
        """
        if 0 <= hour <= 23:
            self.target_hour = hour
            logger.info(f"Время уведомлений изменено на {hour}:00")
        else:
            raise ValueError("Время должно быть от 0 до 23")


# Глобальный экземпляр планировщика
scheduler = None


def get_scheduler(bot: Bot) -> NotificationScheduler:
    """
    Получает экземпляр планировщика
    """
    global scheduler
    if scheduler is None:
        scheduler = NotificationScheduler(bot)
    return scheduler
