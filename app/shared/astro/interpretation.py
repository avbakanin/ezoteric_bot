"""Генерация текстовых интерпретаций для транзитов."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .daily_transits import ForecastResult
from .interpretation_data import ASPECT_NAMES_RU, PLANET_RU
from .transits import TransitAspect

TEMPLATES_PATH = Path(__file__).resolve().parents[3] / "data" / "transit_templates.json"


@dataclass(slots=True)
class RenderedAspect:
    title: str
    text: str
    advice: str
    transit_house_note: str | None = None
    natal_house_note: str | None = None
    retro_note: str | None = None

    def to_text(self) -> str:
        parts = [f"{self.title}", self.text]
        if self.transit_house_note:
            parts.append(self.transit_house_note)
        if self.natal_house_note and self.natal_house_note != self.transit_house_note:
            parts.append(self.natal_house_note)
        if self.retro_note:
            parts.append(self.retro_note)
        parts.append(f"Совет: {self.advice}")
        return "\n".join(parts)


class TransitInterpreter:
    def __init__(self, templates_path: Path = TEMPLATES_PATH):
        self.templates_path = templates_path
        self._data: dict[str, Any] | None = None

    @property
    def data(self) -> dict[str, Any]:
        if self._data is None:
            with open(self.templates_path, "r", encoding="utf-8") as file:
                self._data = json.load(file)
        return self._data

    def render_forecast(self, forecast: ForecastResult) -> str:
        if not forecast.ok:
            missing = ", ".join(forecast.missing_fields)
            return (
                "⚠️ Не хватает данных для натальной карты.\n"
                f"Заполните: {missing}."
            )

        rendered = [
            self._render_aspect(aspect, forecast)
            for aspect in forecast.aspects
        ]
        rendered = [item for item in rendered if item]

        if not rendered:
            return "Сегодня значимые транзиты не зафиксированы. Сохраняйте спокойный ритм."

        paragraphs = [item.to_text() for item in rendered]
        heading = f"✨ Натальная карта дня на {forecast.target_date.strftime('%d.%m.%Y')}"
        return "\n\n".join([heading, *paragraphs])

    def _render_aspect(self, aspect: TransitAspect, forecast: ForecastResult) -> RenderedAspect | None:
        template = self._choose_template(aspect)
        if template is None:
            return None

        title = template["title"].format(**self._build_context(aspect))
        text = template["text"].format(**self._build_context(aspect))
        advice = template["advice"].format(**self._build_context(aspect))

        transit_house_note = self._house_note(aspect.transit_house, prefix="⚡ Транзит затрагивает")
        natal_house_note = self._house_note(aspect.natal_house, prefix="🧭 Натальная тема")
        retro_note = self._retrograde_note(aspect)

        return RenderedAspect(
            title=title,
            text=text,
            advice=advice,
            transit_house_note=transit_house_note,
            natal_house_note=natal_house_note,
            retro_note=retro_note,
        )

    def _house_note(self, house: int | None, prefix: str) -> str | None:
        if not house:
            return None

        meanings = self.data.get("houses", {}).get(str(house))
        if not meanings:
            return None
        return f"{prefix}: {random.choice(meanings)}"

    def _choose_template(self, aspect: TransitAspect) -> dict[str, str] | None:
        data = self.data
        planets = data.get("planets", {})
        transit_block = planets.get(aspect.transit_planet, {})
        aspect_block = transit_block.get(aspect.aspect, {})
        exact_pair = aspect_block.get(aspect.natal_planet)
        if exact_pair:
            return random.choice(exact_pair)

        defaults = data.get("defaults", {}).get(aspect.aspect)
        if defaults:
            return random.choice(defaults)
        return None

    def _build_context(self, aspect: TransitAspect) -> dict[str, Any]:
        return {
            "transit_planet": PLANET_RU.get(aspect.transit_planet, aspect.transit_planet),
            "natal_planet": PLANET_RU.get(aspect.natal_planet, aspect.natal_planet),
            "aspect_name": ASPECT_NAMES_RU.get(aspect.aspect, aspect.aspect),
            "orb": aspect.orb,
        }

    def _retrograde_note(self, aspect: TransitAspect) -> str | None:
        if not aspect.transit_position.retrograde:
            return None
        retro_data = self.data.get("retrograde_notes", {})
        message = retro_data.get(aspect.transit_planet)
        if not message:
            message = "♻️ {transit_planet} движется ретроградно: действуйте вдумчиво, оставьте пространство для корректировок."
        context = self._build_context(aspect)
        return message.format(**context)


transit_interpreter = TransitInterpreter()


