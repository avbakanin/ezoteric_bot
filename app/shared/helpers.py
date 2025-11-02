"""Общие хелперы для работы с пользователями, подписками и временными зонами."""

from __future__ import annotations

from datetime import date, datetime

from app.shared.birth_profiles import birth_profile_storage
from app.shared.storage import user_storage

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


def is_premium(user_id: int) -> bool:
    """Проверяет, активна ли Premium подписка у пользователя."""
    user = user_storage.get_user(user_id)
    subscription = user.get("subscription", {})
    return bool(subscription.get("active"))


def get_user_timezone(user_id: int) -> str:
    """Возвращает часовой пояс пользователя из профиля или user_storage."""
    profile = birth_profile_storage.get_profile(user_id)
    if profile and profile.get("timezone"):
        return profile["timezone"]
    user = user_storage.get_user(user_id)
    return user.get("timezone") or "UTC"


def get_today_local(tz_name: str) -> date:
    """Возвращает сегодняшнюю дату в указанном часовом поясе."""
    if ZoneInfo is None:
        return date.today()
    try:
        tz = ZoneInfo(tz_name)
        return datetime.now(tz).date()
    except Exception:
        return date.today()

