"""
Система хранения данных пользователей
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class UserStorage:
    """Хранилище пользователей"""

    def __init__(self, storage_file: str = "users_data.json"):
        self.storage_file = Path(__file__).parent / storage_file
        self.data: Dict[str, Any] = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки {self.storage_file}: {e}")
                return {}
        return {}

    def _save_data(self):
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения {self.storage_file}: {e}")
            raise

    def get_user(self, user_id: int) -> Dict[str, Any]:
        uid = str(user_id)
        if uid not in self.data:
            self.data[uid] = {
                "birth_date": None,
                "life_path_number": None,
                "soul_number": None,
                "subscription": {"active": False, "expires": None, "type": "free"},
                "usage_stats": {
                    "daily_requests": 0,
                    "compatibility_checks": 0,
                    "repeat_views": 0,
                    "last_reset": datetime.now().strftime("%Y-%m-%d"),
                },
                "daily_cache": {},
                "text_history": [],
                "last_activity": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._save_data()
        else:
            self.data[uid]["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.data[uid]

    def set_birth_date(self, user_id: int, birth_date: str, life_path: int, soul: int):
        user = self.get_user(user_id)
        user.update({"birth_date": birth_date, "life_path_number": life_path, "soul_number": soul})
        self._save_data()

    def can_make_request(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        stats = user["usage_stats"]
        today = datetime.now().strftime("%Y-%m-%d")
        if stats["last_reset"] != today:
            stats.update(
                {"daily_requests": 0, "compatibility_checks": 0, "repeat_views": 0, "last_reset": today}
            )
            self._save_data()
        return user["subscription"]["active"] or stats["daily_requests"] < 2

    def increment_usage(self, user_id: int, request_type: str = "daily"):
        user = self.get_user(user_id)
        if request_type == "daily":
            user["usage_stats"]["daily_requests"] += 1
        elif request_type == "compatibility":
            user["usage_stats"]["compatibility_checks"] += 1
        self._save_data()


user_storage = UserStorage()
