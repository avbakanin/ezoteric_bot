"""
Планировщик для push-уведомлений
"""

import asyncio
import datetime
import logging
from typing import Any, Dict, List

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from calculations import calculate_daily_number
from storage import user_storage

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """
    Класс для управления push-уведомлениями
    """

    def __init__(self, bot: Bot, target_hour: int = 9):
        self.bot = bot
        self.is_running = False
        self.target_hour = target_hour  # Время отправки уведомлений
        self.last_sent_date = None
        self.max_retries = 3
        self.retry_delay = 5  # секунды

    async def start(self):
        """
        Запускает планировщик уведомлений
        """
        self.is_running = True
        logger.info(f"Планировщик уведомлений запущен (время отправки: {self.target_hour}:00)")

        while self.is_running:
            try:
                await self._check_and_send_notifications()
                await asyncio.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"Ошибка в планировщике уведомлений: {e}")
                await asyncio.sleep(300)  # При ошибке ждем 5 минут

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
        if now.hour == self.target_hour and now.minute == 0 and self.last_sent_date != today:
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
            f"🌅 Доброе утро!\n\n" f"📅 Число дня: {daily_number}\n\n" f"{text}\n\n" f"Хорошего дня! ✨"
        )

        # Повторные попытки отправки
        for attempt in range(self.max_retries):
            try:
                await self.bot.send_message(user_id, message_text)

                # Добавляем текст в историю и отмечаем отправку
                user_storage.add_text_to_history(user_id, text)
                user_storage.mark_daily_notification_sent(user_id)

                logger.info(f"Уведомление отправлено пользователю {user_id}")
                return

            except TelegramAPIError as e:
                if e.error_code == 403:  # Пользователь заблокировал бота
                    logger.warning(f"Пользователь {user_id} заблокировал бота")
                    user_storage.update_user(user_id, notifications={"enabled": False})
                    return
                elif e.error_code == 400:  # Неверный запрос
                    logger.error(f"Неверный запрос для пользователя {user_id}: {e}")
                    return
                else:
                    logger.warning(
                        f"Попытка {attempt + 1} отправки уведомления "
                        f"пользователю {user_id} неудачна: {e}"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
                    else:
                        raise

            except Exception as e:
                logger.warning(
                    f"Попытка {attempt + 1} отправки уведомления пользователю {user_id} неудачна: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise

    def _get_daily_text(self, daily_number: int, text_history: List[str]) -> str:
        """
        Получает текст для числа дня с учетом истории
        """
        try:
            # Используем кэшированные тексты из handlers
            from app.handlers.handlers import get_number_texts

            number_texts = get_number_texts()

            if str(daily_number) not in number_texts:
                logger.warning(f"Нет текстов для числа дня {daily_number}")
                return "Сегодня особенный день! Доверьтесь своей интуиции."

            if "daily" not in number_texts[str(daily_number)]:
                logger.warning(f"Нет контекста 'daily' для числа {daily_number}")
                return "Сегодня особенный день! Доверьтесь своей интуиции."

            options = number_texts[str(daily_number)]["daily"]

            if not options:
                logger.warning(f"Пустой список текстов для числа дня {daily_number}")
                return "Сегодня особенный день! Доверьтесь своей интуиции."

            # Исключаем тексты, которые уже показывали
            unused = [t for t in options if t not in text_history]

            # Если все тексты показаны, очищаем историю и используем все варианты
            if not unused:
                unused = options

            import random

            return random.choice(unused)

        except Exception as e:
            logger.error(f"Ошибка получения текста для числа дня {daily_number}: {e}")
            return "Сегодня особенный день! Доверьтесь своей интуиции."

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
