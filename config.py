import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Bot Server Configuration
    WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 5000))
    WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', '0.0.0.0')
    
    # Health Check Configuration
    HEALTH_CHECK_INTERVAL = int(os.getenv('HEALTH_CHECK_INTERVAL', 300))
    HEALTH_CHECK_TIMEOUT = int(os.getenv('HEALTH_CHECK_TIMEOUT', 10))
    
    # Monitoring Configuration
    MONITOR_URLS = [
        url.strip() 
        for url in os.getenv('MONITOR_URLS', '').split(',') 
        if url.strip()
    ]
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not cls.TELEGRAM_CHAT_ID:
            raise ValueError("TELEGRAM_CHAT_ID is required")
        return True
