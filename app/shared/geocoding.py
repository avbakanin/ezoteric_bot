"""Утилиты для получения геоданных по названию места."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Optional

from app.settings import config

logger = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class GeocodeResult:
    query: str
    lat: float
    lon: float
    display_name: str
    raw: dict | None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "GeocodeResult":
        return GeocodeResult(
            query=data.get("query", ""),
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            display_name=data.get("display_name", ""),
            raw=data.get("raw"),
        )


class Geocoder:
    """Обёртка над Nominatim с минимальным кешированием."""

    def __init__(self):
        try:
            from geopy.geocoders import Nominatim  # type: ignore[import]
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "geopy не установлен. Выполните `pip install geopy` согласно requirements.txt"
            ) from exc

        self._client = Nominatim(
            user_agent=config.GEOCODER_USER_AGENT,
            timeout=config.GEOCODER_TIMEOUT,
        )
        self._cache: dict[tuple[str, int], list[GeocodeResult]] = {}

    def geocode(self, query: str, *, limit: int = 1) -> list[GeocodeResult]:
        normalized = query.strip()
        if not normalized:
            raise ValueError("Название места не должно быть пустым")

        limit = max(1, min(limit, 5))
        cache_key = (normalized, limit)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            location = self._client.geocode(normalized, exactly_one=limit == 1, limit=limit)
        except Exception as exc:  # noqa: BLE001 - хотим залогировать любые ошибки geopy
            logger.error("Ошибка обращения к геосервису: %s", exc)
            raise

        if not location:
            self._cache[cache_key] = []
            return []

        if isinstance(location, list):
            locations = location
        else:
            locations = [location]

        results: list[GeocodeResult] = []
        for item in locations:
            display_name = getattr(item, "address", None) or getattr(item, "raw", {}).get("display_name")
            if not display_name:
                display_name = normalized
            results.append(
                GeocodeResult(
                    query=normalized,
                    lat=float(item.latitude),
                    lon=float(item.longitude),
                    display_name=display_name,
                    raw=getattr(item, "raw", {}),
                )
            )

        self._cache[cache_key] = results
        return results


geocoder = Geocoder()


def geocode_place(query: str) -> Optional[GeocodeResult]:
    """Получает координаты и описание места.

    Raises:
        ValueError: если строка запроса пустая.
        RuntimeError: если библиотека геокодера не установлена.
        Exception: любые ошибки от внешнего сервиса геокодирования.
    """

    results = geocoder.geocode(query, limit=1)
    return results[0] if results else None


def geocode_candidates(query: str, *, limit: int = 3) -> list[GeocodeResult]:
    """Возвращает несколько наиболее подходящих результатов геокодирования."""

    return geocoder.geocode(query, limit=limit)


