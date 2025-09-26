"""
Модуль безопасности для бота
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SecurityValidator:
    """
    Класс для валидации безопасности
    """
    
    @staticmethod
    def validate_user_input(text: str, max_length: int = 1000) -> bool:
        """
        Валидирует пользовательский ввод
        """
        if not text or not isinstance(text, str):
            return False
        
        # Проверяем длину
        if len(text) > max_length:
            logger.warning(f"Слишком длинный ввод: {len(text)} символов")
            return False
        
        # Проверяем на подозрительные символы
        suspicious_patterns = [
            r'<script.*?>.*?</script>',  # XSS
            r'javascript:',  # JavaScript injection
            r'data:text/html',  # Data URI
            r'vbscript:',  # VBScript
            r'onload\s*=',  # Event handlers
            r'onerror\s*=',
            r'onclick\s*=',
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Обнаружен подозрительный паттерн в вводе: {pattern}")
                return False
        
        return True
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Очищает текст от потенциально опасных символов
        """
        if not text:
            return ""
        
        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        
        # Экранируем специальные символы
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        
        return text
    
    @staticmethod
    def validate_date_format(date_str: str) -> bool:
        """
        Валидирует формат даты
        """
        if not date_str:
            return False
        
        # Проверяем формат ДД.ММ.ГГГГ
        pattern = r'^\d{2}\.\d{2}\.\d{4}$'
        if not re.match(pattern, date_str):
            return False
        
        try:
            day, month, year = date_str.split('.')
            day, month, year = int(day), int(month), int(year)
            
            # Проверяем разумные границы
            if year < 1900 or year > 2100:
                return False
            if month < 1 or month > 12:
                return False
            if day < 1 or day > 31:
                return False
            
            return True
            
        except ValueError:
            return False
    
    @staticmethod
    def rate_limit_check(user_id: int, action: str, limit: int = 10, window: int = 60) -> bool:
        """
        Проверяет лимит запросов пользователя
        """
        # Простая реализация rate limiting
        # В продакшене лучше использовать Redis или базу данных
        
        import time
        from storage import user_storage
        
        user_data = user_storage.get_user(user_id)
        
        if "rate_limits" not in user_data:
            user_data["rate_limits"] = {}
        
        current_time = time.time()
        action_key = f"{action}_{window}"
        
        if action_key not in user_data["rate_limits"]:
            user_data["rate_limits"][action_key] = []
        
        # Очищаем старые записи
        user_data["rate_limits"][action_key] = [
            timestamp for timestamp in user_data["rate_limits"][action_key]
            if current_time - timestamp < window
        ]
        
        # Проверяем лимит
        if len(user_data["rate_limits"][action_key]) >= limit:
            logger.warning(f"Превышен лимит запросов для пользователя {user_id}, действие: {action}")
            return False
        
        # Добавляем текущий запрос
        user_data["rate_limits"][action_key].append(current_time)
        user_storage._save_data()
        
        return True


# Глобальный экземпляр валидатора
security_validator = SecurityValidator()
