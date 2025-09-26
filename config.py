# Конфигурация бота
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота (получить у @BotFather)
API_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')

# Настройки базы данных
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///numerology_bot.db')

# Настройки уведомлений
NOTIFICATION_TIME = "09:00"  # Время ежедневных уведомлений

# Лимиты для бесплатных пользователей
FREE_DAILY_LIMIT = 3  # Количество запросов в день для бесплатных пользователей
FREE_COMPATIBILITY_LIMIT = 1  # Количество проверок совместимости в день

# Настройки подписки
SUBSCRIPTION_PRICE = 299  # Цена подписки в рублях
SUBSCRIPTION_DURATION = 30  # Длительность подписки в днях