"""
Модуль для нумерологических расчетов с учетом мастер-чисел
"""

import json
import random
from datetime import datetime
from pathlib import Path

# Путь к файлу с аффирмациями
NUMBERS_FILE = Path(__file__).resolve().parent.parent.parent / "numbers.json"

with open(NUMBERS_FILE, "r", encoding="utf-8") as f:
    NUMBERS_DATA = json.load(f)

MASTER_NUMBERS = [11, 22, 33]  # Мастер-числа, которые не редуцируем


def _build_name_number_map() -> dict[str, int]:
    mapping = {
        1: ["A", "J", "S", "А", "И", "С", "Ъ", "Ь"],
        2: ["B", "K", "T", "Б", "Й", "Т", "Ы"],
        3: ["C", "L", "U", "В", "К", "У", "Э"],
        4: ["D", "M", "V", "Г", "Л", "Ф", "Ю"],
        5: ["E", "N", "W", "Д", "М", "Х", "Я"],
        6: ["F", "O", "X", "Е", "Ё", "Н", "Ц"],
        7: ["G", "P", "Y", "Ж", "О", "Ч", "Щ"],
        8: ["H", "Q", "Z", "З", "П", "Ш"],
        9: ["I", "R", "Р"],
    }
    result: dict[str, int] = {}
    for value, letters in mapping.items():
        for letter in letters:
            result[letter.upper()] = value
            result[letter.lower()] = value
    return result


NAME_NUMBER_MAP = _build_name_number_map()

NAME_NUMBER_FALLBACKS = {
    1: "Лидерство, независимость и стремление быть первым.",
    2: "Сотрудничество, дипломатия и умение слышать других.",
    3: "Творческое самовыражение, вдохновение и оптимизм.",
    4: "Практичность, системность и стабильность во всем.",
    5: "Любознательность, перемены и свобода действий.",
    6: "Ответственность, забота и стремление к гармонии.",
    7: "Аналитический ум, интуиция и поиск глубинного смысла.",
    8: "Амбиции, управление ресурсами и материальный успех.",
    9: "Гуманизм, эмпатия и желание помогать миру.",
    11: "Интуитивная сила, духовность и вдохновение для других.",
    22: "Созидательная энергия мастера, достигающего великих целей.",
    33: "Бескорыстное служение и духовное наставничество.",
}


def reduce_number(number: int) -> int:
    """Сводит число к однозначному, но сохраняет мастер-числа"""
    while number > 9 and number not in MASTER_NUMBERS:
        number = sum(int(d) for d in str(number))
    return number


def get_affirmation(user_id: int = None) -> tuple[int, str]:
    from datetime import datetime

    from .storage import user_storage

    try:
        if user_id:
            user_data = user_storage.get_user(user_id)
            today = datetime.now().strftime("%Y-%m-%d")

            # Проверяем, есть ли аффирмация на сегодня
            affirmation_history = user_data.get("affirmation_history", [])
            if affirmation_history:
                last_affirmation = affirmation_history[-1]
                last_date = last_affirmation.get("date", "")

                # Если аффирмация уже была сегодня - возвращаем её
                if last_date == today:
                    return last_affirmation.get("number", 0), last_affirmation.get("text", "")

            # Генерируем новую аффирмацию для нового дня
            number = random.choice(list(NUMBERS_DATA.keys()))
            affirmations = NUMBERS_DATA[number]["affirmations"]

            history_texts = [a["text"] for a in affirmation_history[-10:]]
            available = [a for a in affirmations if a not in history_texts]
            chosen = random.choice(available) if available else random.choice(affirmations)

            # Сохраняем с датой
            if "affirmation_history" not in user_data:
                user_data["affirmation_history"] = []
            user_data["affirmation_history"].append(
                {
                    "number": int(number),
                    "text": chosen,
                    "date": today,
                }
            )
            user_data["affirmation_history"] = user_data["affirmation_history"][-10:]
            user_storage._save_data()

            return int(number), chosen
        else:
            # Без user_id - просто случайная аффирмация
            number = random.choice(list(NUMBERS_DATA.keys()))
            affirmations = NUMBERS_DATA[number]["affirmations"]
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
