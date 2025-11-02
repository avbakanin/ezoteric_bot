"""Общие функции форматирования для дат, текста и других данных."""

from __future__ import annotations

from datetime import date, datetime


def format_iso_to_display(iso_date: str, default: str = "—") -> str:
    """
    Форматирует ISO дату (YYYY-MM-DD) в формат ДД.ММ.ГГГГ.

    Args:
        iso_date: Дата в формате ISO (YYYY-MM-DD или ISO с временем)
        default: Значение по умолчанию, если форматирование не удалось

    Returns:
        Отформатированная дата в формате ДД.ММ.ГГГГ
    """
    if not iso_date:
        return default

    try:
        # Пробуем разные форматы
        if "T" in iso_date:
            dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(iso_date)
        return dt.strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return iso_date if iso_date else default


def format_date_label(target_date: date, include_year: bool = False) -> str:
    """
    Форматирует дату в читаемый формат с днём недели.

    Args:
        target_date: Дата для форматирования
        include_year: Включать ли год в формат

    Returns:
        Отформатированная строка, например "15.03 (понедельник)" или "15.03.2024 (понедельник)"
    """
    weekdays = [
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ]

    weekday_name = weekdays[target_date.weekday()]

    if include_year:
        date_str = target_date.strftime("%d.%m.%Y")
    else:
        date_str = target_date.strftime("%d.%m")

    return f"{date_str} ({weekday_name})"


def format_today_iso() -> str:
    """Возвращает сегодняшнюю дату в формате ISO (YYYY-MM-DD)."""
    return datetime.now().strftime("%Y-%m-%d")


def format_datetime_iso() -> str:
    """Возвращает текущие дату и время в формате ISO (YYYY-MM-DD HH:MM:SS)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_date_iso(date_obj: date | datetime) -> str:
    """
    Форматирует объект date или datetime в ISO формат (YYYY-MM-DD).

    Args:
        date_obj: Объект date или datetime

    Returns:
        Строка в формате YYYY-MM-DD
    """
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%Y-%m-%d")
    return date_obj.strftime("%Y-%m-%d")


def pluralize_days(value: int) -> str:
    """
    Возвращает правильную форму слова "день" для русского языка.

    Args:
        value: Количество дней

    Returns:
        "день", "дня" или "дней"
    """
    if value % 10 == 1 and value % 100 != 11:
        return "день"
    if value % 10 in (2, 3, 4) and value % 100 not in (12, 13, 14):
        return "дня"
    return "дней"

