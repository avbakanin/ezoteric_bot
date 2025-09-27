"""
Модуль для нумерологических расчетов
"""

import json
import random
from datetime import datetime
from pathlib import Path

from storage import user_storage

# Путь к файлу с аффирмациями
NUMBERS_FILE = Path(__file__).parent.parent / "numbers.json"

print(NUMBERS_FILE, Path(__file__).parent)

with open(NUMBERS_FILE, "r", encoding="utf-8") as f:
    NUMBERS_DATA = json.load(f)


def get_affirmation(user_id: int = None) -> tuple[int, str]:
    """
    Возвращает случайную аффирмацию для пользователя.
    Если передан user_id, старается не повторять последние 10 аффирмаций.

    Returns:
        Tuple[number, text] — число и текст аффирмации
    """
    try:
        number = random.choice(list(NUMBERS_DATA.keys()))
        affirmations = NUMBERS_DATA[number]["affirmations"]

        # Проверка истории пользователя
        if user_id:
            user_data = user_storage.get_user(user_id)
            history = [a["text"] for a in user_data.get("affirmation_history", [])[-10:]]
            available = [a for a in affirmations if a not in history]
            if available:
                chosen = random.choice(available)
            else:
                chosen = random.choice(affirmations)
        else:
            chosen = random.choice(affirmations)

        return int(number), chosen

    except Exception as e:
        # На случай ошибки возвращаем запасную аффирмацию
        defaults = [
            "Я принимаю себя и доверяю процессу жизни",
            "Каждый день я становлюсь лучше и счастливее",
            "Я открыт для чудес и возможностей вселенной",
            "Моя жизнь наполнена радостью и гармонией",
        ]
        return 0, random.choice(defaults)


def calculate_life_path_number(birth_date: str) -> int:
    """
    Вычисляет число судьбы (жизненного пути) по дате рождения

    Args:
        birth_date: Дата рождения в формате ДД.ММ.ГГГГ

    Returns:
        Число судьбы от 1 до 9
    """
    try:
        day, month, year = map(int, birth_date.split("."))

        # Суммируем все цифры даты рождения
        total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")

        # Сводим к однозначному числу, кроме 11, 22, 33 (мастер-числа)
        while total > 9 and total not in [11, 22, 33]:
            total = sum(int(d) for d in str(total))

        return total
    except:
        return 0


def calculate_soul_number(birth_date: str) -> int:
    """
    Вычисляет число души по дате рождения
    Число души = сумма гласных букв в полном имени

    Args:
        birth_date: Дата рождения в формате ДД.ММ.ГГГГ

    Returns:
        Число души от 1 до 9
    """
    try:
        day, month, year = map(int, birth_date.split("."))

        # Для упрощения используем день рождения
        # В реальной нумерологии нужно полное имя
        total = day

        while total > 9:
            total = sum(int(d) for d in str(total))

        return total
    except:
        return 0


def calculate_daily_number(date: str = None) -> int:
    """
    Вычисляет число дня для прогноза

    Args:
        date: Дата в формате ДД.ММ.ГГГГ (по умолчанию сегодня)

    Returns:
        Число дня от 1 до 9
    """
    if date is None:
        date = datetime.now().strftime("%d.%m.%Y")

    try:
        day, month, year = map(int, date.split("."))

        total = sum(int(d) for d in f"{day:02d}{month:02d}{year}")

        while total > 9:
            total = sum(int(d) for d in str(total))

        return total
    except:
        return 0


def validate_date(date_str: str) -> bool:
    """
    Проверяет корректность даты

    Args:
        date_str: Дата в формате ДД.ММ.ГГГГ

    Returns:
        True если дата корректна, False иначе
    """
    try:
        day, month, year = map(int, date_str.split("."))

        # Проверяем диапазон годов
        if year < 1900 or year > 2100:
            return False

        # Проверяем месяц
        if month < 1 or month > 12:
            return False

        # Проверяем день
        if day < 1 or day > 31:
            return False

        # Проверяем конкретные месяцы
        if month in [4, 6, 9, 11] and day > 30:
            return False

        # Проверяем февраль
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
