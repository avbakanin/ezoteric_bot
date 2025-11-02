"""Сервис для работы с картами Таро."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TAROT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "tarot-data"

# Кэш для данных
_tarot_data_cache: dict[str, Any] | None = None


def _load_all_tarot_data() -> dict[str, Any]:
    """Загружает все данные карт Таро из файлов с кэшированием в памяти."""
    global _tarot_data_cache
    if _tarot_data_cache is not None:
        return _tarot_data_cache

    _tarot_data_cache = {
        "major": {},
        "minor": {
            "wands": {},
            "cups": {},
            "swords": {},
            "pentacles": {},
        },
        "spreads": {},
    }

    try:
        # Загружаем старшие арканы (оптимизировано: один цикл)
        for file_num in ["01", "02"]:
            file_path = TAROT_DATA_DIR / f"tarot_major_{file_num}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        major_data = data.get("major_arcana", {})
                        _tarot_data_cache["major"].update(major_data)
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning("Ошибка загрузки файла %s: %s", file_path, e)
                    continue

        # Загружаем младшие арканы (оптимизировано: один цикл)
        for suit in ["wands", "cups", "swords", "pentacles"]:
            file_path = TAROT_DATA_DIR / f"tarot_{suit}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        minor_data = data.get("minor_arcana", {}).get(suit, {})
                        if minor_data:
                            _tarot_data_cache["minor"][suit] = minor_data
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning("Ошибка загрузки файла %s: %s", file_path, e)
                    continue

        # Загружаем расклады (один раз)
        spreads_path = TAROT_DATA_DIR / "tarot_spreads.json"
        if spreads_path.exists():
            try:
                with open(spreads_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _tarot_data_cache["spreads"] = data.get("spreads", {})
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Ошибка загрузки файла раскладов: %s", e)

        major_count = len(_tarot_data_cache["major"])
        minor_count = sum(len(s) for s in _tarot_data_cache["minor"].values())
        spreads_count = len(_tarot_data_cache["spreads"])
        logger.info(
            "Данные Таро загружены: %d старших, %d младших, %d раскладов",
            major_count,
            minor_count,
            spreads_count,
        )
    except Exception as exc:
        logger.error("Критическая ошибка при загрузке данных Таро: %s", exc, exc_info=True)
        _tarot_data_cache = {
            "major": {},
            "minor": {"wands": {}, "cups": {}, "swords": {}, "pentacles": {}},
            "spreads": {},
        }

    return _tarot_data_cache


def get_spread_info(spread_key: str) -> dict[str, Any] | None:
    """Получает информацию о раскладе."""
    data = _load_all_tarot_data()
    return data.get("spreads", {}).get(spread_key)


def get_available_spreads(is_premium: bool = False) -> dict[str, dict[str, Any]]:
    """Возвращает доступные расклады для пользователя."""
    data = _load_all_tarot_data()
    spreads = data.get("spreads", {})
    result = {}
    for key, spread in spreads.items():
        is_free = spread.get("free", False)
        is_premium_only = spread.get("premium_only", False)
        if is_free or (is_premium and is_premium_only):
            result[key] = spread
    return result


class TarotCard:
    """Класс для представления карты Таро."""

    def __init__(
        self,
        key: str,
        name: str,
        emoji: str,
        card_type: str,
        suit: str | None = None,
        is_reversed: bool = False,
    ):
        self.key = key
        self.name = name
        self.emoji = emoji
        self.card_type = card_type  # "major" или "minor"
        self.suit = suit  # для младших арканов: wands, cups, swords, pentacles
        self.is_reversed = is_reversed

    def __repr__(self) -> str:
        direction = "перевернутая" if self.is_reversed else "прямая"
        return f"<TarotCard: {self.name} ({direction})>"


def get_all_cards(use_only_major: bool = False) -> list[tuple[str, dict, str, str | None]]:
    """
    Возвращает список всех карт в формате (key, card_data, card_type, suit).

    Args:
        use_only_major: Если True, возвращает только старшие арканы

    Returns:
        Список карт (key, card_data, card_type, suit)
    """
    data = _load_all_tarot_data()

    cards = []

    # Старшие арканы
    for key, card_data in data.get("major", {}).items():
        cards.append((key, card_data, "major", None))

    if not use_only_major:
        # Младшие арканы
        for suit in ["wands", "cups", "swords", "pentacles"]:
            suit_cards = data.get("minor", {}).get(suit, {})
            for key, card_data in suit_cards.items():
                cards.append((key, card_data, "minor", suit))

    return cards


def draw_random_cards(count: int, use_only_major: bool = False, allow_reversed: bool = True) -> list[TarotCard]:
    """
    Выбирает случайные карты из колоды.

    Args:
        count: Количество карт для выбора
        use_only_major: Если True, выбирает только из старших арканов
        allow_reversed: Если True, карты могут быть перевернутыми (50% шанс)

    Returns:
        Список карт TarotCard
    """
    all_cards = get_all_cards(use_only_major=use_only_major)

    if count > len(all_cards):
        count = len(all_cards)

    selected = random.sample(all_cards, count)
    result = []

    for key, card_data, card_type, suit in selected:
        is_reversed = random.choice([True, False]) if allow_reversed else False
        name = card_data.get("name", "Неизвестная карта")
        emoji = card_data.get("emoji", "🃏")

        result.append(
            TarotCard(
                key=key,
                name=name,
                emoji=emoji,
                card_type=card_type,
                suit=suit,
                is_reversed=is_reversed,
            )
        )

    return result


def detect_context_from_question(question: str | None) -> str:
    """
    Определяет контекст интерпретации на основе вопроса.
    
    Args:
        question: Вопрос пользователя
        
    Returns:
        Контекст: general, love, career, health
    """
    if not question:
        return "general"
    
    question_lower = question.lower()
    
    # Ключевые слова для разных контекстов
    love_keywords = ["любовь", "отношени", "партнер", "семья", "брак", "встреча", "расставан", "ревность"]
    career_keywords = ["карьер", "работ", "деньг", "бизнес", "проект", "зарплат", "начальник", "коллег"]
    health_keywords = ["здоровье", "болезн", "самочувств", "лечение", "врач", "медицин"]
    
    if any(keyword in question_lower for keyword in love_keywords):
        return "love"
    elif any(keyword in question_lower for keyword in career_keywords):
        return "career"
    elif any(keyword in question_lower for keyword in health_keywords):
        return "health"
    
    return "general"


def get_card_interpretation(
    card: TarotCard,
    context: str = "general",
) -> str:
    """
    Получает интерпретацию карты.

    Args:
        card: Объект карты TarotCard
        context: Контекст интерпретации (general, love, career, health)

    Returns:
        Текст интерпретации
    """
    data = _load_all_tarot_data()
    direction = "reversed" if card.is_reversed else "upright"

    try:
        if card.card_type == "major":
            card_data = data.get("major", {}).get(card.key)
            if not card_data:
                return "Интерпретация недоступна."
            interpretations = card_data.get(direction, {}).get(context, [])
        else:
            suit_data = data.get("minor", {}).get(card.suit, {})
            card_data = suit_data.get(card.key)
            if not card_data:
                return "Интерпретация недоступна."
            interpretations = card_data.get(direction, [])

        if isinstance(interpretations, list) and interpretations:
            return random.choice(interpretations)
        elif isinstance(interpretations, str):
            return interpretations
        else:
            return "Интерпретация недоступна."
    except Exception as exc:
        logger.error("Ошибка при получении интерпретации карты %s: %s", card.key, exc)
        return "Произошла ошибка при получении интерпретации."


def interpret_spread(
    cards: list[TarotCard],
    spread_key: str,
    context: str = "general",
) -> list[dict[str, Any]]:
    """
    Интерпретирует расклад.

    Args:
        cards: Список выбранных карт
        spread_key: Ключ расклада

    Returns:
        Список словарей с интерпретацией для каждой позиции
    """
    spread_info = get_spread_info(spread_key)
    if not spread_info:
        return []

    positions = spread_info.get("positions", [])
    interpretations = []

    for i, card in enumerate(cards):
        if i >= len(positions):
            position_name = f"Позиция {i + 1}"
            position_meaning = ""
        else:
            position = positions[i]
            position_name = position.get("name", f"Позиция {i + 1}")
            position_meaning = position.get("meaning", "")

        # Используем контекст для интерпретации
        interpretation_text = get_card_interpretation(card, context=context)

        interpretations.append(
            {
                "position_name": position_name,
                "position_meaning": position_meaning,
                "card": card,
                "interpretation": interpretation_text,
            }
        )

    return interpretations


def format_yes_no_answer(card: TarotCard) -> tuple[str, str]:
    """
    Форматирует ответ для расклада Да/Нет.

    Returns:
        Кортеж (ответ, объяснение)
    """
    spread_info = get_spread_info("yes_no")
    if not spread_info:
        return ("Возможно", "Карты не дают четкого ответа.")

    interpretations_map = spread_info.get("interpretations", {})
    card_key = card.key

    if card_key in interpretations_map.get("yes_cards", []):
        answer = "Да"
    elif card_key in interpretations_map.get("no_cards", []):
        answer = "Нет"
    elif card_key in interpretations_map.get("maybe_cards", []):
        answer = "Возможно"
    else:
        # Если карта не в списке, определяем по интерпретации
        interpretation = get_card_interpretation(card)
        if "нет" in interpretation.lower() or "отказ" in interpretation.lower():
            answer = "Нет"
        elif "да" in interpretation.lower() or "успех" in interpretation.lower():
            answer = "Да"
        else:
            answer = "Возможно"

    explanation = get_card_interpretation(card)
    return (answer, explanation)

