"""
Конфигурация бота
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# ID администратора (для безопасности)
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

# База данных
DATABASE_PATH = 'crm_bot.db'

# Настройки по умолчанию
DEFAULT_COMMISSION = 15.0  # Процент комиссии площадки