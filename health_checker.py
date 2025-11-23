import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional
from config import Config

logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(self):
        self.last_status: Dict[str, bool] = {}
        self.endpoints_to_check = [
            {'url': url, 'name': self._extract_env_name(url)}
            for url in Config.MONITOR_URLS
        ]
    
    @staticmethod
    def _extract_env_name(url: str) -> str:
        """Extract environment name from URL"""
        if 'dev' in url.lower():
            return 'Development'
        elif 'preprod' in url.lower() or 'pre-prod' in url.lower():
            return 'Pre-Production'
        elif 'prod' in url.lower():
            return 'Production'
        return url
    
    def check_endpoint(self, endpoint: Dict[str, str]) -> Dict:
        """Check if an endpoint is healthy"""
        url = endpoint['url']
        name = endpoint['name']
        
        try:
            # Try to hit the actuator health endpoint first, fallback to base URL
            health_urls = [
                f"{url}/actuator/health",
                f"{url}/api/health",
                f"{url}/health",
                url
            ]
            
            response = None
            for health_url in health_urls:
                try:
                    response = requests.get(
                        health_url,
                        timeout=Config.HEALTH_CHECK_TIMEOUT,
                        allow_redirects=True
                    )
                    if response.status_code == 200:
                        break
                except requests.RequestException:
                    continue
            
            if response and response.status_code == 200:
                return {
                    'name': name,
                    'url': url,
                    'status': 'UP',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'name': name,
                    'url': url,
                    'status': 'DOWN',
                    'status_code': response.status_code if response else None,
                    'error': f"HTTP {response.status_code}" if response else "No response",
                    'timestamp': datetime.now().isoformat()
                }
                
        except requests.exceptions.Timeout:
            return {
                'name': name,
                'url': url,
                'status': 'DOWN',
                'error': 'Timeout',
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.ConnectionError:
            return {
                'name': name,
                'url': url,
                'status': 'DOWN',
                'error': 'Connection Error',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking {url}: {str(e)}")
            return {
                'name': name,
                'url': url,
                'status': 'DOWN',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_all(self) -> List[Dict]:
        results = []
        for endpoint in self.endpoints_to_check:
            result = self.check_endpoint(endpoint)
            results.append(result)
        return results
    
    def get_status_changes(self, current_results: List[Dict]) -> List[Dict]:
        """Detect status changes from previous check"""
        changes = []
        
        for result in current_results:
            url = result['url']
            current_status = result['status'] == 'UP'
            previous_status = self.last_status.get(url)
            
            # Status changed
            if previous_status is not None and previous_status != current_status:
                changes.append({
                    'name': result['name'],
                    'url': url,
                    'previous': 'UP' if previous_status else 'DOWN',
                    'current': 'UP' if current_status else 'DOWN',
                    'result': result
                })
            
            # Update last status
            self.last_status[url] = current_status
        
        return changes
    
    def format_health_report(self, results: List[Dict], include_all: bool = False) -> str:
        """Format health check results as a message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        up_count = sum(1 for r in results if r['status'] == 'UP')
        down_count = len(results) - up_count
        
        message = "🏥 *Health Check Report*\n"
        message += f"⏰ {timestamp}\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if up_count == len(results):
            message += f"✅ All services are UP ({up_count}/{len(results)})\n\n"
        else:
            message += f"⚠️ {down_count} service(s) DOWN, {up_count} UP\n\n"
        
        # Show all results if requested or if there are issues
        if include_all or down_count > 0:
            for result in results:
                status_emoji = "✅" if result['status'] == 'UP' else "❌"
                message += f"{status_emoji} *{result['name']}*\n"
                
                if result['status'] == 'UP':
                    response_time = result.get('response_time', 0)
                    message += f"   Status: {result['status']} ({response_time:.2f}s)\n"
                else:
                    error = result.get('error', 'Unknown error')
                    message += f"   Status: {result['status']}\n"
                    message += f"   Error: {error}\n"
                
                # Don't use code blocks for URLs - they can cause issues
                message += f"   URL: {result['url']}\n\n"
        
        return message
    
    def format_status_change_alert(self, changes: List[Dict]) -> Optional[str]:
        """Format status change alerts"""
        if not changes:
            return None
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        message = "🚨 *Service Status Alert*\n"
        message += f"⏰ {timestamp}\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for change in changes:
            if change['current'] == 'UP':
                emoji = "✅"
                message += f"{emoji} *{change['name']}* is now UP\n"
                message += f"   Previous: {change['previous']} → Current: {change['current']}\n"
            else:
                emoji = "❌"
                message += f"{emoji} *{change['name']}* is now DOWN\n"
                message += f"   Previous: {change['previous']} → Current: {change['current']}\n"
                error = change['result'].get('error', 'Unknown')
                message += f"   Error: {error}\n"
            
            # Don't use code blocks for URLs
            message += f"   URL: {change['url']}\n\n"
        
        return message
