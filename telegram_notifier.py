import logging
import requests
from config import Config

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Handles sending notifications to Telegram using requests library"""
    
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send a message to the configured chat"""
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Message sent successfully to chat {self.chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {str(e)}")
            return False
    
    def send_health_report(self, report: str) -> bool:
        """Send health check report"""
        return self.send_message(report)
    
    def send_gitlab_notification(self, notification: str) -> bool:
        """Send GitLab event notification"""
        return self.send_message(notification)
    
    def send_alert(self, alert: str) -> bool:
        """Send alert message"""
        return self.send_message(f"🚨 **ALERT**\n\n{alert}")
    
    def test_connection(self) -> bool:
        """Test bot connection and permissions"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            bot_info = response.json().get('result', {})
            bot_username = bot_info.get('username', 'Unknown')
            logger.info(f"Bot connected: @{bot_username}")
            
            # Try to send a test message
            test_message = "✅ Bot connection test successful!"
            self.send_message(test_message)
            return True
        except Exception as e:
            logger.error(f"Bot connection test failed: {str(e)}")
            return False
