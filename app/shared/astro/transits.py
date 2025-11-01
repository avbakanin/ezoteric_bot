"""Расчёт аспектов между транзитами и натальной картой."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

from .ephemeris import ChartSnapshot, HouseCusp, PlanetPosition

ASPECTS: dict[str, tuple[float, float]] = {
    "conjunction": (0.0, 6.0),
    "sextile": (60.0, 4.0),
    "square": (90.0, 5.0),
    "trine": (120.0, 5.0),
    "opposition": (180.0, 6.0),
}

PLANET_WEIGHTS: dict[str, float] = {
    "Sun": 1.0,
    "Moon": 1.0,
    "Mercury": 0.8,
    "Venus": 0.8,
    "Mars": 0.9,
    "Jupiter": 0.7,
    "Saturn": 0.7,
    "Uranus": 0.6,
    "Neptune": 0.6,
    "Pluto": 0.6,
}

TransitType = Literal["transit"]


@dataclass(slots=True, frozen=True)
class TransitAspect:
    transit_planet: str
    natal_planet: str
    aspect: str
    orb: float
    exact: bool
    applying: bool
    weight: float
    transit_house: int | None
    natal_house: int | None
    transit_position: PlanetPosition
    natal_position: PlanetPosition


def angular_distance(lon1: float, lon2: float) -> float:
    diff = abs(lon1 - lon2) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    return diff


def _calculate_orb(target_angle: float, actual_angle: float) -> float:
    return abs(target_angle - actual_angle)


def _determine_house(longitude: float, houses: dict[int, HouseCusp]) -> int | None:
    if not houses:
        return None
    sorted_houses = sorted(houses.values(), key=lambda cusp: cusp.house)
    longs = [cusp.lon % 360 for cusp in sorted_houses]
    ids = [cusp.house for cusp in sorted_houses]

    for idx, start_lon in enumerate(longs):
        end_idx = (idx + 1) % len(longs)
        end_lon = longs[end_idx]
        house_id = ids[idx]

        if end_idx == 0:
            if start_lon <= longitude or longitude < end_lon:
                return house_id
        else:
            if start_lon <= end_lon:
                if start_lon <= longitude < end_lon:
                    return house_id
            else:
                if longitude >= start_lon or longitude < end_lon:
                    return house_id
    return ids[-1]


def _is_applying(transit: PlanetPosition, natal: PlanetPosition, target_angle: float) -> bool:
    relative = (transit.lon - natal.lon) % 360.0
    diff = relative - target_angle
    if diff > 180:
        diff -= 360
    if diff < -180:
        diff += 360
    if diff > 0:
        return transit.speed < 0  # движется назад к точке
    return transit.speed > 0


def _aspect_weight(transit_planet: str, natal_planet: str, aspect: str, orb: float) -> float:
    base = PLANET_WEIGHTS.get(transit_planet, 0.5) + PLANET_WEIGHTS.get(natal_planet, 0.5)
    aspect_bonus = {
        "conjunction": 1.2,
        "square": 1.1,
        "opposition": 1.1,
        "trine": 0.9,
        "sextile": 0.8,
    }.get(aspect, 0.8)
    orb_penalty = max(0.1, 1.0 - (orb / max(ASPECTS.get(aspect, (0, 6))[1], 1.0)))
    return base * aspect_bonus * orb_penalty


def find_transit_aspects(
    natal: ChartSnapshot,
    transit: ChartSnapshot,
    *,
    aspects: dict[str, tuple[float, float]] | None = None,
    include_planets: Sequence[str] | None = None,
    max_orb_multiplier: float = 1.0,
) -> list[TransitAspect]:
    aspects = aspects or ASPECTS
    include_planets = tuple(include_planets or transit.objects.keys())

    results: list[TransitAspect] = []
    for transit_code in include_planets:
        transit_obj = transit.objects.get(transit_code)
        if not transit_obj:
            continue

        transit_house = _determine_house(transit_obj.lon % 360, natal.houses)

        for natal_code, natal_obj in natal.objects.items():
            angle = angular_distance(transit_obj.lon, natal_obj.lon)
            for aspect_name, (aspect_angle, base_orb) in aspects.items():
                max_orb = base_orb * max_orb_multiplier
                orb = _calculate_orb(aspect_angle, angle)
                if orb <= max_orb:
                    results.append(
                        TransitAspect(
                            transit_planet=transit_code,
                            natal_planet=natal_code,
                            aspect=aspect_name,
                            orb=round(orb, 2),
                            exact=orb <= 0.1,
                            applying=_is_applying(transit_obj, natal_obj, aspect_angle),
                            weight=_aspect_weight(transit_code, natal_code, aspect_name, orb),
                            transit_house=transit_house,
                            natal_house=_determine_house(natal_obj.lon % 360, natal.houses),
                            transit_position=transit_obj,
                            natal_position=natal_obj,
                        )
                    )
    results.sort(key=lambda item: (item.weight, -item.orb), reverse=True)
    return results


