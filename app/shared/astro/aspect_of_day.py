"""Расчёт и генерация текста для аспекта дня (транзит-транзит)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time
from itertools import combinations
from typing import Dict, List, Optional, Sequence

from app.shared.astro.ephemeris import EphemerisService, PlanetPosition, ephemeris_service
from app.shared.astro.interpretation import PLANET_RU, TransitInterpreter
from app.shared.astro.transits import ASPECTS, TransitAspect, angular_distance

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AspectOfDay:
    planet_a: str
    planet_b: str
    aspect: str
    orb: float
    exact: bool
    weight: float
    text: str
    premium: str


class AspectOfDayService:
    def __init__(
        self,
        ephemeris: EphemerisService = ephemeris_service,
        *,
        planets: Sequence[str] | None = None,
    ) -> None:
        self.ephemeris = ephemeris
        self.planets = tuple(planets or ephemeris.planets)
        self._cache: Dict[date, List[AspectOfDay]] = {}
        self._interpreter = TransitInterpreter()

    def get_aspects(self, target_date: date) -> List[AspectOfDay]:
        if target_date in self._cache:
            return self._cache[target_date]

        dt = datetime.combine(target_date, time(hour=12, minute=0))
        positions = self.ephemeris.get_ephemeris(dt, planets=self.planets)

        collected: List[AspectOfDay] = []
        for planet_a, planet_b in combinations(self.planets, 2):
            pos_a = positions[planet_a]
            pos_b = positions[planet_b]
            angle = angular_distance(pos_a.lon, pos_b.lon)

            for aspect_name, (exact_angle, base_orb) in ASPECTS.items():
                orb = abs(exact_angle - angle)
                if orb > base_orb:
                    continue
                weight = self._aspect_weight(planet_a, planet_b, aspect_name, orb)
                template = self._render_template(planet_a, planet_b, aspect_name, orb, pos_a, pos_b)
                if template is None:
                    continue
                collected.append(
                    AspectOfDay(
                        planet_a=planet_a,
                        planet_b=planet_b,
                        aspect=aspect_name,
                        orb=round(orb, 2),
                        exact=orb <= 0.1,
                        weight=weight,
                        text=template["free"],
                        premium=template["premium"],
                    )
                )

        collected.sort(key=lambda item: (item.weight, -item.orb), reverse=True)
        self._cache[target_date] = collected
        return collected

    def get_top(self, target_date: date, count: int = 1) -> List[AspectOfDay]:
        return self.get_aspects(target_date)[:count]

    def format_message(self, aspects: List[AspectOfDay], is_premium: bool) -> str:
        if not aspects:
            return "Сегодня значимых аспектов нет — спокойный фон."

        blocks: List[str] = ["✨ Сегодняшний фон"]
        for aspect in aspects:
            fake_aspect = self._build_transit_aspect(
                aspect.planet_a,
                aspect.planet_b,
                aspect.aspect,
                aspect.orb,
                aspect.exact,
                aspect.weight,
            )
            context = self._interpreter._build_context(fake_aspect)  # pylint: disable=protected-access
            aspect_name = context["aspect_name"]
            title = (
                f"🌟 {PLANET_RU.get(aspect.planet_a, aspect.planet_a)} "
                f"{aspect_name} {PLANET_RU.get(aspect.planet_b, aspect.planet_b)} #аспектдня"
            )
            body = aspect.premium if is_premium else aspect.text
            blocks.append("\n".join([title, body]))

        if is_premium and len(aspects) > 1:
            blocks.append("💡 Premium-бонус: вы видите все значимые аспекты суток. Исполните главный совет и сохраните заметку в дневнике.")
        return "\n\n".join(blocks)

    def _render_template(
        self,
        planet_a: str,
        planet_b: str,
        aspect: str,
        orb: float,
        pos_a: PlanetPosition,
        pos_b: PlanetPosition,
    ) -> Optional[dict[str, str]]:
        fake_aspect = self._build_transit_aspect(
            planet_a,
            planet_b,
            aspect,
            orb,
            orb <= 0.1,
            self._aspect_weight(planet_a, planet_b, aspect, orb),
            pos_a,
            pos_b,
        )
        template = self._interpreter._choose_template(fake_aspect)  # pylint: disable=protected-access
        if not template:
            return None
        context = self._interpreter._build_context(fake_aspect)  # pylint: disable=protected-access
        text = template["text"].format(**context)
        advice = template["advice"].format(**context)
        retro = self._interpreter._retrograde_note(fake_aspect)  # pylint: disable=protected-access

        premium_parts = [text]
        if retro:
            premium_parts.append(retro)
        premium_parts.append(f"Совет дня: {advice}. #советдня")

        free_text = "\n".join([text, f"Совет дня: {advice}. #советдня"])

        return {
            "free": free_text,
            "premium": "\n".join(premium_parts),
        }

    @staticmethod
    def _aspect_weight(planet_a: str, planet_b: str, aspect: str, orb: float) -> float:
        from app.shared.astro.transits import PLANET_WEIGHTS

        base = PLANET_WEIGHTS.get(planet_a, 0.5) + PLANET_WEIGHTS.get(planet_b, 0.5)
        aspect_bonus = {
            "conjunction": 1.2,
            "square": 1.1,
            "opposition": 1.1,
            "trine": 0.9,
            "sextile": 0.8,
        }.get(aspect, 0.8)
        orb_limit = ASPECTS.get(aspect, (0.0, 6.0))[1]
        orb_penalty = 1.0 - orb / max(orb_limit, 1.0)
        return base * aspect_bonus * max(0.1, orb_penalty)

    @staticmethod
    def _build_transit_aspect(
        planet_a: str,
        planet_b: str,
        aspect: str,
        orb: float,
        exact: bool,
        weight: float,
        pos_a: Optional[PlanetPosition] = None,
        pos_b: Optional[PlanetPosition] = None,
    ) -> TransitAspect:
        pos_a = pos_a or PlanetPosition(planet_a, 0.0, 0.0, 0.0, False)
        pos_b = pos_b or PlanetPosition(planet_b, 0.0, 0.0, 0.0, False)
        applying = AspectOfDayService._is_applying(pos_a, pos_b, aspect)
        return TransitAspect(
            transit_planet=planet_a,
            natal_planet=planet_b,
            aspect=aspect,
            orb=round(orb, 2),
            exact=exact,
            applying=applying,
            weight=weight,
            transit_house=None,
            natal_house=None,
            transit_position=pos_a,
            natal_position=pos_b,
        )

    @staticmethod
    def _is_applying(pos_a: PlanetPosition, pos_b: PlanetPosition, aspect: str) -> bool:
        exact_angle = ASPECTS.get(aspect, (0.0, 0.0))[0]
        diff = (pos_a.lon - pos_b.lon) % 360.0
        if diff > 180:
            diff -= 360
        delta = diff - exact_angle
        if delta > 0:
            return pos_a.speed < pos_b.speed
        return pos_a.speed > pos_b.speed


aspect_of_day_service = AspectOfDayService()
