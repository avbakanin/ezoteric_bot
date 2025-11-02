"""
Константы и данные для натального профиля.
"""

# Слова для выхода из процесса ввода
EXIT_WORDS: set[str] = {"выход", "cancel", "отмена", "exit"}

# Популярные часовые пояса для выбора
POPULAR_TIMEZONES: list[tuple[str, str]] = [
    ("Europe/Moscow", "🇷🇺 Москва"),
    ("Europe/Kaliningrad", "🇷🇺 Калининград"),
    ("Europe/Samara", "🇷🇺 Самара"),
    ("Asia/Yekaterinburg", "🇷🇺 Екатеринбург"),
    ("Asia/Almaty", "🇰🇿 Алматы"),
    ("America/New_York", "🇺🇸 Нью-Йорк"),
]

