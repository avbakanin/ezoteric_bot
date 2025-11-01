import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.settings import config
from app.shared.security import is_admin

logger = logging.getLogger(__name__)


class UserStorage:
    def __init__(self, storage_file: str = "users_data.json"):
        # Используем корневую директорию проекта для хранения данных
        base_dir = Path(__file__).resolve().parent.parent.parent
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

        if is_admin(user_id):
            admin_mode = user.get("admin_mode")
            if admin_mode not in {"premium", "free"}:
                admin_mode = "premium"
                user["admin_mode"] = admin_mode

            desired_active = admin_mode != "free"
            subscription = user.setdefault(
                "subscription",
                {"active": False, "expires": None, "type": "free"},
            )

            if subscription.get("active") != desired_active:
                subscription["active"] = desired_active
                subscription["type"] = "premium" if desired_active else "free"
                if desired_active:
                    subscription.setdefault("expires", None)
                self._save_data()

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
                "requests": 0,
                "last_reset": now[:10],
            },
            "daily_cache": {
                "date": None,
                "life_path_result": None,
                "soul_number_result": None,
                "daily_number_result": None,
                "birth_date": None,
            },
            "notifications": {"enabled": True, "time": config.NOTIFICATION_TIME},
            "text_history": [],
            "affirmation_history": [],
            "last_daily_notification": None,
            "daily_number": {
                "date": None,
                "number": None,
                "text": None,
            },
            "created_at": now,
            "last_activity": now,
        }

    def get_user(self, user_id: int) -> Dict[str, Any]:
        return self._get_user(user_id)

    def update_user(self, user_id: int, **kwargs):
        user = self._get_user(user_id)
        user.update(kwargs)
        self._save_data()

    def get_today_diary_count(self, user_id: int) -> int:
        user = self.get_user(user_id)
        today = datetime.now().strftime("%Y-%m-%d")
        observations = user.get("diary_observations", [])
        return sum(1 for obs in observations if obs["date"].startswith(today))

    def _update_daily_cache_if_needed(self, user_id: int):
        """Сбрасывает дневные лимиты и кэш, если наступил новый день"""
        user = self._get_user(user_id)
        usage = user["usage_stats"]
        today = datetime.now().strftime("%Y-%m-%d")
        if usage["last_reset"] != today:
            usage["daily_requests"] = 0
            usage["compatibility_checks"] = 0
            usage["repeat_views"] = 0
            usage["requests"] = 0
            usage["last_reset"] = today
            user["daily_cache"] = {
                "date": None,
                "life_path_result": None,
                "soul_number_result": None,
                "daily_number_result": None,
                "birth_date": None,
            }
            user["repeat_views"] = 0
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
        self._update_daily_cache_if_needed(user_id)
        user = self._get_user(user_id)

        if user["subscription"]["active"]:
            user["usage_stats"]["daily_requests"] += 1
            self._save_data()
            return True

        limit = config.FREE_DAILY_LIMIT
        usage = user["usage_stats"]

        if usage["daily_requests"] >= limit:
            return False

        usage["daily_requests"] += 1
        self._save_data()
        return True

    def can_check_compatibility(self, user_id: int) -> bool:
        self._update_daily_cache_if_needed(user_id)
        user = self._get_user(user_id)
        if user["subscription"]["active"]:
            return True
        limit = config.FREE_COMPATIBILITY_LIMIT
        return user["usage_stats"]["compatibility_checks"] < limit

    def increment_usage(self, user_id: int, request_type: str = "daily"):
        self._update_daily_cache_if_needed(user_id)
        user = self._get_user(user_id)
        if request_type == "daily":
            user["usage_stats"]["daily_requests"] += 1
        elif request_type == "compatibility":
            user["usage_stats"]["compatibility_checks"] += 1
        self._save_data()

    def can_view_cached_result(self, user_id: int) -> bool:
        self._update_daily_cache_if_needed(user_id)
        user = self.get_user(user_id)

        if user["subscription"]["active"]:
            return True

        limit = config.FREE_REPEAT_VIEWS_LIMIT
        return user["usage_stats"].get("repeat_views", 0) < limit

    def increment_repeat_view(self, user_id: int):
        self._update_daily_cache_if_needed(user_id)
        user = self.get_user(user_id)
        usage = user["usage_stats"]
        usage["repeat_views"] = usage.get("repeat_views", 0) + 1
        self._save_data()

    # -------------------------
    # Работа с кэшем
    # -------------------------

    def save_daily_result(
        self,
        user_id: int,
        birth_date: str,
        life_path: int,
        soul_number: int,
        text: str = None,
    ):
        user = self.get_user(user_id)
        result = {
            "birth_date": birth_date,
            "life_path_result": life_path,
            "soul_number": soul_number,
            "text": text,  # Сохраняем текст вместе с результатом
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
        if is_admin(user_id):
            user["admin_mode"] = "premium" if active else "free"
        self._save_data()

    def set_notifications(self, user_id: int, enabled: bool, time: str | None = None):
        user = self._get_user(user_id)
        notifications = user.setdefault("notifications", {})
        target_time = time or notifications.get("time") or config.NOTIFICATION_TIME
        notifications["enabled"] = enabled
        notifications["time"] = target_time
        if enabled:
            user["last_daily_notification"] = None
        self._save_data()

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Удаляет данные пользователей, неактивных более N дней

        :param days: Количество дней неактивности
        :return: Количество удаленных пользователей
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        users_to_delete = []

        for user_id, user_data in self.data.items():
            last_activity = user_data.get("last_activity")
            if last_activity:
                try:
                    activity_date = datetime.strptime(last_activity, "%Y-%m-%d %H:%M:%S")
                    if activity_date < cutoff_date:
                        users_to_delete.append(user_id)
                except ValueError:
                    # Если формат даты неверный, пропускаем
                    continue

        # Удаляем пользователей
        for user_id in users_to_delete:
            del self.data[user_id]

        if users_to_delete:
            self._save_data()
            logger.info(f"Удалено {len(users_to_delete)} неактивных пользователей")

        return len(users_to_delete)

    def get_all_users(self) -> Dict[str, Any]:
        """Возвращает всех пользователей"""
        return self.data

    def get_diary_entries_in_range(self, user_id: int, start: datetime, end: datetime) -> list[dict[str, Any]]:
        user = self.get_user(user_id)
        entries = user.get("diary_observations", [])
        result = []
        for entry in entries:
            date_str = entry.get("date")
            if not date_str:
                continue
            try:
                entry_datetime = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if start <= entry_datetime <= end:
                result.append(entry)
        return result

    # -------------------------
    # Уведомления
    # -------------------------

    def get_users_with_notifications(self) -> list[dict[str, Any]]:
        """Возвращает пользователей с включёнными уведомлениями."""
        users: list[dict[str, Any]] = []
        for user_id, user_data in self.data.items():
            notifications = user_data.get("notifications", {})
            if notifications.get("enabled", False):
                users.append({"user_id": int(user_id), **user_data})
        return users

    def can_send_daily_notification(self, user_id: int) -> bool:
        """Проверяет, отправляли ли уведомление пользователю сегодня."""
        user = self.get_user(user_id)
        today = datetime.now().strftime("%Y-%m-%d")
        last_sent = user.get("last_daily_notification")
        return last_sent != today

    def mark_daily_notification_sent(self, user_id: int):
        """Отмечает, что уведомление пользователю уже отправлено сегодня."""
        user = self.get_user(user_id)
        user["last_daily_notification"] = datetime.now().strftime("%Y-%m-%d")
        self._save_data()

    def get_daily_number_cache(self, user_id: int) -> dict[str, Any]:
        user = self.get_user(user_id)
        return user.get("daily_number", {})

    def set_daily_number_cache(self, user_id: int, date: str, number: int, text: str):
        user = self.get_user(user_id)
        user["daily_number"] = {
            "date": date,
            "number": number,
            "text": text,
        }
        self._save_data()


# -------------------------
# Глобальный экземпляр
# -------------------------
user_storage = UserStorage()
