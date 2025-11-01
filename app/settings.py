"""
Настройки и конфигурация бота
"""

import logging
import os
from typing import Any, Dict

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)


class BotConfig:
    """Конфигурация бота"""

    def __init__(self):
        self._load_config()

    def _load_config(self):
        """Загружает конфигурацию из переменных окружения"""
        # Токен бота
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        if not self.BOT_TOKEN:
            logger.error("BOT_TOKEN не найден в переменных окружения")
            raise ValueError("BOT_TOKEN не найден в переменных окружения")

        # Настройки базы данных
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///numerology_bot.db")

        # Настройки уведомлений
        self.NOTIFICATION_TIME = os.getenv("NOTIFICATION_TIME", "11:00")

        # Лимиты для бесплатных пользователей
        # Уменьшено до 2 запросов в день
        self.FREE_DAILY_LIMIT = int(os.getenv("FREE_DAILY_LIMIT", "2"))
        self.FREE_COMPATIBILITY_LIMIT = int(os.getenv("FREE_COMPATIBILITY_LIMIT", "1"))
        # Лимит повторных просмотров
        self.FREE_REPEAT_VIEWS_LIMIT = int(os.getenv("FREE_REPEAT_VIEWS_LIMIT", "5"))

        # Настройки подписки
        self.SUBSCRIPTION_PRICE = int(os.getenv("SUBSCRIPTION_PRICE", "299"))
        self.SUBSCRIPTION_DURATION = int(os.getenv("SUBSCRIPTION_DURATION", "30"))

        # Дополнительные настройки
        self.MAX_MESSAGE_LENGTH = int(os.getenv("MAX_MESSAGE_LENGTH", "4096"))
        self.MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
        self.RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))

        # Настройки безопасности
        self.RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
        self.MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", "1000"))

        # Настройки логирования
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FILE = os.getenv("LOG_FILE", "bot.log")

        logger.info("Конфигурация загружена успешно")

    def get_all_settings(self) -> Dict[str, Any]:
        """Возвращает все настройки"""
        return {
            "BOT_TOKEN": self.BOT_TOKEN,
            "DATABASE_URL": self.DATABASE_URL,
            "NOTIFICATION_TIME": self.NOTIFICATION_TIME,
            "FREE_DAILY_LIMIT": self.FREE_DAILY_LIMIT,
            "FREE_COMPATIBILITY_LIMIT": self.FREE_COMPATIBILITY_LIMIT,
            "FREE_REPEAT_VIEWS_LIMIT": self.FREE_REPEAT_VIEWS_LIMIT,
            "SUBSCRIPTION_PRICE": self.SUBSCRIPTION_PRICE,
            "SUBSCRIPTION_DURATION": self.SUBSCRIPTION_DURATION,
            "MAX_MESSAGE_LENGTH": self.MAX_MESSAGE_LENGTH,
            "MAX_RETRIES": self.MAX_RETRIES,
            "RETRY_DELAY": self.RETRY_DELAY,
            "RATE_LIMIT_PER_MINUTE": self.RATE_LIMIT_PER_MINUTE,
            "MAX_INPUT_LENGTH": self.MAX_INPUT_LENGTH,
            "LOG_LEVEL": self.LOG_LEVEL,
            "LOG_FILE": self.LOG_FILE,
        }


# Глобальный экземпляр конфигурации
config = BotConfig()

# Для обратной совместимости
API_TOKEN = config.BOT_TOKEN
DATABASE_URL = config.DATABASE_URL
NOTIFICATION_TIME = config.NOTIFICATION_TIME
FREE_DAILY_LIMIT = config.FREE_DAILY_LIMIT
FREE_COMPATIBILITY_LIMIT = config.FREE_COMPATIBILITY_LIMIT
FREE_REPEAT_VIEWS_LIMIT = config.FREE_REPEAT_VIEWS_LIMIT
SUBSCRIPTION_PRICE = config.SUBSCRIPTION_PRICE
SUBSCRIPTION_DURATION = config.SUBSCRIPTION_DURATION
MAX_MESSAGE_LENGTH = config.MAX_MESSAGE_LENGTH
MAX_RETRIES = config.MAX_RETRIES
RETRY_DELAY = config.RETRY_DELAY
