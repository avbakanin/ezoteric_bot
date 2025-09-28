import html
import logging
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)


class SecurityValidator:
    """Валидатор безопасности"""

    def __init__(self):
        # Сохраняем историю запросов отдельно по действиям
        self.rate_limit_cache: Dict[str, Dict[int, list]] = {
            "birth_date": {},
            "feedback": {},
            "diary": {},
        }
        self.max_requests_per_minute = {
            "birth_date": 1,  # Раз в минуту
            "feedback": 1,  # Раз в час
            "diary": 1,  # Раз в час
        }
        self.rate_limit_seconds = {
            "birth_date": 30,  # в секундах
            "feedback": 3600,
            "diary": 3600,
        }
        self.max_input_length = 1000

    def rate_limit_check(self, user_id: int, action: str) -> bool:
        """
        Проверяет лимит запросов пользователя для конкретного действия
        """
        try:
            if action not in self.rate_limit_cache:
                self.rate_limit_cache[action] = {}

            current_time = datetime.now()
            user_requests = self.rate_limit_cache[action].get(user_id, [])

            # Очистка старых запросов
            limit_seconds = self.rate_limit_seconds.get(action, 60)
            user_requests = [
                t
                for t in user_requests
                if (current_time - t).total_seconds() >= 0
                and (current_time - t).total_seconds() < limit_seconds
            ]
            self.rate_limit_cache[action][user_id] = user_requests

            # Проверяем лимит
            if len(user_requests) >= 1:
                logger.warning(f"Превышен лимит '{action}' для пользователя {user_id}")
                return False

            # Добавляем текущий запрос
            self.rate_limit_cache[action][user_id].append(current_time)
            return True

        except Exception as e:
            logger.error(f"Ошибка в rate_limit_check: {e}")
            return True  # Разрешаем по умолчанию

    def validate_user_input(self, text: str) -> bool:
        """Валидирует пользовательский ввод"""
        try:
            if not text or not isinstance(text, str):
                return False
            if len(text) > self.max_input_length:
                logger.warning(f"Превышена максимальная длина ввода: {len(text)}")
                return False
            suspicious_chars = ["<script", "javascript:", "data:", "vbscript:"]
            text_lower = text.lower()
            for char in suspicious_chars:
                if char in text_lower:
                    logger.warning(f"Обнаружен подозрительный символ в вводе: {char}")
                    return False
            return True
        except Exception as e:
            logger.error(f"Ошибка в validate_user_input: {e}")
            return False

    def sanitize_text(self, text: str) -> str:
        """Очищает текст от потенциально опасных символов"""
        try:
            if not text:
                return ""
            sanitized = html.escape(text)
            sanitized = " ".join(sanitized.split())
            return sanitized
        except Exception as e:
            logger.error(f"Ошибка в sanitize_text: {e}")
            return ""

    def validate_date_format(self, date_str: str) -> bool:
        """Валидирует формат даты ДД.ММ.ГГГГ"""
        try:
            if not date_str or not isinstance(date_str, str):
                return False
            parts = date_str.split(".")
            if len(parts) != 3:
                return False
            day, month, year = parts
            if not (day.isdigit() and month.isdigit() and year.isdigit()):
                return False
            day, month, year = int(day), int(month), int(year)
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                return False
            return True
        except Exception as e:
            logger.error(f"Ошибка в validate_date_format: {e}")
            return False

    def cleanup_old_requests(self):
        """Очищает устаревшие запросы по всем действиям"""
        try:
            current_time = datetime.now()
            for action, users in self.rate_limit_cache.items():
                for user_id in list(users.keys()):
                    users[user_id] = [
                        t
                        for t in users[user_id]
                        if (current_time - t).total_seconds() < self.rate_limit_seconds.get(action, 60)
                    ]
                    if not users[user_id]:
                        del users[user_id]
        except Exception as e:
            logger.error(f"Ошибка в cleanup_old_requests: {e}")


# Глобальный экземпляр валидатора
security_validator = SecurityValidator()
