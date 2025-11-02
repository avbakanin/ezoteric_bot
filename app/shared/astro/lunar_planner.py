"""Сервис лунного планирования дел и действий."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from math import cos, radians
from pathlib import Path
from typing import Dict, List

from flatlib import const  # type: ignore[import]

from app.shared.astro.ephemeris import ChartSnapshot, EphemerisService, ephemeris_service
from app.shared.astro.lunar_planner_data import (
    ACTION_INDEX,
    ACTIONS,
    PHASES,
    RATING_SCORES,
    SIGN_DEFINITIONS,
    ActionDefinition,
    PhaseAdvice,
    PhaseDefinition,
    SignDefinition,
)
from app.shared.astro.transits import _determine_house

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]

TEMPLATES_PATH = Path(__file__).resolve().parents[3] / "data" / "transit_templates.json"


@dataclass(slots=True, frozen=True)
class DayContext:
    date: date
    phase: PhaseDefinition
    moon_sign: SignDefinition
    illumination: int
    angle: float
    natal_house: int | None = None  # Дом натальной карты, в котором находится транзитная Луна


@dataclass(slots=True, frozen=True)
class ActionSuggestion:
    action: ActionDefinition
    advice: PhaseAdvice


class LunarPlannerService:
    def __init__(self, ephemeris: EphemerisService = ephemeris_service, cache_size: int = 100):
        self.ephemeris = ephemeris
        self._day_cache: Dict[tuple[date, str], DayContext] = {}
        self._cache_size = cache_size

    def _prune_cache(self) -> None:
        if len(self._day_cache) > self._cache_size:
            keys = list(self._day_cache.keys())
            keys.sort(key=lambda k: k[0])
            keep = keys[-self._cache_size // 2:]
            self._day_cache = {k: self._day_cache[k] for k in keep}

    def build_window(self, *, start: date, tz_name: str, days: int = 5, natal_chart: ChartSnapshot | None = None) -> List[DayContext]:
        contexts: List[DayContext] = []
        current = start
        for _ in range(days):
            contexts.append(self._compute_day(current, tz_name, natal_chart=natal_chart))
            current += timedelta(days=1)
        return contexts

    def select_actions(
        self,
        *,
        day: DayContext,
        is_premium: bool,
        limit: int,
    ) -> List[ActionSuggestion]:
        candidates: List[ActionSuggestion] = []
        for action in ACTIONS:
            if action.premium_only and not is_premium:
                continue
            advice_for_phase = action.phase_advice.get(day.phase.key)
            if advice_for_phase is None:
                advice_for_phase = PhaseAdvice(
                    score=RATING_SCORES["neutral"],
                    rating="neutral",
                    text=action.summary,
                )
            candidates.append(ActionSuggestion(action=action, advice=advice_for_phase))

        candidates.sort(
            key=lambda item: (
                item.advice.score,
                -len(item.action.categories),
                item.action.slug,
            ),
            reverse=True,
        )

        preferred = [item for item in candidates if item.advice.score >= 2]
        if not preferred:
            preferred = [item for item in candidates if item.advice.score >= 1]
        if not preferred:
            preferred = candidates[:limit]

        return preferred[:limit]

    def get_action(self, slug: str) -> ActionDefinition | None:
        return ACTION_INDEX.get(slug)

    def get_action_advice(self, *, slug: str, phase: str) -> PhaseAdvice | None:
        action = self.get_action(slug)
        if not action:
            return None
        return action.phase_advice.get(phase)

    def _compute_day(self, target_date: date, tz_name: str, natal_chart: ChartSnapshot | None = None) -> DayContext:
        cache_key = (target_date, tz_name)
        if cache_key in self._day_cache:
            cached = self._day_cache[cache_key]
            # Если есть натальная карта, но кеш без дома - пересчитываем
            if natal_chart and cached.natal_house is None:
                natal_house = self._get_moon_natal_house(target_date, tz_name, natal_chart)
                if natal_house:
                    cached = DayContext(
                        date=cached.date,
                        phase=cached.phase,
                        moon_sign=cached.moon_sign,
                        illumination=cached.illumination,
                        angle=cached.angle,
                        natal_house=natal_house,
                    )
            return cached
        dt_local = datetime.combine(target_date, time(hour=12, minute=0))
        if ZoneInfo is not None:
            try:
                tz = ZoneInfo(tz_name)
                dt_local = dt_local.replace(tzinfo=tz)
            except Exception:
                dt_local = dt_local.replace(tzinfo=timezone.utc)
        else:
            dt_local = dt_local.replace(tzinfo=timezone.utc)
        dt_utc = dt_local.astimezone(timezone.utc).replace(tzinfo=None)
        sun_moon = self.ephemeris.get_ephemeris(dt_utc, planets=(const.SUN, const.MOON))
        sun_lon = float(sun_moon[const.SUN].lon)
        moon_lon = float(sun_moon[const.MOON].lon)
        angle = (moon_lon - sun_lon) % 360.0
        phase = self._phase_from_angle(angle)
        illumination = int(round((1 - cos(radians(angle))) * 50))
        sign_index = int(moon_lon // 30) % 12
        moon_sign = SIGN_DEFINITIONS[sign_index]
        
        natal_house = None
        if natal_chart:
            natal_house = _determine_house(moon_lon % 360, natal_chart.houses)
        
        result = DayContext(
            date=target_date,
            phase=phase,
            moon_sign=moon_sign,
            illumination=min(max(illumination, 0), 100),
            angle=angle,
            natal_house=natal_house,
        )
        self._day_cache[cache_key] = result
        self._prune_cache()
        return result
    
    def _get_moon_natal_house(self, target_date: date, tz_name: str, natal_chart: ChartSnapshot) -> int | None:
        """Определяет, в каком доме натальной карты находится транзитная Луна."""
        if not natal_chart or not natal_chart.houses:
            return None
        dt_local = datetime.combine(target_date, time(hour=12, minute=0))
        if ZoneInfo is not None:
            try:
                tz = ZoneInfo(tz_name)
                dt_local = dt_local.replace(tzinfo=tz)
            except Exception:
                dt_local = dt_local.replace(tzinfo=timezone.utc)
        else:
            dt_local = dt_local.replace(tzinfo=timezone.utc)
        dt_utc = dt_local.astimezone(timezone.utc).replace(tzinfo=None)
        moon_ephemeris = self.ephemeris.get_ephemeris(dt_utc, planets=(const.MOON,))
        moon_lon = float(moon_ephemeris[const.MOON].lon)
        return _determine_house(moon_lon % 360, natal_chart.houses)

    @staticmethod
    def _phase_from_angle(angle: float) -> PhaseDefinition:
        if angle < 20 or angle >= 340:
            return PHASES["new_moon"]
        if angle < 70:
            return PHASES["waxing_crescent"]
        if angle < 110:
            return PHASES["first_quarter"]
        if angle < 160:
            return PHASES["waxing_gibbous"]
        if angle < 200:
            return PHASES["full_moon"]
        if angle < 250:
            return PHASES["waning_gibbous"]
        if angle < 300:
            return PHASES["last_quarter"]
        return PHASES["waning_crescent"]


def _load_house_interpretations() -> Dict[int, List[str]]:
    """Загружает интерпретации домов из transit_templates.json."""
    try:
        with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            houses_data = data.get("houses", {})
            result: Dict[int, List[str]] = {}
            for house_str, interpretations in houses_data.items():
                try:
                    house_num = int(house_str)
                    if isinstance(interpretations, list):
                        result[house_num] = interpretations
                except (ValueError, TypeError):
                    continue
            return result
    except Exception:
        return {}


_HOUSE_INTERPRETATIONS: Dict[int, List[str]] = _load_house_interpretations()


HOUSE_NAMES: Dict[int, str] = {
    1: "1-й дом (Я, личность)",
    2: "2-й дом (Ресурсы, ценности)",
    3: "3-й дом (Коммуникация, близкие)",
    4: "4-й дом (Дом, семья)",
    5: "5-й дом (Творчество, дети)",
    6: "6-й дом (Здоровье, работа)",
    7: "7-й дом (Партнерство)",
    8: "8-й дом (Трансформация, ресурсы)",
    9: "9-й дом (Философия, путешествия)",
    10: "10-й дом (Карьера, статус)",
    11: "11-й дом (Друзья, мечты)",
    12: "12-й дом (Подсознание, завершение)",
}


def get_house_interpretation(house: int) -> str | None:
    """Возвращает случайную интерпретацию для указанного дома."""
    interpretations = _HOUSE_INTERPRETATIONS.get(house)
    if not interpretations:
        return None
    return random.choice(interpretations)


lunar_planner_service = LunarPlannerService()
