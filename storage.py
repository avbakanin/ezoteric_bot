"""
Система хранения данных пользователей
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class UserStorage:
    """
    Класс для работы с данными пользователей
    """
    
    def __init__(self, storage_file: str = "users_data.json"):
        self.storage_file = storage_file
        self.data = self._load_data()
    
    def _load_data(self) -> Dict[str, Any]:
        """
        Загружает данные из файла
        """
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Данные загружены из {self.storage_file}")
                    return data
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON в {self.storage_file}: {e}")
                return {}
            except Exception as e:
                logger.error(f"Ошибка загрузки данных из {self.storage_file}: {e}")
                return {}
        else:
            logger.info(f"Файл {self.storage_file} не существует, создаем новый")
            return {}
    
    def _save_data(self):
        """
        Сохраняет данные в файл
        """
        try:
            # Создаем резервную копию перед сохранением
            if os.path.exists(self.storage_file):
                backup_file = f"{self.storage_file}.backup"
                with open(self.storage_file, 'r', encoding='utf-8') as src:
                    with open(backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Данные сохранены в {self.storage_file}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения данных в {self.storage_file}: {e}")
            raise
    
    def get_user(self, user_id: int) -> Dict[str, Any]:
        """
        Получает данные пользователя
        """
        try:
            user_id_str = str(user_id)
            if user_id_str not in self.data:
                self.data[user_id_str] = {
                    "birth_date": None,
                    "life_path_number": None,
                    "soul_number": None,
                    "subscription": {
                        "active": False,
                        "expires": None,
                        "type": "free"
                    },
                    "usage_stats": {
                        "daily_requests": 0,
                        "compatibility_checks": 0,
                        "last_reset": datetime.now().strftime("%Y-%m-%d")
                    },
                    "notifications": {
                        "enabled": True,
                        "time": "09:00"
                    },
                    "text_history": [],  # История показанных текстов
                    "last_daily_notification": None,  # Дата последнего ежедневного уведомления
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "last_activity": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self._save_data()
                logger.info(f"Создан новый пользователь: {user_id}")
            else:
                # Обновляем время последней активности
                self.data[user_id_str]["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            return self.data[user_id_str]
            
        except Exception as e:
            logger.error(f"Ошибка получения данных пользователя {user_id}: {e}")
            return {}
    
    def update_user(self, user_id: int, **kwargs):
        """
        Обновляет данные пользователя
        """
        try:
            user_data = self.get_user(user_id)
            user_data.update(kwargs)
            user_data["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_data()
            logger.debug(f"Данные пользователя {user_id} обновлены")
        except Exception as e:
            logger.error(f"Ошибка обновления данных пользователя {user_id}: {e}")
            raise
    
    def set_birth_date(self, user_id: int, birth_date: str):
        """
        Устанавливает дату рождения пользователя
        """
        from calculations import calculate_life_path_number, calculate_soul_number
        
        life_path = calculate_life_path_number(birth_date)
        soul_number = calculate_soul_number(birth_date)
        
        self.update_user(
            user_id,
            birth_date=birth_date,
            life_path_number=life_path,
            soul_number=soul_number
        )
    
    def can_make_request(self, user_id: int) -> bool:
        """
        Проверяет, может ли пользователь сделать запрос
        """
        user_data = self.get_user(user_id)
        usage_stats = user_data["usage_stats"]
        
        # Сбрасываем счетчик, если прошел новый день
        today = datetime.now().strftime("%Y-%m-%d")
        if usage_stats["last_reset"] != today:
            usage_stats["daily_requests"] = 0
            usage_stats["compatibility_checks"] = 0
            usage_stats["last_reset"] = today
            self._save_data()
        
        # Проверяем лимиты
        if user_data["subscription"]["active"]:
            return True  # Подписчики без ограничений
        
        return usage_stats["daily_requests"] < 3  # Лимит для бесплатных пользователей
    
    def can_check_compatibility(self, user_id: int) -> bool:
        """
        Проверяет, может ли пользователь проверить совместимость
        """
        user_data = self.get_user(user_id)
        usage_stats = user_data["usage_stats"]
        
        # Сбрасываем счетчик, если прошел новый день
        today = datetime.now().strftime("%Y-%m-%d")
        if usage_stats["last_reset"] != today:
            usage_stats["daily_requests"] = 0
            usage_stats["compatibility_checks"] = 0
            usage_stats["last_reset"] = today
            self._save_data()
        
        # Проверяем лимиты
        if user_data["subscription"]["active"]:
            return True  # Подписчики без ограничений
        
        return usage_stats["compatibility_checks"] < 1  # Лимит для бесплатных пользователей
    
    def increment_usage(self, user_id: int, request_type: str = "daily"):
        """
        Увеличивает счетчик использования
        """
        user_data = self.get_user(user_id)
        usage_stats = user_data["usage_stats"]
        
        if request_type == "daily":
            usage_stats["daily_requests"] += 1
        elif request_type == "compatibility":
            usage_stats["compatibility_checks"] += 1
        
        self._save_data()
    
    def get_usage_stats(self, user_id: int) -> Dict[str, int]:
        """
        Получает статистику использования
        """
        user_data = self.get_user(user_id)
        usage_stats = user_data["usage_stats"]
        
        # Сбрасываем счетчик, если прошел новый день
        today = datetime.now().strftime("%Y-%m-%d")
        if usage_stats["last_reset"] != today:
            usage_stats["daily_requests"] = 0
            usage_stats["compatibility_checks"] = 0
            usage_stats["last_reset"] = today
            self._save_data()
        
        return {
            "daily_requests": usage_stats["daily_requests"],
            "compatibility_checks": usage_stats["compatibility_checks"],
            "subscription_active": user_data["subscription"]["active"]
        }
    
    def set_subscription(self, user_id: int, active: bool, expires: Optional[str] = None):
        """
        Устанавливает статус подписки
        """
        user_data = self.get_user(user_id)
        user_data["subscription"]["active"] = active
        user_data["subscription"]["expires"] = expires
        user_data["subscription"]["type"] = "premium" if active else "free"
        self._save_data()
    
    def set_notifications(self, user_id: int, enabled: bool, time: str = "09:00"):
        """
        Настраивает уведомления
        """
        user_data = self.get_user(user_id)
        user_data["notifications"]["enabled"] = enabled
        user_data["notifications"]["time"] = time
        self._save_data()
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """
        Получает всех пользователей
        """
        return list(self.data.values())
    
    def get_users_with_notifications(self) -> List[Dict[str, Any]]:
        """
        Получает пользователей с включенными уведомлениями
        """
        users = []
        for user_id, user_data in self.data.items():
            if user_data.get("notifications", {}).get("enabled", False):
                users.append({
                    "user_id": int(user_id),
                    "notifications": user_data["notifications"],
                    "birth_date": user_data.get("birth_date"),
                    "text_history": user_data.get("text_history", [])
                })
        return users
    
    def add_text_to_history(self, user_id: int, text: str):
        """
        Добавляет текст в историю пользователя
        """
        user_data = self.get_user(user_id)
        if "text_history" not in user_data:
            user_data["text_history"] = []
        
        user_data["text_history"].append(text)
        
        # Ограничиваем историю последними 50 текстами
        if len(user_data["text_history"]) > 50:
            user_data["text_history"] = user_data["text_history"][-50:]
        
        self._save_data()
    
    def get_text_history(self, user_id: int) -> List[str]:
        """
        Получает историю текстов пользователя
        """
        user_data = self.get_user(user_id)
        return user_data.get("text_history", [])
    
    def can_send_daily_notification(self, user_id: int) -> bool:
        """
        Проверяет, можно ли отправить ежедневное уведомление
        """
        user_data = self.get_user(user_id)
        last_notification = user_data.get("last_daily_notification")
        
        if not last_notification:
            return True
        
        try:
            last_date = datetime.strptime(last_notification, "%Y-%m-%d").date()
            today = datetime.now().date()
            return last_date < today
        except:
            return True
    
    def mark_daily_notification_sent(self, user_id: int):
        """
        Отмечает, что ежедневное уведомление отправлено
        """
        user_data = self.get_user(user_id)
        user_data["last_daily_notification"] = datetime.now().strftime("%Y-%m-%d")
        self._save_data()
    
    def cleanup_old_data(self, days: int = 30):
        """
        Очищает старые данные пользователей
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            users_to_remove = []
            
            for user_id, user_data in self.data.items():
                last_activity = user_data.get("last_activity")
                if last_activity:
                    try:
                        activity_date = datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")
                        if activity_date < cutoff_date:
                            users_to_remove.append(user_id)
                    except ValueError as e:
                        logger.warning(f"Неверный формат даты для пользователя {user_id}: {last_activity}")
                        # Удаляем пользователей с неверными датами
                        users_to_remove.append(user_id)
            
            for user_id in users_to_remove:
                del self.data[user_id]
            
            if users_to_remove:
                self._save_data()
                logger.info(f"Удалено {len(users_to_remove)} неактивных пользователей")
            else:
                logger.info("Нет неактивных пользователей для удаления")

        except Exception as e:
            logger.error(f"Ошибка при очистке старых данных: {e}")


# Глобальный экземпляр хранилища
user_storage = UserStorage()