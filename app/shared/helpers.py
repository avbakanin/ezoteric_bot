"""Общие хелперы для работы с пользователями, подписками и временными зонами."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.shared.birth_profiles import birth_profile_storage
from app.shared.storage import user_storage

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]


def is_premium(user_id: int) -> bool:
    """Проверяет, активна ли Premium подписка у пользователя."""
    user = user_storage.get_user(user_id)
    subscription = user.get("subscription", {})
    return bool(subscription.get("active"))


def get_user_timezone(user_id: int) -> str:
    """Возвращает часовой пояс пользователя из профиля или user_storage."""
    profile = birth_profile_storage.get_profile(user_id)
    if profile and profile.get("timezone"):
        return profile["timezone"]
    user = user_storage.get_user(user_id)
    return user.get("timezone") or "UTC"


def get_today_local(tz_name: str) -> date:
    """Возвращает сегодняшнюю дату в указанном часовом поясе."""
    if ZoneInfo is None:
        return date.today()
    try:
        tz = ZoneInfo(tz_name)
        return datetime.now(tz).date()
    except Exception:
        return date.today()


def update_user_activity(user_id: int, feature_name: str = None) -> int:
    """
    Обновляет активность пользователя (стрик) и статистику.
    
    Args:
        user_id: ID пользователя
        feature_name: Название используемой функции (для статистики)
    
    Returns:
        Текущий стрик пользователя
    """
    streak = user_storage.update_streak(user_id)
    # Статистика обновляется отдельно в соответствующих функциях
    return streak


def check_streak_achievements(user_id: int, streak: int) -> list[str]:
    """
    Проверяет достижения, связанные со стриками.
    
    Args:
        user_id: ID пользователя
        streak: Текущий стрик пользователя
    
    Returns:
        Список ID разблокированных достижений
    """
    unlocked = []
    
    # Достижения за стрики
    streak_milestones = {
        "streak_3": 3,
        "streak_7": 7,
        "streak_14": 14,
        "streak_30": 30,
        "streak_60": 60,
        "streak_90": 90,
    }
    
    for achievement_id, milestone in streak_milestones.items():
        if streak == milestone:
            if user_storage.check_and_unlock_achievement(user_id, achievement_id):
                unlocked.append(achievement_id)
    
    return unlocked


def get_achievement_info(achievement_id: str) -> tuple[str, str]:
    """
    Получает название и описание достижения.
    
    Args:
        achievement_id: ID достижения
    
    Returns:
        Кортеж (название, описание)
    """
    from app.shared.messages import MessagesData
    
    achievement_map = {
        # Стрики
        "streak_3": (MessagesData.STREAK_3_NAME, MessagesData.STREAK_3_DESC),
        "streak_7": (MessagesData.STREAK_7_NAME, MessagesData.STREAK_7_DESC),
        "streak_14": (MessagesData.STREAK_14_NAME, MessagesData.STREAK_14_DESC),
        "streak_30": (MessagesData.STREAK_30_NAME, MessagesData.STREAK_30_DESC),
        "streak_60": (MessagesData.STREAK_60_NAME, MessagesData.STREAK_60_DESC),
        "streak_90": (MessagesData.STREAK_90_NAME, MessagesData.STREAK_90_DESC),
        # Базовые достижения
        "first_steps": (MessagesData.ACHIEVEMENT_FIRST_STEPS_NAME, MessagesData.ACHIEVEMENT_FIRST_STEPS_DESC),
        "explorer": (MessagesData.ACHIEVEMENT_EXPLORER_NAME, MessagesData.ACHIEVEMENT_EXPLORER_DESC),
        "tarot_master": (MessagesData.ACHIEVEMENT_TAROT_MASTER_NAME, MessagesData.ACHIEVEMENT_TAROT_MASTER_DESC),
        "tarot_expert": (MessagesData.ACHIEVEMENT_TAROT_EXPERT_NAME, MessagesData.ACHIEVEMENT_TAROT_EXPERT_DESC),
        "astrologer": (MessagesData.ACHIEVEMENT_ASTROLOGER_NAME, MessagesData.ACHIEVEMENT_ASTROLOGER_DESC),
        "diary_writer": (MessagesData.ACHIEVEMENT_DIARY_WRITER_NAME, MessagesData.ACHIEVEMENT_DIARY_WRITER_DESC),
        "diary_master": (MessagesData.ACHIEVEMENT_DIARY_MASTER_NAME, MessagesData.ACHIEVEMENT_DIARY_MASTER_DESC),
        "compatibility_expert": (MessagesData.ACHIEVEMENT_COMPATIBILITY_EXPERT_NAME, MessagesData.ACHIEVEMENT_COMPATIBILITY_EXPERT_DESC),
        "numerologist": (MessagesData.ACHIEVEMENT_NUMEROLOGIST_NAME, MessagesData.ACHIEVEMENT_NUMEROLOGIST_DESC),
    }
    
    return achievement_map.get(achievement_id, ("Достижение", "Разблокировано новое достижение"))


def check_base_achievements(user_id: int) -> list[str]:
    """
    Проверяет базовые достижения на основе статистики пользователя.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Список ID разблокированных достижений
    """
    unlocked = []
    user_data = user_storage.get_user(user_id)
    stats = user_storage.get_stats(user_id)
    achievements = user_storage.get_achievements(user_id)
    already_unlocked = achievements.get("unlocked", [])
    
    # Первые шаги - рассчитал число судьбы
    if "first_steps" not in already_unlocked:
        if user_data.get("life_path_number") is not None:
            if user_storage.check_and_unlock_achievement(user_id, "first_steps"):
                unlocked.append("first_steps")
    
    # Исследователь - использовал 5+ разных функций
    if "explorer" not in already_unlocked:
        functions_used = 0
        if user_data.get("life_path_number") is not None:
            functions_used += 1
        if stats.get("total_tarot_readings", 0) > 0:
            functions_used += 1
        if stats.get("total_diary_entries", 0) > 0:
            functions_used += 1
        if birth_profile_storage.get_profile(user_id):
            functions_used += 1
        if user_data.get("birth_date") and user_data.get("life_path_number"):
            functions_used += 1
        # Проверяем другие функции через usage_stats
        usage = user_storage.get_usage_stats(user_id)
        if usage.get("compatibility_checks", 0) > 0:
            functions_used += 1
        
        if functions_used >= 5:
            if user_storage.check_and_unlock_achievement(user_id, "explorer"):
                unlocked.append("explorer")
    
    # Мастер Таро - 10 раскладов
    if "tarot_master" not in already_unlocked:
        tarot_readings = stats.get("total_tarot_readings", 0)
        if tarot_readings >= 10:
            if user_storage.check_and_unlock_achievement(user_id, "tarot_master"):
                unlocked.append("tarot_master")
    
    # Эксперт Таро - 50 раскладов
    if "tarot_expert" not in already_unlocked:
        tarot_readings = stats.get("total_tarot_readings", 0)
        if tarot_readings >= 50:
            if user_storage.check_and_unlock_achievement(user_id, "tarot_expert"):
                unlocked.append("tarot_expert")
    
    # Астролог - заполнил натальный профиль
    if "astrologer" not in already_unlocked:
        profile = birth_profile_storage.get_profile(user_id)
        if profile and profile.get("birth_date") and profile.get("timezone"):
            if user_storage.check_and_unlock_achievement(user_id, "astrologer"):
                unlocked.append("astrologer")
    
    # Дневник - 7 записей
    if "diary_writer" not in already_unlocked:
        diary_entries = stats.get("total_diary_entries", 0)
        if diary_entries >= 7:
            if user_storage.check_and_unlock_achievement(user_id, "diary_writer"):
                unlocked.append("diary_writer")
    
    # Мастер дневника - 30 записей
    if "diary_master" not in already_unlocked:
        diary_entries = stats.get("total_diary_entries", 0)
        if diary_entries >= 30:
            if user_storage.check_and_unlock_achievement(user_id, "diary_master"):
                unlocked.append("diary_master")
    
    # Эксперт совместимости - 5 проверок
    if "compatibility_expert" not in already_unlocked:
        usage = user_storage.get_usage_stats(user_id)
        compatibility_checks = usage.get("compatibility_checks", 0)
        if compatibility_checks >= 5:
            if user_storage.check_and_unlock_achievement(user_id, "compatibility_expert"):
                unlocked.append("compatibility_expert")
    
    # Нумеролог - использовал все нумерологические функции
    if "numerologist" not in already_unlocked:
        has_life_path = user_data.get("life_path_number") is not None
        has_name_number = False  # Можно добавить отслеживание числа имени
        has_compatibility = user_storage.get_usage_stats(user_id).get("compatibility_checks", 0) > 0
        has_daily_number = user_data.get("daily_number", {}).get("number") is not None
        
        if has_life_path and has_compatibility:
            if user_storage.check_and_unlock_achievement(user_id, "numerologist"):
                unlocked.append("numerologist")
    
    return unlocked


def format_progress_bar(value: int, max_value: int, length: int = 10) -> str:
    """
    Создает текстовый прогресс-бар из эмодзи.
    
    Args:
        value: Текущее значение
        max_value: Максимальное значение
        length: Длина прогресс-бара
    
    Returns:
        Строка с прогресс-баром
    """
    if max_value <= 0:
        filled = 0
    else:
        filled = min(length, int((value / max_value) * length))
    
    filled_chars = "█" * filled
    empty_chars = "░" * (length - filled)
    return f"[{filled_chars}{empty_chars}]"


def get_favorite_feature(stats: dict, usage_stats: dict, user_data: dict) -> str:
    """
    Определяет любимую функцию пользователя на основе статистики.
    
    Args:
        stats: Статистика из user_storage.get_stats()
        usage_stats: Статистика использования из user_storage.get_usage_stats()
        user_data: Данные пользователя
    
    Returns:
        Название любимой функции или "Не определена"
    """
    feature_scores = {}
    
    # Таро
    tarot_count = stats.get("total_tarot_readings", 0)
    if tarot_count > 0:
        feature_scores["🔮 Таро"] = tarot_count
    
    # Дневник
    diary_count = stats.get("total_diary_entries", 0)
    if diary_count > 0:
        feature_scores["📝 Дневник"] = diary_count
    
    # Совместимость
    compatibility_count = usage_stats.get("compatibility_checks", 0)
    if compatibility_count > 0:
        feature_scores["💑 Совместимость"] = compatibility_count
    
    # Число судьбы
    if user_data.get("life_path_number") is not None:
        requests = usage_stats.get("daily_requests", 0)
        if requests > 0:
            feature_scores["🧮 Число судьбы"] = requests
    
    if not feature_scores:
        return "Не определена"
    
    return max(feature_scores.items(), key=lambda x: x[1])[0]


def build_extended_stats_text(user_id: int, is_premium_user: bool = False) -> str:
    """
    Строит текст расширенной статистики для пользователя.
    
    Args:
        user_id: ID пользователя
        is_premium_user: Является ли пользователь Premium
    
    Returns:
        Форматированный текст статистики
    """
    user_data = user_storage.get_user(user_id)
    stats = user_storage.get_stats(user_id)
    usage_stats = user_storage.get_usage_stats(user_id)
    achievements = user_storage.get_achievements(user_id)
    
    lines = ["📊 РАСШИРЕННАЯ СТАТИСТИКА\n"]
    
    # Общая информация
    total_days = stats.get("total_days_active", 0)
    streak_days = achievements.get("streak_days", 0)
    unlocked_achievements = len(achievements.get("unlocked", []))
    
    lines.append(f"📅 Дней с ботом: {total_days}")
    if streak_days > 0:
        from app.shared.formatters import pluralize_days
        days_word = pluralize_days(streak_days)
        lines.append(f"🔥 Текущий стрик: {streak_days} {days_word}")
    lines.append(f"🏆 Достижений: {unlocked_achievements}\n")
    
    # Статистика по функциям
    lines.append("🎯 ИСПОЛЬЗОВАНИЕ ФУНКЦИЙ:\n")
    
    tarot_count = stats.get("total_tarot_readings", 0)
    diary_count = stats.get("total_diary_entries", 0)
    compatibility_count = usage_stats.get("compatibility_checks", 0)
    
    if tarot_count > 0:
        max_tarot = 50 if is_premium_user else 20
        progress = format_progress_bar(tarot_count, max_tarot)
        lines.append(f"🔮 Таро: {tarot_count} раскладов {progress}")
    
    if diary_count > 0:
        max_diary = 100 if is_premium_user else 30
        progress = format_progress_bar(diary_count, max_diary)
        lines.append(f"📝 Дневник: {diary_count} записей {progress}")
    
    if compatibility_count > 0:
        lines.append(f"💑 Совместимость: {compatibility_count} проверок")
    
    # Любимая функция
    favorite = get_favorite_feature(stats, usage_stats, user_data)
    lines.append(f"\n⭐ Любимая функция: {favorite}")
    
    # Premium-статистика (расширенная)
    if is_premium_user:
        lines.append("\n💎 PREMIUM АНАЛИТИКА:\n")
        
        # Детальная статистика
        last_feature = stats.get("last_feature_used", "Не использована")
        lines.append(f"📌 Последняя функция: {last_feature}")
        
        # Статистика по дням
        longest_streak = achievements.get("longest_streak", 0)
        if longest_streak > streak_days:
            from app.shared.formatters import pluralize_days
            longest_word = pluralize_days(longest_streak)
            lines.append(f"🏆 Лучший стрик: {longest_streak} {longest_word}")
        
        # Процент активности
        if total_days > 0:
            # Подсчитываем примерный процент (если есть данные о создании)
            created_at = user_data.get("created_at")
            if created_at:
                try:
                    created = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    days_since_creation = (datetime.now() - created).days
                    if days_since_creation > 0:
                        activity_percent = min(100, int((total_days / days_since_creation) * 100))
                        lines.append(f"📈 Активность: {activity_percent}%")
                except Exception:
                    pass
        
        # Натальный профиль
        profile = birth_profile_storage.get_profile(user_id)
        if profile:
            lines.append("✅ Натальный профиль: заполнен")
        else:
            lines.append("⚠️ Натальный профиль: не заполнен")
    else:
        lines.append("\n💎 Получите Premium для расширенной аналитики!")
    
    return "\n".join(lines)


def get_personalized_recommendation(user_id: int, current_action: str = None) -> tuple[str, str] | None:
    """
    Генерирует персонализированную рекомендацию на основе истории пользователя.
    
    Args:
        user_id: ID пользователя
        current_action: Текущее действие пользователя (tarot, diary, life_path, etc.)
    
    Returns:
        Кортеж (текст рекомендации, callback_data для действия) или None
    """
    user_data = user_storage.get_user(user_id)
    stats = user_storage.get_stats(user_id)
    usage_stats = user_storage.get_usage_stats(user_id)
    achievements = user_storage.get_achievements(user_id)
    
    from app.shared.birth_profiles import birth_profile_storage

    # Проверяем разные сценарии для рекомендаций
    recommendations = []
    
    # Рекомендации на основе текущего действия
    if current_action == "tarot":
        # После Таро предлагаем дневник или лунный планировщик
        diary_count = stats.get("total_diary_entries", 0)
        if diary_count < 3:
            recommendations.append((
                "💡 Запишите свои мысли об этом раскладе в дневник - это поможет лучше понять предсказание.",
                "diary_observation"
            ))
        else:
            recommendations.append((
                "🌙 Проверьте лунный планировщик - узнайте лучшие дни для ваших дел!",
                "lunar_planner"
            ))
    
    elif current_action == "diary":
        # После дневника предлагаем Таро или натальную карту
        tarot_count = stats.get("total_tarot_readings", 0)
        if tarot_count < 5:
            recommendations.append((
                "🔮 Попробуйте карту дня - получите инсайт на сегодня!",
                "tarot"
            ))
        else:
            profile = birth_profile_storage.get_profile(user_id)
            if not profile:
                recommendations.append((
                    "🌌 Заполните натальный профиль для персональных астрологических прогнозов!",
                    "natal_profile"
                ))
    
    elif current_action == "life_path":
        # После расчета числа судьбы предлагаем другие функции
        compatibility_count = usage_stats.get("compatibility_checks", 0)
        if compatibility_count == 0:
            recommendations.append((
                "💑 Проверьте совместимость с близким человеком по датам рождения!",
                "compatibility"
            ))
        else:
            profile = birth_profile_storage.get_profile(user_id)
            if not profile:
                recommendations.append((
                    "🌌 Заполните натальный профиль для персональных прогнозов!",
                    "natal_profile"
                ))
            else:
                recommendations.append((
                    "🌌 Получите натальную карту дня с персональными транзитами!",
                    "natal_chart"
                ))
    
    # Общие рекомендации на основе истории
    if not recommendations:
        # Если давно не использовали дневник
        diary_count = stats.get("total_diary_entries", 0)
        if diary_count > 0 and diary_count < 10:
            from datetime import datetime
            diary_observations = user_data.get("diary_observations", [])
            if diary_observations:
                last_entry = diary_observations[-1]
                entry_date = datetime.strptime(last_entry["date"], "%Y-%m-%d %H:%M:%S")
                days_since = (datetime.now() - entry_date).days
                if days_since >= 3:
                    recommendations.append((
                        "📝 Вы давно не записывали в дневник. Поделитесь своими мыслями!",
                        "diary_observation"
                    ))
        
        # Если не заполнен натальный профиль
        profile = birth_profile_storage.get_profile(user_id)
        if not profile and user_data.get("birth_date"):
            recommendations.append((
                "🌌 Заполните натальный профиль (время и место рождения) для персональных прогнозов!",
                "natal_profile"
            ))
        
        # Если мало используют функции
        total_uses = (
            stats.get("total_tarot_readings", 0) +
            stats.get("total_diary_entries", 0) +
            usage_stats.get("compatibility_checks", 0)
        )
        if total_uses < 5:
            tarot_count = stats.get("total_tarot_readings", 0)
            if tarot_count == 0:
                recommendations.append((
                    "🔮 Попробуйте карту дня - получите инсайт на сегодня!",
                    "tarot"
                ))
            else:
                recommendations.append((
                    "🌙 Проверьте лунный планировщик - узнайте лучшие дни для ваших дел!",
                    "lunar_planner"
                ))
    
    # Возвращаем первую рекомендацию или None
    if recommendations:
        return recommendations[0]
    return None


def generate_daily_challenge(user_id: int) -> tuple[str, dict[str, Any]] | None:
    """
    Генерирует ежедневное задание для пользователя на основе его активности.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Кортеж (challenge_id, challenge_data) или None
    """
    import random
    from datetime import datetime
    
    user_data = user_storage.get_user(user_id)
    stats = user_storage.get_stats(user_id)
    usage_stats = user_storage.get_usage_stats(user_id)
    challenges = user_storage.get_daily_challenges(user_id)
    
    # Проверяем, есть ли уже задание на сегодня
    today = datetime.now().strftime("%Y-%m-%d")
    current = challenges.get("current")
    if current and current.get("date") == today:
        # Уже есть задание на сегодня
        return None
    
    # Генерируем задание на основе активности
    available_challenges = []
    
    # Задание: получить карту дня
    tarot_count = stats.get("total_tarot_readings", 0)
    if tarot_count < 20:  # Если еще не использовали много Таро
        available_challenges.append((
            "get_tarot_card",
            {
                "title": "🔮 Получи карту дня",
                "description": "Получите расклад Таро и узнайте, что ждет вас сегодня",
                "reward": "Разблокируй инсайт на день",
            }
        ))
    
    # Задание: записать в дневник
    diary_count = stats.get("total_diary_entries", 0)
    if diary_count < 30:
        available_challenges.append((
            "write_diary",
            {
                "title": "📝 Запиши в дневник",
                "description": "Поделитесь своими мыслями или благодарностями в дневнике",
                "reward": "Улучши свое самопознание",
            }
        ))
    
    # Задание: получить аффирмацию
    if not user_data.get("affirmation_history"):
        available_challenges.append((
            "get_affirmation",
            {
                "title": "✨ Получи аффирмацию",
                "description": "Получите мотивирующую аффирмацию на день",
                "reward": "Начни день с позитива",
            }
        ))
    
    # Задание: проверить лунный планировщик
    available_challenges.append((
        "check_lunar_planner",
        {
            "title": "🌙 Проверь лунный планировщик",
            "description": "Узнайте лучшие дни для важных дел на этой неделе",
            "reward": "Планируй эффективнее",
        }
    ))
    
    # Задание: получить число дня (для Premium)
    from app.shared.helpers import is_premium
    if is_premium(user_id):
        available_challenges.append((
            "get_daily_number",
            {
                "title": "🌞 Получи число дня",
                "description": "Узнайте персональный прогноз на день",
                "reward": "Узнай, что готовит день",
            }
        ))
    
    # Задание: заполнить натальный профиль (если не заполнен)
    from app.shared.birth_profiles import birth_profile_storage
    profile = birth_profile_storage.get_profile(user_id)
    if not profile:
        available_challenges.append((
            "fill_natal_profile",
            {
                "title": "🌌 Заполни натальный профиль",
                "description": "Добавьте время и место рождения для персональных прогнозов",
                "reward": "Получи персональные астрологические прогнозы",
            }
        ))
    
    # Выбираем случайное задание из доступных
    if available_challenges:
        return random.choice(available_challenges)
    
    return None


def check_daily_challenge_completion(user_id: int, action: str) -> tuple[bool, dict[str, Any] | None]:
    """
    Проверяет, выполнено ли текущее ежедневное задание.
    
    Args:
        user_id: ID пользователя
        action: Выполненное действие (tarot, diary, affirmation, etc.)
    
    Returns:
        Кортеж (is_completed, challenge_data) или (False, None)
    """
    challenges = user_storage.get_daily_challenges(user_id)
    current = challenges.get("current")
    
    if not current:
        return False, None
    
    today = datetime.now().strftime("%Y-%m-%d")
    if current.get("date") != today:
        return False, None
    
    challenge_id = current.get("id")
    
    # Маппинг действий на задания
    action_to_challenge = {
        "tarot": "get_tarot_card",
        "diary": "write_diary",
        "affirmation": "get_affirmation",
        "lunar_planner": "check_lunar_planner",
        "daily_number": "get_daily_number",
        "natal_profile": "fill_natal_profile",
    }
    
    expected_challenge = action_to_challenge.get(action)
    
    if challenge_id == expected_challenge:
        # Задание выполнено
        was_first_time = user_storage.complete_daily_challenge(user_id)
        if was_first_time:
            return True, current
    
    return False, None

