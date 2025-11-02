import asyncio
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
        # Асинхронное сохранение
        self._save_task: Optional[asyncio.Task] = None
        self._pending_save = False
        self._last_save_time = 0.0
        self._save_lock: Optional[asyncio.Lock] = None  # Инициализируем при первом использовании
        self._save_debounce_delay = 0.5  # Сохранять максимум раз в 0.5 секунды
    
    async def flush_pending_saves(self):
        """Принудительно сохраняет все ожидающие изменения (используется при shutdown)."""
        if self._pending_save:
            try:
                if self._save_lock is None:
                    self._save_lock = asyncio.Lock()
                await self._save_data_async()
                # Ждем завершения задачи, если она запущена
                if self._save_task and not self._save_task.done():
                    await self._save_task
            except Exception as e:
                logger.error(f"Ошибка при финальном сохранении: {e}", exc_info=True)
                # В случае ошибки пытаемся сохранить синхронно
                try:
                    self._save_data_sync()
                except Exception as sync_error:
                    logger.error(f"Критическая ошибка синхронного сохранения: {sync_error}")

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

    def _save_data_sync(self):
        """Синхронное сохранение данных (используется при инициализации)."""
        try:
            backup_file = f"{self.storage_file}.backup"
            if self.storage_file.exists():
                with open(self.storage_file, "r", encoding="utf-8") as src:
                    with open(backup_file, "w", encoding="utf-8") as dst:
                        dst.write(src.read())
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Данные сохранены в {self.storage_file}")
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}", exc_info=True)
            raise

    async def _save_data_async(self):
        """Асинхронное сохранение данных с debouncing."""
        # Инициализируем lock при необходимости
        if self._save_lock is None:
            self._save_lock = asyncio.Lock()
        
        async with self._save_lock:
            if not self._pending_save:
                return
            
            # Debouncing: проверяем, прошло ли достаточно времени с последнего сохранения
            loop = asyncio.get_event_loop()
            current_time = loop.time()
            time_since_last_save = current_time - self._last_save_time
            
            if time_since_last_save < self._save_debounce_delay:
                # Ждем оставшееся время
                await asyncio.sleep(self._save_debounce_delay - time_since_last_save)
            
            try:
                # Сохраняем данные синхронно (I/O операция)
                # Используем run_in_executor для неблокирующей записи
                await loop.run_in_executor(None, self._save_data_sync)
                self._last_save_time = loop.time()
                self._pending_save = False
            except Exception as e:
                logger.error(f"Ошибка асинхронного сохранения данных: {e}", exc_info=True)

    def _save_data(self, immediate: bool = False):
        """
        Помечает данные для сохранения и запускает асинхронное сохранение.
        
        Args:
            immediate: Если True, сохраняет немедленно (блокирующий вызов)
        """
        if immediate:
            # Для критичных операций (например, при старте) сохраняем сразу
            self._save_data_sync()
            self._pending_save = False
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    self._last_save_time = loop.time()
                else:
                    self._last_save_time = 0.0
            except RuntimeError:
                self._last_save_time = 0.0
        else:
            # Для обычных операций запускаем асинхронное сохранение
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если событийный цикл запущен, создаем задачу
                    if self._save_task is None or self._save_task.done():
                        self._save_task = loop.create_task(self._save_data_async())
                else:
                    # Если цикл не запущен, запускаем синхронно
                    loop.run_until_complete(self._save_data_async())
            except RuntimeError:
                # Если нет активного event loop, сохраняем синхронно
                logger.warning("Нет активного event loop, сохранение синхронно")
                self._save_data_sync()
                self._pending_save = False

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
            "birth_time": None,
            "timezone": None,
            "utc_offset": None,
            "lat": None,
            "lon": None,
            "place_name": None,
            "age": None,
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
            "tarot_cache": {
                "single_card": {"date": None, "card": None, "interpretation": None},
                "daily_three": {"date": None, "cards": None, "interpretations": None},
            },
            "tarot_history": [],
            "retro_alerts": {},
            "achievements": {
                "unlocked": [],
                "streak_days": 0,
                "last_activity_date": None,
                "longest_streak": 0,
            },
            "stats": {
                "total_tarot_readings": 0,
                "total_diary_entries": 0,
                "total_days_active": 0,
                "last_feature_used": None,
            },
            "daily_challenges": {
                "current": None,
                "completed_today": [],
                "streak": 0,
                "last_challenge_date": None,
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
            # Сбрасываем кэш Таро для дневных раскладов
            if "tarot_cache" in user:
                for spread_key in ["single_card", "daily_three"]:
                    if spread_key in user["tarot_cache"]:
                        cache = user["tarot_cache"][spread_key]
                        if cache.get("date") != today:
                            user["tarot_cache"][spread_key] = {"date": None, "cards": None, "interpretations": None}
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
            self._save_data(immediate=True)  # Критичное сохранение при очистке
            logger.info(f"Удалено {len(users_to_delete)} неактивных пользователей")

        return len(users_to_delete)

    def get_all_users(self) -> Dict[str, Any]:
        """Возвращает всех пользователей"""
        return self.data

    def get_retro_alert_state(self, user_id: int) -> dict[str, Any]:
        user = self._get_user(user_id)
        return user.setdefault("retro_alerts", {})

    def has_retro_alert(self, user_id: int, planet: str, alert_type: str, date_str: str) -> bool:
        state = self.get_retro_alert_state(user_id)
        planet_state = state.get(planet, {})
        key = "last_pre_alert" if alert_type == "pre" else "last_start_alert"
        return planet_state.get(key) == date_str

    def mark_retro_alert(self, user_id: int, planet: str, alert_type: str, date_str: str) -> None:
        user = self._get_user(user_id)
        state = user.setdefault("retro_alerts", {})
        planet_state = state.setdefault(planet, {})
        key = "last_pre_alert" if alert_type == "pre" else "last_start_alert"
        if planet_state.get(key) == date_str:
            return
        planet_state[key] = date_str
        self._save_data()

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

    def get_tarot_cache(self, user_id: int, spread_key: str) -> dict[str, Any] | None:
        """Получает кэш расклада Таро для пользователя."""
        user = self._get_user(user_id)
        tarot_cache = user.get("tarot_cache", {})
        return tarot_cache.get(spread_key)

    def set_tarot_cache(self, user_id: int, spread_key: str, date: str, cache_data: dict[str, Any]):
        """Сохраняет кэш расклада Таро для пользователя."""
        user = self._get_user(user_id)
        if "tarot_cache" not in user:
            user["tarot_cache"] = {}
        user["tarot_cache"][spread_key] = {
            "date": date,
            **cache_data,
        }
        self._save_data()

    def add_tarot_reading(self, user_id: int, spread_key: str, question: str | None, cards: list[dict], interpretations: list[dict]):
        """Добавляет расклад в историю пользователя."""
        user = self._get_user(user_id)
        if "tarot_history" not in user:
            user["tarot_history"] = []
        
        reading = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "spread_key": spread_key,
            "question": question,
            "cards": cards,
            "interpretations": interpretations,
        }
        
        user["tarot_history"].append(reading)
        # Храним последние 100 раскладов
        if len(user["tarot_history"]) > 100:
            user["tarot_history"] = user["tarot_history"][-100:]
        
        self._save_data()

    def get_tarot_history(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        """Получает историю раскладов пользователя."""
        user = self._get_user(user_id)
        history = user.get("tarot_history", [])
        return history[-limit:] if limit else history

    def set_daily_number_cache(self, user_id: int, date: str, number: int, text: str):
        user = self.get_user(user_id)
        user["daily_number"] = {
            "date": date,
            "number": number,
            "text": text,
        }
        self._save_data()

    # -------------------------
    # Стрики и достижения
    # -------------------------

    def update_streak(self, user_id: int) -> int:
        """
        Обновляет стрик пользователя (серию дней использования).
        Возвращает новый стрик.
        """
        user = self._get_user(user_id)
        achievements = user.setdefault("achievements", {})
        today = datetime.now().strftime("%Y-%m-%d")
        last_date = achievements.get("last_activity_date")
        
        # Если уже обновляли сегодня, возвращаем текущий стрик
        if last_date == today:
            return achievements.get("streak_days", 0)
        
        streak = achievements.get("streak_days", 0)
        
        if last_date:
            try:
                last_dt = datetime.strptime(last_date, "%Y-%m-%d")
                today_dt = datetime.strptime(today, "%Y-%m-%d")
                days_diff = (today_dt - last_dt).days
                
                if days_diff == 1:
                    # Продолжение стрика
                    streak += 1
                elif days_diff > 1:
                    # Стрик прерван, начинаем новый
                    streak = 1
                else:
                    # Тот же день, но еще не обновляли сегодня
                    streak = max(streak, 1)
            except ValueError:
                # Неверный формат даты, начинаем новый стрик
                streak = 1
        else:
            # Первый раз - начинаем стрик
            streak = 1
        
        achievements["streak_days"] = streak
        achievements["last_activity_date"] = today
        
        # Обновляем самый длинный стрик
        longest = achievements.get("longest_streak", 0)
        if streak > longest:
            achievements["longest_streak"] = streak
        
        # Обновляем статистику
        stats = user.setdefault("stats", {})
        total_days = stats.get("total_days_active", 0)
        # Увеличиваем счетчик дней только если это новый день
        if last_date != today:
            stats["total_days_active"] = total_days + 1
        
        self._save_data()
        return streak

    def get_streak(self, user_id: int) -> int:
        """Получает текущий стрик пользователя."""
        user = self._get_user(user_id)
        achievements = user.get("achievements", {})
        return achievements.get("streak_days", 0)

    def check_and_unlock_achievement(self, user_id: int, achievement_id: str) -> bool:
        """
        Проверяет и разблокирует достижение.
        Возвращает True, если достижение разблокировано впервые.
        """
        user = self._get_user(user_id)
        achievements = user.setdefault("achievements", {})
        unlocked = achievements.setdefault("unlocked", [])
        
        if achievement_id in unlocked:
            return False
        
        unlocked.append(achievement_id)
        self._save_data()
        return True

    def get_achievements(self, user_id: int) -> dict[str, Any]:
        """Получает информацию о достижениях пользователя."""
        user = self._get_user(user_id)
        return user.get("achievements", {
            "unlocked": [],
            "streak_days": 0,
            "last_activity_date": None,
            "longest_streak": 0,
        })

    def get_stats(self, user_id: int) -> dict[str, Any]:
        """Получает статистику пользователя."""
        user = self._get_user(user_id)
        return user.get("stats", {
            "total_tarot_readings": 0,
            "total_diary_entries": 0,
            "total_days_active": 0,
            "last_feature_used": None,
        })

    def increment_stat(self, user_id: int, stat_name: str, feature_name: str = None):
        """
        Увеличивает счетчик статистики.
        
        Args:
            user_id: ID пользователя
            stat_name: Название статистики (total_tarot_readings, total_diary_entries, etc.)
            feature_name: Название функции для last_feature_used
        """
        user = self._get_user(user_id)
        stats = user.setdefault("stats", {})
        stats[stat_name] = stats.get(stat_name, 0) + 1
        if feature_name:
            stats["last_feature_used"] = feature_name
        self._save_data()
    
    def get_daily_challenges(self, user_id: int) -> dict[str, Any]:
        """Получает информацию о ежедневных заданиях пользователя."""
        user = self._get_user(user_id)
        return user.get("daily_challenges", {
            "current": None,
            "completed_today": [],
            "streak": 0,
            "last_challenge_date": None,
        })
    
    def set_daily_challenge(self, user_id: int, challenge_id: str, challenge_data: dict[str, Any]):
        """Устанавливает ежедневное задание для пользователя."""
        user = self._get_user(user_id)
        challenges = user.setdefault("daily_challenges", {})
        challenges["current"] = {
            "id": challenge_id,
            **challenge_data,
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        self._save_data()
    
    def complete_daily_challenge(self, user_id: int) -> bool:
        """
        Отмечает текущее задание как выполненное.
        
        Returns:
            True если задание было успешно выполнено (впервые сегодня), False иначе
        """
        user = self._get_user(user_id)
        challenges = user.setdefault("daily_challenges", {})
        current = challenges.get("current")
        today = datetime.now().strftime("%Y-%m-%d")
        
        if not current:
            return False
        
        # Проверяем, что задание на сегодня
        if current.get("date") != today:
            return False
        
        challenge_id = current.get("id")
        completed_today = challenges.get("completed_today", [])
        
        # Проверяем, не выполнено ли уже сегодня
        if challenge_id in completed_today:
            return False
        
        # Отмечаем как выполненное
        completed_today.append(challenge_id)
        challenges["completed_today"] = completed_today
        
        # Обновляем стрик заданий
        last_challenge_date = challenges.get("last_challenge_date")
        if last_challenge_date == today:
            # Уже выполняли сегодня, не увеличиваем стрик
            pass
        elif last_challenge_date:
            try:
                last_dt = datetime.strptime(last_challenge_date, "%Y-%m-%d")
                today_dt = datetime.strptime(today, "%Y-%m-%d")
                days_diff = (today_dt - last_dt).days
                
                if days_diff == 1:
                    # Продолжение стрика
                    challenges["streak"] = challenges.get("streak", 0) + 1
                elif days_diff > 1:
                    # Стрик прерван
                    challenges["streak"] = 1
                else:
                    # Тот же день
                    challenges["streak"] = max(challenges.get("streak", 0), 1)
            except ValueError:
                challenges["streak"] = 1
        else:
            # Первый раз
            challenges["streak"] = 1
        
        challenges["last_challenge_date"] = today
        self._save_data()
        return True


# -------------------------
# Глобальный экземпляр
# -------------------------
user_storage = UserStorage()
