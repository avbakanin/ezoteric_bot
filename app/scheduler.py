"""
Планировщик для push-уведомлений
"""

import asyncio
import datetime
import logging
from collections import Counter
from datetime import timedelta
from typing import Any, Dict, List, Sequence, Tuple

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.settings import config
from app.shared.astro import (
    ForecastResult,
    daily_transit_service,
    retrograde_service,
    transit_interpreter,
)
from app.shared.birth_profiles import birth_profile_storage
from app.shared.calculations import calculate_daily_number
from app.shared.helpers import get_user_timezone, is_premium
from app.shared.messages import DiaryMessages, MessagesData
from app.shared.storage import user_storage
from app.shared.texts import get_number_texts

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


class ForecastPreview:
    def __init__(self, base: ForecastResult, aspects_limit: int = 1):
        self.base = base
        self.aspects_limit = aspects_limit

    @classmethod
    def build(cls, base: ForecastResult, aspects_limit: int = 1) -> "ForecastPreview":
        return cls(base, aspects_limit)

    def to_result(self) -> ForecastResult:
        return ForecastResult(
            user_id=self.base.user_id,
            target_date=self.base.target_date,
            natal_chart=self.base.natal_chart,
            transit_chart=self.base.transit_chart,
            aspects=self.base.aspects[: self.aspects_limit],
            missing_fields=[],
        )




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
        self.last_digest_week: Tuple[int, int] | None = None
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

        if now.weekday() == 0 and self.last_digest_week != now.isocalendar()[:2]:
            await self._send_weekly_digests(now)
            self.last_digest_week = now.isocalendar()[:2]

        await self._send_daily_transit_forecasts(now)
        await self._send_retrograde_alerts(now)

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

    async def _send_weekly_digests(self, now: datetime.datetime):
        """Отправляет еженедельный дайджест дневника наблюдений."""

        start_period = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_period = now

        users = user_storage.get_all_users().items()
        if not users:
            return

        for user_id_str, user_data in users:
            try:
                user_id = int(user_id_str)
            except ValueError:
                continue

            entries = user_storage.get_diary_entries_in_range(user_id, start_period, end_period)
            is_premium_user = is_premium(user_id)

            if not entries:
                try:
                    await self.bot.send_message(
                        user_id,
                        f"{DiaryMessages.DIGEST_NO_ENTRIES}\n\n{DiaryMessages.DIGEST_REMINDER}",
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Не удалось отправить пустой дайджест %s: %s", user_id, exc)
                continue

            categories = [entry.get("category") or "Без темы" for entry in entries]
            counter = Counter(categories)
            top_categories = ", ".join(
                f"{name} ({count})" for name, count in counter.most_common(3)
            )

            message_lines = [
                DiaryMessages.DIGEST_TITLE.format(count=len(entries), top_categories=top_categories or "Без темы"),
            ]

            if not is_premium_user:
                message_lines.append(DiaryMessages.HISTORY_PREMIUM_PROMO)

            message_lines.append(DiaryMessages.DIGEST_REMINDER)

            try:
                await self.bot.send_message(user_id, "\n\n".join(message_lines))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Не удалось отправить дайджест %s: %s", user_id, exc)

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

    async def _send_daily_transit_forecasts(self, now: datetime.datetime):  # noqa: C901
        if ZoneInfo is None:
            return

        profiles = birth_profile_storage.get_all_profiles()
        if not profiles:
            return

        for user_id_str, profile in profiles.items():
            try:
                user_id = int(user_id_str)
            except ValueError:
                continue

            timezone_name = profile.get("timezone")
            if not timezone_name:
                continue

            try:
                tz = ZoneInfo(timezone_name)
            except Exception:
                logger.debug("Неверный часовой пояс %s для пользователя %s", timezone_name, user_id)
                continue

            local_now = now.astimezone(tz)
            if not (local_now.hour == 11 and local_now.minute == 0):
                continue

            local_date = local_now.date()
            if profile.get("last_forecast_sent") == local_date.isoformat():
                continue

            try:
                forecast = daily_transit_service.generate(
                    profile,
                    user_id=user_id,
                    target_date=local_date,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Ошибка расчёта натальной карты для %s: %s", user_id, exc)
                continue

            if forecast.missing_fields:
                continue

            is_premium_user = is_premium(user_id)
            if is_premium_user:
                message_text = transit_interpreter.render_forecast(forecast)
            else:
                preview = ForecastPreview.build(forecast)
                message_text = "\n\n".join(
                    [
                        transit_interpreter.render_forecast(preview.to_result()),
                        MessagesData.NATAL_CHART_PREMIUM_PREVIEW,
                        MessagesData.NATAL_CHART_PREMIUM_ONLY,
                    ]
                )

            try:
                await self.bot.send_message(user_id, message_text)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Не удалось отправить натальную карту %s: %s", user_id, exc)
                continue

            birth_profile_storage.mark_forecast_sent(user_id, local_date.isoformat())
            birth_profile_storage.save_forecast_text(
                user_id,
                local_date.isoformat(),
                message_text,
                is_preview=not is_premium_user,
            )

    async def _send_retrograde_alerts(self, now: datetime.datetime):  # noqa: C901
        start_date = now.date()
        end_date = start_date + timedelta(days=120)
        periods_map = retrograde_service.get_periods(start_date, end_date)
        if not any(periods_map.values()):
            return

        users = user_storage.get_all_users().items()
        if not users:
            return

        for user_id_str, user_data in users:
            try:
                user_id = int(user_id_str)
            except ValueError:
                continue

            notifications = user_data.get("notifications", {})
            if not notifications.get("enabled", True):
                continue

            tz_name = get_user_timezone(user_id)
            local_now = self._to_local(now, tz_name)
            if not (local_now.hour == self.target_hour and local_now.minute == self.target_minute):
                continue

            local_date = local_now.date()
            is_premium_user = is_premium(user_id)
            allowed_planets: Sequence[str] = retrograde_service.tracked_planets if is_premium_user else ("Mercury",)

            for planet in allowed_planets:
                for period in periods_map.get(planet, []):
                    pre_iso = period.pre_alert.isoformat()
                    start_iso = period.start.isoformat()

                    if period.pre_alert == local_date and not user_storage.has_retro_alert(user_id, planet, "pre", pre_iso):
                        message = retrograde_service.format_pre_alert(period, is_premium_user, local_date)
                        await self._send_retro_message(user_id, message)
                        user_storage.mark_retro_alert(user_id, planet, "pre", pre_iso)

                    if period.start == local_date and not user_storage.has_retro_alert(user_id, planet, "start", start_iso):
                        message = retrograde_service.format_start_alert(period, is_premium_user)
                        await self._send_retro_message(user_id, message)
                        user_storage.mark_retro_alert(user_id, planet, "start", start_iso)

    async def _send_retro_message(self, user_id: int, message_text: str) -> None:
        for attempt in range(self.max_retries):
            try:
                await self.bot.send_message(user_id, message_text)
                return
            except TelegramAPIError as e:
                if e.error_code == 403:
                    logger.warning("Пользователь %s заблокировал бота (ретро-оповещение)", user_id)
                    user_storage.update_user(user_id, notifications={"enabled": False})
                    return
                if e.error_code == 400:
                    logger.error("Неверный запрос при отправке ретро-оповещения %s: %s", user_id, e)
                    return
                logger.warning(
                    "Попытка %s отправить ретро-оповещение пользователю %s неудачна: %s",
                    attempt + 1,
                    user_id,
                    e,
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise
            except Exception as e:
                logger.warning(
                    "Попытка %s отправить ретро-оповещение пользователю %s неудачна: %s",
                    attempt + 1,
                    user_id,
                    e,
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise

    @staticmethod
    def _to_local(now: datetime.datetime, tz_name: str) -> datetime.datetime:
        if ZoneInfo is None:
            return now
        try:
            return now.astimezone(ZoneInfo(tz_name))
        except Exception:
            return now

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
