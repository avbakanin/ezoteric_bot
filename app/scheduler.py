"""
Планировщик для push-уведомлений
"""

import asyncio
import datetime
import logging
from typing import Any, Dict, List

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.settings import config
from app.shared.calculations import calculate_daily_number
from app.shared.storage import user_storage
from app.shared.texts import get_number_texts

logger = logging.getLogger(__name__)


class NotificationScheduler:
    """
    Класс для управления push-уведомлениями
    """

    def __init__(self, bot: Bot, target_hour: int = 11, target_minute: int = 0):
        self.bot = bot
        self.is_running = False
        self.target_hour = target_hour  # Время отправки уведомлений
        self.target_minute = target_minute
        self.last_sent_date = None
        self.max_retries = 3
        self.retry_delay = 5  # секунды

    async def start(self):
        """
        Запускает планировщик уведомлений
        """
        self.is_running = True
        logger.info(
            "Планировщик уведомлений запущен (время отправки: %02d:%02d)",
            self.target_hour,
            self.target_minute,
        )

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
        if (
            now.hour == self.target_hour
            and now.minute == self.target_minute
            and self.last_sent_date != today
        ):
            await self._send_daily_notifications(now)
            self.last_sent_date = today

            # Ждем минуту, чтобы не отправлять несколько раз
            await asyncio.sleep(60)

    async def _send_daily_notifications(self, now: datetime.datetime):
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
            notifications = user.get("notifications", {})
            notif_time = notifications.get("time")
            if notif_time:
                try:
                    hour_str, minute_str = notif_time.split(":", 1)
                    user_hour = int(hour_str)
                    user_minute = int(minute_str)
                except (ValueError, AttributeError):
                    user_hour = self.target_hour
                    user_minute = self.target_minute
                if user_hour != self.target_hour or user_minute != self.target_minute:
                    continue
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
            number_texts = get_number_texts()

            if str(daily_number) not in number_texts:
                logger.warning(f"Нет текстов для числа дня {daily_number}")
                return "Сегодня особенный день! Доверьтесь своей интуиции."

            contexts = number_texts[str(daily_number)]
            if not isinstance(contexts, dict):
                logger.warning(f"Некорректный формат текстов для числа {daily_number}")
                return "Сегодня особенный день! Доверьтесь своей интуиции."

            options = contexts.get("premium_daily") or contexts.get("daily")

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

    def set_notification_time(self, hour: int, minute: int = 0):
        """
        Устанавливает время отправки уведомлений
        """
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Время должно быть в диапазоне 00:00-23:59")
        self.target_hour = hour
        self.target_minute = minute
        logger.info("Время уведомлений изменено на %02d:%02d", hour, minute)


# Глобальный экземпляр планировщика
scheduler = None


def get_scheduler(bot: Bot) -> NotificationScheduler:
    """
    Получает экземпляр планировщика
    """
    global scheduler
    if scheduler is None:
        hour, minute = _parse_notification_time(config.NOTIFICATION_TIME)
        scheduler = NotificationScheduler(bot, hour, minute)
    return scheduler


def _parse_notification_time(value: str) -> tuple[int, int]:
    try:
        hour_str, minute_str = value.split(":", 1)
        hour = int(hour_str)
        minute = int(minute_str)
    except (ValueError, AttributeError):
        logger.warning("Некорректное значение NOTIFICATION_TIME: %s, используется 11:00", value)
        return 11, 0

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        logger.warning("NOTIFICATION_TIME вне диапазона: %s, используется 11:00", value)
        return 11, 0
    return hour, minute
