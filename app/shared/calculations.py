"""
Модуль для нумерологических расчетов с учетом мастер-чисел
"""

import json
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.shared.calculations_data import MASTER_NUMBERS, NAME_NUMBER_FALLBACKS, NAME_NUMBER_MAP

# Путь к файлу с аффирмациями
NUMBERS_FILE = Path(__file__).resolve().parent.parent.parent / "numbers.json"

with open(NUMBERS_FILE, "r", encoding="utf-8") as f:
    NUMBERS_DATA = json.load(f)


def reduce_number(number: int) -> int:
    """Сводит число к однозначному, но сохраняет мастер-числа"""
    while number > 9 and number not in MASTER_NUMBERS:
        number = sum(int(d) for d in str(number))
    return number


@dataclass(frozen=True)
class AffirmationResult:
    number: int
    text: str
    date: str | None
    is_new: bool
    is_premium_user: bool
    generated_today: int
    history: list[dict[str, Any]]
    was_forced: bool = False


def _normalize_affirmation_history(raw_history: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entry in raw_history[-10:]:
        if isinstance(entry, dict) and "text" in entry:
            normalized.append(
                {
                    "number": int(entry.get("number")) if entry.get("number") is not None else None,
                    "text": str(entry.get("text", "")),
                    "date": entry.get("date"),
                }
            )
        elif isinstance(entry, str):
            normalized.append(
                {
                    "number": None,
                    "text": entry,
                    "date": None,
                }
            )
    return normalized[-10:]


def get_affirmation(user_id: int | None = None, *, force_new: bool = False) -> AffirmationResult:
    from .storage import user_storage

    try:
        if user_id is None:
            number = int(random.choice(list(NUMBERS_DATA.keys())))
            affirmations = NUMBERS_DATA[str(number)]["affirmations"]
            chosen = random.choice(affirmations)
            today = datetime.now().strftime("%Y-%m-%d")
            return AffirmationResult(
                number=number,
                text=chosen,
                date=today,
                is_new=True,
                is_premium_user=False,
                generated_today=1,
                history=[],
                was_forced=False,
            )

        from .helpers import is_premium as is_premium_check

        user_data = user_storage.get_user(user_id)
        is_premium = is_premium_check(user_id)
        today = datetime.now().strftime("%Y-%m-%d")

        raw_history = user_data.get("affirmation_history", [])
        normalized_history = _normalize_affirmation_history(raw_history if isinstance(raw_history, list) else [])

        if normalized_history != raw_history:
            user_data["affirmation_history"] = normalized_history
            user_storage._save_data()

        generated_today = sum(1 for entry in normalized_history if entry.get("date") == today)
        last_affirmation = normalized_history[-1] if normalized_history else None

        effective_force = bool(force_new and is_premium)

        if not effective_force and last_affirmation and last_affirmation.get("date") == today:
            return AffirmationResult(
                number=int(last_affirmation.get("number") or 0),
                text=last_affirmation.get("text", ""),
                date=last_affirmation.get("date"),
                is_new=False,
                is_premium_user=is_premium,
                generated_today=generated_today or 1,
                history=normalized_history,
                was_forced=False,
            )

        number_key = random.choice(list(NUMBERS_DATA.keys()))
        affirmations = NUMBERS_DATA[number_key]["affirmations"]
        history_texts = {entry.get("text") for entry in normalized_history[-10:] if entry.get("text")}
        available = [a for a in affirmations if a not in history_texts]
        chosen = random.choice(available) if available else random.choice(affirmations)

        new_entry = {
            "number": int(number_key),
            "text": chosen,
            "date": today,
        }

        updated_history = normalized_history + [new_entry]
        user_data["affirmation_history"] = updated_history[-10:]
        user_storage._save_data()

        return AffirmationResult(
            number=int(number_key),
            text=chosen,
            date=today,
            is_new=True,
            is_premium_user=is_premium,
            generated_today=generated_today + 1,
            history=user_data["affirmation_history"],
            was_forced=effective_force,
        )

    except Exception:
        defaults = [
            "Я принимаю себя и доверяю процессу жизни",
            "Каждый день я становлюсь лучше и счастливее",
            "Я открыт для чудес и возможностей вселенной",
            "Моя жизнь наполнена радостью и гармонией",
        ]
        fallback = random.choice(defaults)
        return AffirmationResult(
            number=0,
            text=fallback,
            date=None,
            is_new=True,
            is_premium_user=False,
            generated_today=1,
            history=[],
            was_forced=False,
        )


def calculate_life_path_number(birth_date: str) -> int:
    """Вычисляет число судьбы (жизненный путь) с учетом мастер-чисел"""
    try:
        day, month, year = map(int, birth_date.split("."))
        total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
        return reduce_number(total)
    except Exception:
        return 0


def calculate_soul_number(birth_date: str) -> int:
    """Вычисляет число души (используем день рождения как упрощение)"""
    try:
        day, _, _ = map(int, birth_date.split("."))
        return reduce_number(day)
    except Exception:
        return 0


def calculate_name_number(full_name: str) -> int:
    """Рассчитывает число имени по буквенным значениям"""
    if not full_name:
        return 0

    total = 0
    for char in full_name:
        if char in NAME_NUMBER_MAP:
            total += NAME_NUMBER_MAP[char]

    if total == 0:
        return 0

    return reduce_number(total)


def get_name_number_description(number: int) -> str:
    """Возвращает описание для числа имени"""
    try:
        options = NUMBERS_DATA.get(str(number), {}).get("life_path")
        if options:
            return random.choice(options)
    except Exception:
        pass
    return NAME_NUMBER_FALLBACKS.get(number, "Это число несет в себе индивидуальную вибрацию имени.")


def calculate_daily_number(date: str = None) -> int:
    """Вычисляет число дня для прогноза"""
    if date is None:
        date = datetime.now().strftime("%d.%m.%Y")

    try:
        day, month, year = map(int, date.split("."))
        total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
        return reduce_number(total)
    except Exception:
        return 0


def validate_date(date_str: str) -> bool:
    """Проверяет корректность даты"""
    try:
        day, month, year = map(int, date_str.split("."))
        if year < 1900 or year > 2100:
            return False
        if month < 1 or month > 12:
            return False
        if day < 1 or day > 31:
            return False
        if month in [4, 6, 9, 11] and day > 30:
            return False
        if month == 2:
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                if day > 29:
                    return False
            else:
                if day > 28:
                    return False
        return True
    except Exception:
        return False
