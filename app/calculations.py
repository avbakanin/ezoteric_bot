"""
Модуль нумерологических расчетов и аффирмаций
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from app.user_storage import user_storage

# Загружаем данные из numbers.json
BASE_DIR = Path(__file__).parent
NUMBERS_FILE = BASE_DIR / "numbers.json"

try:
    with open(NUMBERS_FILE, "r", encoding="utf-8") as f:
        NUMBERS_DATA: Dict[str, Dict] = json.load(f)
except Exception as e:
    print(f"Ошибка загрузки numbers.json: {e}")
    NUMBERS_DATA: Dict[str, Dict] = {}


def calculate_life_path_number(birth_date: str) -> int:
    """Вычисляет число судьбы (жизненный путь)"""
    try:
        day, month, year = map(int, birth_date.split("."))
        total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
        while total > 9 and total not in [11, 22, 33]:
            total = sum(int(d) for d in str(total))
        return total
    except Exception:
        return 0


def calculate_soul_number(birth_date: str) -> int:
    """Вычисляет число души (для упрощения — день рождения)"""
    try:
        day, month, year = map(int, birth_date.split("."))
        total = day
        while total > 9:
            total = sum(int(d) for d in str(total))
        return total
    except Exception:
        return 0


def calculate_daily_number(date: Optional[str] = None) -> int:
    """Вычисляет число дня для прогноза"""
    if not date:
        date = datetime.now().strftime("%d.%m.%Y")
    try:
        day, month, year = map(int, date.split("."))
        total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
        while total > 9:
            total = sum(int(d) for d in str(total))
        return total
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


def get_affirmation(number: int, user_id: Optional[int] = None) -> str:
    """
    Генерирует аффирмацию для числа из numbers.json, исключая последние 10 показанных пользователю.
    """
    try:
        str_number = str(number)
        affirmations = NUMBERS_DATA.get(str_number, {}).get("affirmations", [])

        if user_id and affirmations:
            user_data = user_storage.get_user(user_id)
            history = user_data.get("affirmation_history", [])
            recent_texts = [a["text"] for a in history[-10:]]
            available = [a for a in affirmations if a not in recent_texts]
            if available:
                return random.choice(available)

        if affirmations:
            return random.choice(affirmations)

        # Дефолтные аффирмации
        defaults = [
            "Я принимаю себя и доверяю процессу жизни",
            "Каждый день я становлюсь лучше и счастливее",
            "Я открыт для чудес и возможностей вселенной",
            "Моя жизнь наполнена радостью и гармонией",
        ]
        return random.choice(defaults)

    except Exception:
        return "Я доверяю мудрости вселенной и принимаю её дары"


def get_daily_number_for_user(user_id: int) -> int:
    """
    Возвращает число дня для пользователя с учетом даты рождения и кэша.
    """
    user_data = user_storage.get_user(user_id)
    birth_date = user_data.get("birth_date")
    if not birth_date:
        return 0

    cache = user_storage.get_cached_result(user_id)
    if cache and cache.get("daily_number_result") is not None:
        return cache["daily_number_result"]

    daily_number = calculate_daily_number()
    cache_data = cache or {}
    cache_data["daily_number_result"] = daily_number
    user_storage.data[str(user_id)]["daily_cache"].update(cache_data)
    return daily_number
