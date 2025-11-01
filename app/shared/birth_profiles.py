"""Модуль для хранения и валидации натальных профилей пользователей."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python < 3.9 не поддерживается, но оставим защиту
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = ValueError  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def validate_birth_date(value: str) -> str:
    """Проверяет формат даты рождения и возвращает ISO-строку."""

    if not value:
        raise ValueError("Дата рождения обязательна")

    normalized = value.strip()
    parsed = None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(normalized, fmt).date()
            break
        except ValueError:
            continue

    if parsed is None:
        raise ValueError("Неверный формат даты рождения. Используйте YYYY-MM-DD или ДД.ММ.ГГГГ")

    return parsed.isoformat()


def validate_birth_time(value: Optional[str]) -> Optional[str]:
    """Возвращает нормализованное время рождения или None."""

    if not value:
        return None
    value = value.strip()
    try:
        parsed = datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise ValueError("Неверный формат времени. Используйте HH:MM") from exc
    return parsed.strftime("%H:%M")


def validate_timezone(value: Optional[str]) -> Optional[str]:
    """Проверяет строку часового пояса."""

    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if ZoneInfo is None:
        logger.warning("ZoneInfo недоступен, пропускаем проверку часового пояса")
        return value
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Неизвестный часовой пояс") from exc
    return value


def validate_coordinate(name: str, value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Координата {name} должна быть числом") from exc
    if name == "lat" and not -90.0 <= numeric <= 90.0:
        raise ValueError("Широта должна быть в диапазоне [-90; 90]")
    if name == "lon" and not -180.0 <= numeric <= 180.0:
        raise ValueError("Долгота должна быть в диапазоне [-180; 180]")
    return numeric


def validate_age(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    try:
        numeric = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Возраст должен быть целым числом") from exc
    if numeric <= 0:
        raise ValueError("Возраст должен быть положительным")
    if numeric > 120:
        raise ValueError("Возраст выглядит нереалистичным")
    return numeric


@dataclass
class BirthProfile:
    birth_date: str
    birth_time: Optional[str] = None
    timezone: Optional[str] = None
    utc_offset: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    place_name: Optional[str] = None
    age: Optional[int] = None
    last_forecast_sent: Optional[str] = None
    last_forecast_date: Optional[str] = None
    last_forecast_text: Optional[str] = None
    last_forecast_is_preview: bool = False
    created_at: str = field(default_factory=_utcnow_iso)
    updated_at: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "birth_date": self.birth_date,
            "birth_time": self.birth_time,
            "timezone": self.timezone,
            "utc_offset": self.utc_offset,
            "lat": self.lat,
            "lon": self.lon,
            "place_name": self.place_name,
            "age": self.age,
            "last_forecast_sent": self.last_forecast_sent,
            "last_forecast_date": self.last_forecast_date,
            "last_forecast_text": self.last_forecast_text,
            "last_forecast_is_preview": self.last_forecast_is_preview,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class BirthProfileStorage:
    """Управление хранением натальных профилей в отдельном JSON."""

    def __init__(self, storage_file: str = "birth_profiles.json"):
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.storage_path = base_dir / storage_file
        self.data: Dict[str, Dict[str, Any]] = self._load()

    # --------------------- Работа с файлом ---------------------
    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.storage_path.exists():
            return {}
        try:
            with open(self.storage_path, "r", encoding="utf-8") as file:
                raw = json.load(file)
                if isinstance(raw, dict):
                    return raw
                logger.warning("Некорректный формат birth_profiles.json, ожидается dict")
                return {}
        except Exception as exc:  # noqa: BLE001 - хотим логировать любые проблемы загрузки
            logger.error("Ошибка загрузки %s: %s", self.storage_path, exc)
            return {}

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.storage_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as tmp_file:
            json.dump(self.data, tmp_file, ensure_ascii=False, indent=2)
        tmp_path.replace(self.storage_path)

    # --------------------- CRUD операции ---------------------
    def get_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self.data.get(str(user_id))

    def upsert_profile(self, user_id: int, **kwargs: Any) -> Dict[str, Any]:
        uid = str(user_id)
        existing = self.data.get(uid, {})

        birth_date = kwargs.get("birth_date")
        birth_time = kwargs.get("birth_time")
        timezone = kwargs.get("timezone")
        utc_offset = kwargs.get("utc_offset")
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        place_name = kwargs.get("place_name")
        age = kwargs.get("age") if "age" in kwargs else existing.get("age")
        last_forecast_date = kwargs.get("last_forecast_date", existing.get("last_forecast_date"))
        last_forecast_text = kwargs.get("last_forecast_text", existing.get("last_forecast_text"))
        last_forecast_is_preview = kwargs.get(
            "last_forecast_is_preview",
            existing.get("last_forecast_is_preview", False),
        )

        normalized = BirthProfile(
            birth_date=validate_birth_date(birth_date or existing.get("birth_date")),
            birth_time=validate_birth_time(birth_time or existing.get("birth_time")),
            timezone=validate_timezone(timezone or existing.get("timezone")),
            utc_offset=float(utc_offset) if utc_offset is not None else existing.get("utc_offset"),
            lat=validate_coordinate("lat", lat if lat is not None else existing.get("lat")),
            lon=validate_coordinate("lon", lon if lon is not None else existing.get("lon")),
            place_name=(place_name or existing.get("place_name")) or None,
            age=validate_age(age),
            last_forecast_sent=kwargs.get("last_forecast_sent", existing.get("last_forecast_sent")),
            last_forecast_date=last_forecast_date,
            last_forecast_text=last_forecast_text,
            last_forecast_is_preview=bool(last_forecast_is_preview),
            created_at=existing.get("created_at", _utcnow_iso()),
        )
        normalized.updated_at = _utcnow_iso()

        self.data[uid] = normalized.to_dict()
        self._save()
        return self.data[uid]

    def delete_profile(self, user_id: int) -> None:
        if str(user_id) in self.data:
            del self.data[str(user_id)]
            self._save()

    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        return self.data

    # --------------------- Синхронизация ---------------------
    def sync_from_user_profile(self, user_id: int, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        birth_date = user_data.get("birth_date")
        if not birth_date:
            return None

        payload: Dict[str, Any] = {"birth_date": birth_date}
        if user_data.get("birth_time"):
            payload["birth_time"] = user_data["birth_time"]
        if user_data.get("timezone"):
            payload["timezone"] = user_data["timezone"]
        if user_data.get("utc_offset") is not None:
            payload["utc_offset"] = user_data["utc_offset"]
        if user_data.get("lat") is not None:
            payload["lat"] = user_data["lat"]
        if user_data.get("lon") is not None:
            payload["lon"] = user_data["lon"]
        if user_data.get("place_name"):
            payload["place_name"] = user_data["place_name"]
        if user_data.get("age") is not None:
            payload["age"] = user_data["age"]

        return self.upsert_profile(user_id, **payload)

    def mark_forecast_sent(self, user_id: int, date_str: str) -> None:
        uid = str(user_id)
        profile = self.data.get(uid)
        if not profile:
            return
        profile["last_forecast_sent"] = date_str
        profile["updated_at"] = _utcnow_iso()
        self._save()

    def save_forecast_text(self, user_id: int, date_str: str, text: str, is_preview: bool) -> None:
        uid = str(user_id)
        profile = self.data.get(uid)
        if not profile:
            return
        profile["last_forecast_date"] = date_str
        profile["last_forecast_text"] = text
        profile["last_forecast_is_preview"] = bool(is_preview)
        profile["updated_at"] = _utcnow_iso()
        self._save()

    def get_last_forecast(self, user_id: int) -> Dict[str, Any] | None:
        profile = self.data.get(str(user_id))
        if not profile:
            return None
        date_str = profile.get("last_forecast_date")
        text = profile.get("last_forecast_text")
        if not date_str or not text:
            return None
        return {
            "date": date_str,
            "text": text,
            "is_preview": bool(profile.get("last_forecast_is_preview")),
        }


birth_profile_storage = BirthProfileStorage()


