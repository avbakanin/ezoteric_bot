"""Сервис расчёта персональных транзитов на день."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from app.shared.birth_profiles import birth_profile_storage

from .ephemeris import ChartSnapshot, EphemerisService, ephemeris_service
from .transits import TransitAspect, find_transit_aspects

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

DEFAULT_TRANSIT_TIME = time(hour=12, minute=0)


@dataclass(slots=True)
class ForecastResult:
    user_id: int
    target_date: date
    natal_chart: ChartSnapshot | None
    transit_chart: ChartSnapshot | None
    aspects: list[TransitAspect]
    missing_fields: list[str]

    @property
    def ok(self) -> bool:
        return not self.missing_fields and self.natal_chart is not None and self.transit_chart is not None


class DailyTransitService:
    def __init__(
        self,
        ephemeris: EphemerisService = ephemeris_service,
        *,
        top_aspects: int = 6,
        aspect_multiplier: float = 1.0,
    ):
        self.ephemeris = ephemeris
        self.top_aspects = top_aspects
        self.aspect_multiplier = aspect_multiplier

    def generate_for_user(self, user_id: int, target_date: date | None = None) -> ForecastResult:
        profile = birth_profile_storage.get_profile(user_id)
        if not profile:
            return ForecastResult(
                user_id=user_id,
                target_date=target_date or date.today(),
                natal_chart=None,
                transit_chart=None,
                aspects=[],
                missing_fields=["profile"],
            )
        return self.generate(profile, user_id=user_id, target_date=target_date)

    def generate(
        self,
        profile: dict[str, Any],
        *,
        user_id: int,
        target_date: date | None = None,
    ) -> ForecastResult:
        missing: list[str] = []
        birth_date = profile.get("birth_date")
        birth_time = profile.get("birth_time") or "12:00"
        timezone_name = profile.get("timezone") or "UTC"
        lat = profile.get("lat")
        lon = profile.get("lon")

        if not birth_date:
            missing.append("birth_date")
        if profile.get("timezone") is None:
            missing.append("timezone")
        if lat is None:
            missing.append("lat")
        if lon is None:
            missing.append("lon")

        if missing:
            return ForecastResult(
                user_id=user_id,
                target_date=target_date or date.today(),
                natal_chart=None,
                transit_chart=None,
                aspects=[],
                missing_fields=missing,
            )

        birth_dt = self._parse_datetime(birth_date, birth_time)
        if birth_dt is None:
            return ForecastResult(
                user_id=user_id,
                target_date=target_date or date.today(),
                natal_chart=None,
                transit_chart=None,
                aspects=[],
                missing_fields=["birth_date"],
            )

        target_date = target_date or date.today()
        target_dt = datetime.combine(target_date, DEFAULT_TRANSIT_TIME)

        natal_chart = self.ephemeris.build_chart(
            dt=birth_dt,
            tz_name=timezone_name,
            lat=float(lat),
            lon=float(lon),
            chart_type="natal",
        )

        transit_chart = self.ephemeris.get_transit_chart(
            natal_snapshot=natal_chart,
            dt=target_dt,
            tz_name=timezone_name,
        )

        aspects = find_transit_aspects(
            natal_chart,
            transit_chart,
            max_orb_multiplier=self.aspect_multiplier,
        )

        if self.top_aspects:
            aspects = aspects[: self.top_aspects]

        return ForecastResult(
            user_id=user_id,
            target_date=target_date,
            natal_chart=natal_chart,
            transit_chart=transit_chart,
            aspects=aspects,
            missing_fields=[],
        )

    @staticmethod
    @staticmethod
    def _parse_datetime(date_str: str, time_str: str) -> datetime | None:
        try:
            hour, minute = DailyTransitService._parse_time(time_str)
            if "T" in date_str:
                parsed = datetime.fromisoformat(date_str)
                return parsed.replace(hour=hour, minute=minute, second=0, microsecond=0)
            year, month, day = map(int, date_str.split("-"))
            return datetime(year, month, day, hour, minute)
        except Exception:
            logger.warning("Не удалось разобрать дату рождения: %s %s", date_str, time_str)
            return None

    @staticmethod
    def _parse_time(time_str: str) -> tuple[int, int]:
        try:
            parts = [int(part) for part in time_str.split(":")[:2]]
            if len(parts) == 2:
                hour, minute = parts
            elif len(parts) == 1:
                hour, minute = parts[0], 0
            else:
                hour, minute = 12, 0
        except Exception:
            hour, minute = 12, 0
        hour = max(0, min(hour, 23))
        minute = max(0, min(minute, 59))
        return hour, minute


daily_transit_service = DailyTransitService()


