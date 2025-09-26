"""
Модуль для нумерологических расчетов
"""

from datetime import datetime
from typing import Tuple, Dict, Any


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