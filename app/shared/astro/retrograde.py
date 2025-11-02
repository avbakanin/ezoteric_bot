"""Сервис для расчёта ретроградных периодов и подготовка уведомлений."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Sequence

from app.shared.messages import MessagesData

from .ephemeris import EphemerisService, ephemeris_service
from .retrograde_data import DEFAULT_BEFORE_GUIDE, DEFAULT_DURING_GUIDE, GUIDES, PLANET_NAMES_RU

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetroPeriod:
    planet: str
    start: date
    end: date | None
    pre_alert: date

    def contains(self, target: date) -> bool:
        if self.end is None:
            return self.start <= target
        return self.start <= target <= self.end


class RetrogradeService:
    def __init__(self, ephemeris: EphemerisService = ephemeris_service):
        self.ephemeris = ephemeris
        # Базовые планеты для всех пользователей
        self.base_planets: Sequence[str] = ("Mercury",)
        # Полный список планет для Premium
        self.tracked_planets: Sequence[str] = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")
        self.pre_alert_days = 3
        
        # Маппинг планет на объяснения для Premium
        self._premium_explanations: dict[str, str] = {
            "Mercury": MessagesData.RETRO_MERCURY_EXPLANATION,
            "Venus": MessagesData.RETRO_VENUS_EXPLANATION,
            "Mars": MessagesData.RETRO_MARS_EXPLANATION,
            "Jupiter": MessagesData.RETRO_JUPITER_EXPLANATION,
            "Saturn": MessagesData.RETRO_SATURN_EXPLANATION,
        }
        
        # Маппинг планет на краткие объяснения для Free
        self._free_explanations: dict[str, str] = {
            "Mercury": MessagesData.RETRO_FREE_MERCURY,
            "Venus": MessagesData.RETRO_FREE_VENUS,
            "Mars": MessagesData.RETRO_FREE_MARS,
            "Jupiter": MessagesData.RETRO_FREE_JUPITER,
            "Saturn": MessagesData.RETRO_FREE_SATURN,
        }

    def get_periods(self, start_date: date, end_date: date) -> Dict[str, List[RetroPeriod]]:
        analysis_start = start_date - timedelta(days=30)
        analysis_end = end_date + timedelta(days=60)
        statuses = self._compute_statuses(analysis_start, analysis_end)
        periods: Dict[str, List[RetroPeriod]] = {}
        for planet in self.tracked_planets:
            periods[planet] = self._extract_periods(planet, statuses, start_date, end_date)
        return periods

    def get_next_period(self, planet: str, periods: List[RetroPeriod], reference_date: date) -> RetroPeriod | None:
        upcoming = [
            period
            for period in periods
            if period.start >= reference_date or period.contains(reference_date)
        ]
        if not upcoming:
            return None
        upcoming.sort(key=lambda p: p.start)
        return upcoming[0]

    def format_pre_alert(self, period: RetroPeriod, is_premium: bool, today: date) -> str:
        days = max((period.start - today).days, 0)
        planet_name = PLANET_NAMES_RU.get(period.planet, period.planet)
        start_str = period.start.strftime("%d.%m.%Y")
        end_str = period.end.strftime("%d.%m.%Y") if period.end else "неизвестно"
        days_word = self._pluralize_days(days)
        if is_premium:
            lines = [
                MessagesData.RETRO_PRE_ALERT_PREMIUM_HEADER.format(
                    planet=planet_name,
                    start_date=start_str,
                    end_date=end_str,
                    days=days,
                    days_word=days_word,
                )
            ]
            tasks = self._get_planet_guide(period.planet, phase="pre")
            if tasks:
                lines.append(MessagesData.RETRO_PRE_ALERT_PREMIUM_LIST)
                lines.extend(f"• {item}" for item in tasks)
            return "\n".join(lines)
        message = MessagesData.RETRO_PRE_ALERT_FREE.format(
            planet=planet_name,
            start_date=start_str,
            end_date=end_str,
            days=days,
            days_word=days_word,
        )
        return "\n\n".join(
            [
                message,
                MessagesData.RETRO_ALERTS_PREMIUM_ONLY,
                MessagesData.RETRO_ALERTS_PREMIUM_CTA,
            ]
        )

    def format_start_alert(self, period: RetroPeriod, is_premium: bool) -> str:
        planet_name = PLANET_NAMES_RU.get(period.planet, period.planet)
        start_str = period.start.strftime("%d.%m.%Y")
        end_str = period.end.strftime("%d.%m.%Y") if period.end else MessagesData.RETRO_START_NO_END
        if is_premium:
            lines = [
                MessagesData.RETRO_START_PREMIUM_HEADER.format(
                    planet=planet_name,
                    start_date=start_str,
                    end_date=end_str,
                )
            ]
            tasks = self._get_planet_guide(period.planet, phase="during")
            if tasks:
                lines.append(MessagesData.RETRO_START_PREMIUM_LIST)
                lines.extend(f"• {item}" for item in tasks)
            return "\n".join(lines)
        message = MessagesData.RETRO_START_FREE.format(
            planet=planet_name,
            start_date=start_str,
            end_date=end_str,
        )
        return "\n\n".join(
            [
                message,
                MessagesData.RETRO_ALERTS_PREMIUM_ONLY,
                MessagesData.RETRO_ALERTS_PREMIUM_CTA,
            ]
        )

    def format_summary(self, period: RetroPeriod, is_premium: bool, today: date) -> str:
        planet_name = PLANET_NAMES_RU.get(period.planet, period.planet)
        start_str = period.start.strftime("%d.%m.%Y")
        end_str = period.end.strftime("%d.%m.%Y") if period.end else MessagesData.RETRO_START_NO_END
        pre_str = period.pre_alert.strftime("%d.%m.%Y")
        
        if period.contains(today):
            base_message = MessagesData.RETRO_ALERTS_SUMMARY_ACTIVE.format(
                planet=planet_name,
                start_date=start_str,
                end_date=end_str,
            )
        else:
            base_message = MessagesData.RETRO_ALERTS_SUMMARY_UPCOMING.format(
            planet=planet_name,
            start_date=start_str,
            end_date=end_str,
            pre_alert=pre_str,
        )
        
        # Добавляем объяснение ретроградности
        explanation = self._get_retrograde_explanation(period.planet, is_premium)
        return base_message + explanation
    
    def _get_retrograde_explanation(self, planet: str, is_premium: bool) -> str:
        """Возвращает объяснение ретроградности для планеты."""
        if is_premium:
            # Для Premium - подробное объяснение для каждой планеты
            return self._premium_explanations.get(planet, MessagesData.RETRO_WHAT_IS_RETROGRADE)
        else:
            # Для Free - базовое объяснение + краткое по планетам
            explanation = MessagesData.RETRO_WHAT_IS_RETROGRADE
            planet_explanation = self._free_explanations.get(planet)
            if planet_explanation:
                explanation += planet_explanation
            else:
                # Для других планет (если добавят в будущем)
                explanation += "\n\n💎 Оформите Premium для подробных рекомендаций!"
            return explanation

    def _compute_statuses(self, start_date: date, end_date: date) -> Dict[date, Dict[str, bool]]:
        statuses: Dict[date, Dict[str, bool]] = {}
        current = start_date
        step_time = time(hour=12, minute=0)
        while current <= end_date:
            dt = datetime.combine(current, step_time)
            ephemeris = self.ephemeris.get_ephemeris(dt, planets=self.tracked_planets)
            statuses[current] = {planet: ephemeris[planet].retrograde for planet in self.tracked_planets}
            current += timedelta(days=1)
        return statuses

    def _extract_periods(
        self,
        planet: str,
        statuses: Dict[date, Dict[str, bool]],
        start_date: date,
        end_date: date,
    ) -> List[RetroPeriod]:
        dates = sorted(statuses.keys())
        if not dates:
            return []

        periods: List[RetroPeriod] = []
        prev_status = statuses[dates[0]][planet]
        current_start: date | None = dates[0] if prev_status else None

        for day in dates[1:]:
            status = statuses[day][planet]
            if not prev_status and status:
                current_start = day
            elif prev_status and not status:
                if current_start is None:
                    current_start = dates[0]
                end_day = day - timedelta(days=1)
                self._append_period(periods, planet, current_start, end_day)
                current_start = None
            prev_status = status

        if prev_status and current_start is not None:
            self._append_period(periods, planet, current_start, None)

        # Оставляем только релевантные периоды
        filtered: List[RetroPeriod] = []
        for period in periods:
            if period.end and period.end < start_date - timedelta(days=30):
                continue
            if period.start > end_date + timedelta(days=60):
                continue
            filtered.append(period)
        filtered.sort(key=lambda p: p.start)
        return filtered

    def _append_period(self, periods: List[RetroPeriod], planet: str, start: date, end: date | None) -> None:
        pre_alert = start - timedelta(days=self.pre_alert_days)
        periods.append(RetroPeriod(planet=planet, start=start, end=end, pre_alert=pre_alert))

    def _get_planet_guide(self, planet: str, phase: str) -> List[str]:
        guide = GUIDES.get(planet)
        if not guide:
            return DEFAULT_BEFORE_GUIDE if phase == "pre" else DEFAULT_DURING_GUIDE
        return guide.get(phase, DEFAULT_BEFORE_GUIDE if phase == "pre" else DEFAULT_DURING_GUIDE)

    @staticmethod
    def _pluralize_days(days: int) -> str:
        if days % 10 == 1 and days % 100 != 11:
            return "день"
        if 2 <= days % 10 <= 4 and not 12 <= days % 100 <= 14:
            return "дня"
        return "дней"


retrograde_service = RetrogradeService()


