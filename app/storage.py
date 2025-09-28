import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class UserStorage:
    def __init__(self, storage_file: str = "users_data.json"):
        base_dir = Path(__file__).parent
        self.storage_file = base_dir / storage_file
        self.data: Dict[str, Any] = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Данные загружены из {self.storage_file}")
                    return data
            except Exception as e:
                logger.error(f"Ошибка загрузки {self.storage_file}: {e}")
                return {}
        return {}

    def _save_data(self):
        try:
            backup_file = f"{self.storage_file}.backup"
            if self.storage_file.exists():
                with open(self.storage_file, "r", encoding="utf-8") as src:
                    with open(backup_file, "w", encoding="utf-8") as dst:
                        dst.write(src.read())
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
            raise

    def _get_user(self, user_id: int) -> Dict[str, Any]:
        uid = str(user_id)
        if uid not in self.data:
            self.data[uid] = self._create_new_user()
        user = self.data[uid]
        user["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return user

    def _create_new_user(self) -> Dict[str, Any]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "birth_date": None,
            "life_path_number": None,
            "soul_number": None,
            "subscription": {"active": False, "expires": None, "type": "free"},
            "usage_stats": {
                "daily_requests": 0,
                "compatibility_checks": 0,
                "repeat_views": 0,
                "last_reset": now[:10],
            },
            "daily_cache": {
                "date": None,
                "life_path_result": None,
                "soul_number_result": None,
                "daily_number_result": None,
                "birth_date": None,
            },
            "notifications": {"enabled": True, "time": "09:00"},
            "text_history": [],
            "affirmation_history": [],
            "last_daily_notification": None,
            "created_at": now,
            "last_activity": now,
        }

    def get_user(self, user_id: int) -> Dict[str, Any]:
        return self._get_user(user_id)

    def update_user(self, user_id: int, **kwargs):
        user = self._get_user(user_id)
        user.update(kwargs)
        self._save_data()

    def _update_daily_cache_if_needed(self, user_id: int):
        """Сбрасывает дневные лимиты и кэш, если наступил новый день"""
        user = self._get_user(user_id)
        usage = user["usage_stats"]
        today = datetime.now().strftime("%Y-%m-%d")
        if usage["last_reset"] != today:
            usage["daily_requests"] = 0
            usage["compatibility_checks"] = 0
            usage["repeat_views"] = 0
            usage["last_reset"] = today
            user["daily_cache"] = {
                "date": None,
                "life_path_result": None,
                "soul_number_result": None,
                "daily_number_result": None,
                "birth_date": None,
            }
            self._save_data()

    # -------------------------
    # Дополнительно: методы для дневника
    # -------------------------

    def add_diary_observation(self, user_id: int, text: str, number: str):
        user = self.get_user(user_id)
        observation = {
            "text": text,
            "number": number,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        user.setdefault("diary_observations", []).append(observation)
        self._save_data()

    # -------------------------
    # Ограничения и лимиты
    # -------------------------

    def get_usage_stats(self, user_id: int) -> dict:
        user = self.get_user(user_id)
        return user.get("usage_stats", {})

    def can_make_request(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        user["usage_stats"]["requests"] = user["usage_stats"].get("requests", 0) + 1
        self._save_data()
        # лимит запросов в день, например, 20
        return user["usage_stats"]["requests"] <= 20

    def can_check_compatibility(self, user_id: int) -> bool:
        self._update_daily_cache_if_needed(user_id)
        user = self._get_user(user_id)
        if user["subscription"]["active"]:
            return True
        return user["usage_stats"]["compatibility_checks"] < 1

    def increment_usage(self, user_id: int, request_type: str = "daily"):
        user = self._get_user(user_id)
        if request_type == "daily":
            user["usage_stats"]["daily_requests"] += 1
        elif request_type == "compatibility":
            user["usage_stats"]["compatibility_checks"] += 1
        self._save_data()

    def can_view_cached_result(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        return user.get("repeat_views", 0) < 100  # например, 3 просмотра

    def increment_repeat_view(self, user_id: int):
        user = self.get_user(user_id)
        user["repeat_views"] = user.get("repeat_views", 0) + 1
        self._save_data()

    # -------------------------
    # Работа с кэшем
    # -------------------------

    def save_daily_result(self, user_id: int, birth_date: str, life_path: int, soul_number: int):
        user = self.get_user(user_id)
        result = {
            "birth_date": birth_date,
            "life_path_result": life_path,
            "soul_number": soul_number,
            "timestamp": datetime.now().isoformat(),
        }
        user.setdefault("daily_results", []).append(result)
        user["life_path_number"] = life_path
        user["soul_number"] = soul_number
        self._save_data()

    def get_cached_result(self, user_id: int) -> dict | None:
        user = self.get_user(user_id)
        results = user.get("daily_results", [])
        if results:
            return results[-1]  # возвращаем последний результат
        return None

    # -------------------------
    # Истории
    # -------------------------

    def add_text_to_history(self, user_id: int, text: str):
        user = self.get_user(user_id)
        user.setdefault("text_history", []).append(text)
        self._save_data()

    def get_text_history(self, user_id: int) -> list:
        user = self.get_user(user_id)
        return user.get("text_history", [])

    def add_affirmation_to_history(self, user_id: int, text: str):
        user = self._get_user(user_id)
        user.setdefault("affirmation_history", []).append(text)
        user["affirmation_history"] = user["affirmation_history"][-10:]
        self._save_data()

    # -------------------------
    # Установить ДР
    # -------------------------

    def set_birth_date(self, user_id: int, birth_date: str):
        """
        Устанавливает дату рождения пользователя
        """
        user = self.get_user(user_id)
        user["birth_date"] = birth_date
        self._save_data()  # Сохраняем изменения в файл/базу

    # -------------------------
    # Подписки и уведомления
    # -------------------------

    def set_subscription(self, user_id: int, active: bool, expires: Optional[str] = None):
        user = self._get_user(user_id)
        user["subscription"]["active"] = active
        user["subscription"]["expires"] = expires
        user["subscription"]["type"] = "premium" if active else "free"
        self._save_data()

    def set_notifications(self, user_id: int, enabled: bool, time: str = "09:00"):
        user = self._get_user(user_id)
        user["notifications"]["enabled"] = enabled
        user["notifications"]["time"] = time
        self._save_data()


# -------------------------
# Глобальный экземпляр
# -------------------------
user_storage = UserStorage()
