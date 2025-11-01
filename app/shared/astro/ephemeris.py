"""Обёртка над flatlib для расчёта натальных карт и транзитов."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal, Sequence

from flatlib import const, ephem  # type: ignore[import]
from flatlib.chart import Chart  # type: ignore[import]
from flatlib.datetime import Datetime  # type: ignore[import]
from flatlib.geopos import GeoPos  # type: ignore[import]
from flatlib.object import Object  # type: ignore[import]

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

PLANET_CODES: Sequence[str] = (
    const.SUN,
    const.MOON,
    const.MERCURY,
    const.VENUS,
    const.MARS,
    const.JUPITER,
    const.SATURN,
    const.URANUS,
    const.NEPTUNE,
    const.PLUTO,
)

HOUSE_SYSTEM = "Placidus"


@dataclass(slots=True, frozen=True)
class PlanetPosition:
    name: str
    lon: float  # геоцентрическая долгота в градусах
    lat: float  # широта
    speed: float  # скорость в град/день
    retrograde: bool


@dataclass(slots=True, frozen=True)
class HouseCusp:
    house: int
    lon: float


@dataclass(slots=True, frozen=True)
class ChartSnapshot:
    timestamp: datetime
    chart_type: Literal["natal", "transit"]
    location: GeoPos
    objects: dict[str, PlanetPosition]
    houses: dict[int, HouseCusp]


def _build_datetime(dt: datetime, tz_name: str) -> Datetime:
    offset_hours = 0
    if ZoneInfo is not None:
        try:
            tz = ZoneInfo(tz_name)
            aware_dt = dt.replace(tzinfo=tz)
            offset = aware_dt.utcoffset()
            if offset is not None:
                offset_hours = offset.total_seconds() / 3600
        except Exception:
            logger.debug("Не удалось определить смещение для %s", tz_name)
    date_str = dt.strftime("%Y/%m/%d")
    time_str = dt.strftime("%H:%M")
    return Datetime(date_str, time_str, offset_hours)


def _normalize_house_id(raw_id: str | int) -> int:
    if isinstance(raw_id, int):
        return raw_id
    cleaned = str(raw_id).lstrip("Hh")
    try:
        return int(cleaned)
    except ValueError:
        logger.debug("Не удалось преобразовать идентификатор дома %s", raw_id)
        return 0


def _build_location(lat: float, lon: float) -> GeoPos:
    return GeoPos(lat, lon)


def _to_planet_position(obj: Object) -> PlanetPosition:
    return PlanetPosition(
        name=obj.id,
        lon=float(obj.lon),
        lat=float(obj.lat),
        speed=float(getattr(obj, "lonspeed", 0.0)),
        retrograde=bool(obj.isRetrograde()),
    )


class EphemerisService:
    """Упрощённый доступ к flatlib."""

    def __init__(self, house_system: str = HOUSE_SYSTEM, planets: Sequence[str] = PLANET_CODES):
        self.house_system = house_system
        self.planets = tuple(planets)

    def build_chart(
        self,
        *,
        dt: datetime,
        tz_name: str,
        lat: float,
        lon: float,
        chart_type: Literal["natal", "transit"] = "natal",
    ) -> ChartSnapshot:
        chart_datetime = _build_datetime(dt, tz_name)
        location = _build_location(lat, lon)
        kwargs: dict[str, object] = {}
        if self.house_system:
            kwargs["hsys"] = self.house_system
        kwargs["IDs"] = list(self.planets)
        chart = Chart(chart_datetime, location, **kwargs)

        objects = {
            code: _to_planet_position(chart.getObject(code))
            for code in self.planets
        }

        houses = {}
        for house in chart.houses:
            house_id = _normalize_house_id(house.id)
            if house_id <= 0:
                continue
            houses[house_id] = HouseCusp(house=house_id, lon=float(house.lon))

        return ChartSnapshot(
            timestamp=dt,
            chart_type=chart_type,
            location=location,
            objects=objects,
            houses=houses,
        )

    def get_transit_chart(
        self,
        *,
        natal_snapshot: ChartSnapshot,
        dt: datetime,
        tz_name: str,
    ) -> ChartSnapshot:
        location = natal_snapshot.location
        chart_datetime = _build_datetime(dt, tz_name)
        kwargs: dict[str, object] = {}
        if self.house_system:
            kwargs["hsys"] = self.house_system
        kwargs["IDs"] = list(self.planets)
        chart = Chart(chart_datetime, location, **kwargs)

        objects = {
            code: _to_planet_position(chart.getObject(code))
            for code in self.planets
        }

        houses = {}
        for house in chart.houses:
            house_id = _normalize_house_id(house.id)
            if house_id <= 0:
                continue
            houses[house_id] = HouseCusp(house=house_id, lon=float(house.lon))

        return ChartSnapshot(
            timestamp=dt,
            chart_type="transit",
            location=location,
            objects=objects,
            houses=houses,
        )

    def get_ephemeris(self, dt: datetime, planets: Iterable[str] | None = None) -> dict[str, PlanetPosition]:
        planets = tuple(planets or self.planets)
        chart = Chart(
            _build_datetime(dt, "UTC"),
            GeoPos(0.0, 0.0),
            hsys=self.house_system,
            IDs=planets,
        )

        return {code: _to_planet_position(chart.getObject(code)) for code in planets}


ephemeris_service = EphemerisService()


