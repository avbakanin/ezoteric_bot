"""
Модуль безопасности для бота
"""

import html
import logging
from datetime import datetime, timedelta
from typing import Dict

logger = logging.getLogger(__name__)

class SecurityValidator:
    """Валидатор безопасности"""
    
    def __init__(self):
        self.rate_limit_cache: Dict[str, list] = {}
        self.max_requests_per_minute = 10
        self.max_input_length = 1000
    
    def rate_limit_check(self, user_id: int) -> bool:
        """
        Проверяет лимит запросов пользователя
        """
        try:
            current_time = datetime.now()
            minute_ago = current_time - timedelta(minutes=1)
            
            if user_id not in self.rate_limit_cache:
                self.rate_limit_cache[user_id] = []
            
            # Очищаем старые запросы
            self.rate_limit_cache[user_id] = [
                req_time for req_time in self.rate_limit_cache[user_id]
                if req_time > minute_ago
            ]
            
            # Проверяем лимит
            if len(self.rate_limit_cache[user_id]) >= self.max_requests_per_minute:
                logger.warning(f"Превышен лимит запросов для пользователя {user_id}")
                return False
            
            # Добавляем текущий запрос
            self.rate_limit_cache[user_id].append(current_time)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка в rate_limit_check: {e}")
            return True  # В случае ошибки разрешаем запрос
    
    def validate_user_input(self, text: str) -> bool:
        """
        Валидирует пользовательский ввод
        """
        try:
            if not text or not isinstance(text, str):
                return False
            
            # Проверяем длину
            if len(text) > self.max_input_length:
                logger.warning(f"Превышена максимальная длина ввода: {len(text)}")
                return False
            
            # Проверяем на подозрительные символы
            suspicious_chars = ['<script', 'javascript:', 'data:', 'vbscript:']
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
        """
        Очищает текст от потенциально опасных символов
        """
        try:
            if not text:
                return ""
            
            # HTML-экранирование
            sanitized = html.escape(text)
            
            # Удаляем лишние пробелы
            sanitized = ' '.join(sanitized.split())
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Ошибка в sanitize_text: {e}")
            return ""
    
    def validate_date_format(self, date_str: str) -> bool:
        """
        Валидирует формат даты
        """
        try:
            if not date_str or not isinstance(date_str, str):
                return False
            
            # Проверяем формат ДД.ММ.ГГГГ
            parts = date_str.split('.')
            if len(parts) != 3:
                return False
            
            day, month, year = parts
            
            # Проверяем, что все части - числа
            if not (day.isdigit() and month.isdigit() and year.isdigit()):
                return False
            
            day, month, year = int(day), int(month), int(year)
            
            # Проверяем диапазоны
            if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка в validate_date_format: {e}")
            return False
    
    def cleanup_old_requests(self):
        """
        Очищает старые записи из кэша
        """
        try:
            current_time = datetime.now()
            minute_ago = current_time - timedelta(minutes=1)
            
            for user_id in list(self.rate_limit_cache.keys()):
                self.rate_limit_cache[user_id] = [
                    req_time for req_time in self.rate_limit_cache[user_id]
                    if req_time > minute_ago
                ]
                
                # Удаляем пустые записи
                if not self.rate_limit_cache[user_id]:
                    del self.rate_limit_cache[user_id]
                    
        except Exception as e:
            logger.error(f"Ошибка в cleanup_old_requests: {e}")

# Глобальный экземпляр валидатора
security_validator = SecurityValidator()
