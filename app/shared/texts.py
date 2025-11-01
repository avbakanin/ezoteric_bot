"""Работа с текстами чисел."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path

from .storage import user_storage

logger = logging.getLogger(__name__)

NUMBERS_FILE = Path(__file__).resolve().parent.parent.parent / "numbers.json"
_number_texts_cache: dict[str, dict] | None = None


def get_number_texts() -> dict[str, dict]:
    global _number_texts_cache
    if _number_texts_cache is None:
        try:
            with open(NUMBERS_FILE, "r", encoding="utf-8") as f:
                _number_texts_cache = json.load(f)
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка при загрузке numbers.json: %s", exc)
            _number_texts_cache = {}
    return _number_texts_cache


def get_text(number: int, context: str, user_id: int) -> str:
    try:
        number_texts = get_number_texts()
        if str(number) not in number_texts or context not in number_texts[str(number)]:
            return "Информация временно недоступна."

        options = number_texts[str(number)][context]
        shown = user_storage.get_text_history(user_id)
        unused = [text for text in options if text not in shown]
        if not unused:
            unused = options
            user_storage.update_user(user_id, text_history=[])

        chosen = random.choice(unused)
        user_storage.add_text_to_history(user_id, chosen)
        return chosen
    except Exception as exc:  # noqa: BLE001
        logger.error("Ошибка при получении текста: %s", exc)
        return "Произошла ошибка. Попробуйте позже."

