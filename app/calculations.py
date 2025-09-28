"""
Модуль для нумерологических расчетов с учетом мастер-чисел
"""

import json
import random
from datetime import datetime
from pathlib import Path

# Путь к файлу с аффирмациями
NUMBERS_FILE = Path(__file__).parent.parent / "numbers.json"

with open(NUMBERS_FILE, "r", encoding="utf-8") as f:
    NUMBERS_DATA = json.load(f)

MASTER_NUMBERS = [11, 22, 33]  # Мастер-числа, которые не редуцируем


def reduce_number(number: int) -> int:
    """Сводит число к однозначному, но сохраняет мастер-числа"""
    while number > 9 and number not in MASTER_NUMBERS:
        number = sum(int(d) for d in str(number))
    return number


def get_affirmation(user_id: int = None) -> tuple[int, str]:
    from storage import user_storage

    try:
        number = random.choice(list(NUMBERS_DATA.keys()))
        affirmations = NUMBERS_DATA[number]["affirmations"]

        if user_id:
            user_data = user_storage.get_user(user_id)
            history = [a["text"] for a in user_data.get("affirmation_history", [])[-10:]]
            available = [a for a in affirmations if a not in history]
            chosen = random.choice(available) if available else random.choice(affirmations)

            if "affirmation_history" not in user_data:
                user_data["affirmation_history"] = []
            user_data["affirmation_history"].append({"number": int(number), "text": chosen})
            user_data["affirmation_history"] = user_data["affirmation_history"][-10:]
            user_storage._save_data()
        else:
            chosen = random.choice(affirmations)

        return int(number), chosen
    except Exception:
        defaults = [
            "Я принимаю себя и доверяю процессу жизни",
            "Каждый день я становлюсь лучше и счастливее",
            "Я открыт для чудес и возможностей вселенной",
            "Моя жизнь наполнена радостью и гармонией",
        ]
        return 0, random.choice(defaults)


def calculate_life_path_number(birth_date: str) -> int:
    """Вычисляет число судьбы (жизненный путь) с учетом мастер-чисел"""
    try:
        day, month, year = map(int, birth_date.split("."))
        total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
        return reduce_number(total)
    except:
        return 0


def calculate_soul_number(birth_date: str) -> int:
    """Вычисляет число души (используем день рождения как упрощение)"""
    try:
        day, _, _ = map(int, birth_date.split("."))
        return reduce_number(day)
    except:
        return 0


def calculate_daily_number(date: str = None) -> int:
    """Вычисляет число дня для прогноза"""
    if date is None:
        date = datetime.now().strftime("%d.%m.%Y")

    try:
        day, month, year = map(int, date.split("."))
        total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")
        return reduce_number(total)
    except:
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
    except:
        return False
