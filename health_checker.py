import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from config import Config

logger = logging.getLogger(__name__)


class HealthChecker:
    def __init__(self):
        self.last_status: Dict[str, bool] = {}
        monitors = Config.load_monitor_entries()
        self.endpoints_to_check = self._build_endpoints(monitors)

        if not self.endpoints_to_check:
            logger.warning(
                "No monitor endpoints configured - health checks are disabled."
            )

    def _build_endpoints(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        endpoints: List[Dict[str, Any]] = []
        for entry in entries:
            url = entry.get('url')
            if not url:
                continue

            env_name = entry.get('env') or self._extract_env_name(url)
            env_display = env_name or url
            surface_label = self._format_surface_label(entry.get('surface'))
            expected_status = entry.get('expected_status', 200)
            try:
                expected_status = int(expected_status)
            except (TypeError, ValueError):
                expected_status = 200

            endpoints.append(
                {
                    'name': entry.get('name') or env_display,
                    'url': url,
                    'env': env_display,
                    'surface': surface_label,
                    'method': (entry.get('method') or 'GET').upper(),
                    'expected_status': expected_status,
                }
            )
        return endpoints

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

    @staticmethod
    def _format_surface_label(surface: Optional[str]) -> str:
        """Normalize friendly labels for surfaces."""
        if not surface:
            return 'Custom'

        normalized = surface.replace('_', '-').lower()
        if normalized in ('frontdoor', 'front-door'):
            return 'Front Door'
        if normalized in ('vm', 'virtual-machine', 'virtual_machine'):
            return 'VM'
        return surface.title()

    def check_endpoint(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Check if an endpoint is healthy"""
        url = endpoint['url']
        name = endpoint['name']
        surface = endpoint.get('surface')
        method = endpoint.get('method', 'GET').upper()
        expected_status = endpoint.get('expected_status', 200)
        display_name = self._compose_display_name(name, surface)

        try:
            response = requests.request(
                method,
                url,
                timeout=Config.HEALTH_CHECK_TIMEOUT,
                allow_redirects=True
            )

            if response.status_code == expected_status:
                return {
                    'name': name,
                    'display_name': display_name,
                    'url': url,
                    'surface': surface,
                    'status': 'UP',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'name': name,
                    'display_name': display_name,
                    'url': url,
                    'surface': surface,
                    'status': 'DOWN',
                    'status_code': response.status_code,
                    'error': f"HTTP {response.status_code}",
                    'timestamp': datetime.now().isoformat()
                }

        except requests.exceptions.Timeout:
            return {
                'name': name,
                'display_name': display_name,
                'url': url,
                'surface': surface,
                'status': 'DOWN',
                'error': 'Timeout',
                'timestamp': datetime.now().isoformat()
            }
        except requests.exceptions.ConnectionError:
            return {
                'name': name,
                'display_name': display_name,
                'url': url,
                'surface': surface,
                'status': 'DOWN',
                'error': 'Connection Error',
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error checking {url}: {str(e)}")
            return {
                'name': name,
                'display_name': display_name,
                'url': url,
                'surface': surface,
                'status': 'DOWN',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def check_all(self) -> List[Dict[str, Any]]:
        results = []
        for endpoint in self.endpoints_to_check:
            result = self.check_endpoint(endpoint)
            results.append(result)
        return results

    def get_status_changes(self, current_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect status changes from previous check"""
        changes = []

        for result in current_results:
            url = result['url']
            current_status = result['status'] == 'UP'
            previous_status = self.last_status.get(url)

            if previous_status is not None and previous_status != current_status:
                display_name = result.get('display_name') or self._compose_display_name(
                    result.get('name'), result.get('surface')
                )
                changes.append({
                    'name': display_name,
                    'display_name': display_name,
                    'surface': result.get('surface'),
                    'url': url,
                    'previous': 'UP' if previous_status else 'DOWN',
                    'current': 'UP' if current_status else 'DOWN',
                    'result': result
                })

            self.last_status[url] = current_status

        return changes

    def format_health_report(self, results: List[Dict[str, Any]], include_all: bool = False) -> str:
        """Format health check results as a message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')

        up_count = sum(1 for r in results if r['status'] == 'UP')
        down_count = len(results) - up_count

        message = "🏥 **Health Check Report**\n"
        message += f"⏰ {timestamp}\n"
        message += f"{'─' * 40}\n\n"

        if up_count == len(results):
            message += f"✅ All services are UP ({up_count}/{len(results)})\n\n"
        else:
            message += f"⚠️ {down_count} service(s) DOWN, {up_count} UP\n\n"

        if include_all or down_count > 0:
            for result in results:
                status_emoji = "✅" if result['status'] == 'UP' else "❌"
                display_name = result.get('display_name') or self._compose_display_name(
                    result.get('name'), result.get('surface')
                )
                message += f"{status_emoji} **{display_name}**\n"

                if result['status'] == 'UP':
                    response_time = result.get('response_time', 0)
                    message += f"   Status: {result['status']} ({response_time:.2f}s)\n"
                else:
                    error = result.get('error', 'Unknown error')
                    message += f"   Status: {result['status']}\n"
                    message += f"   Error: {error}\n"

                message += f"   URL: {result['url']}\n\n"

        return message

    def format_status_change_alert(self, changes: List[Dict[str, Any]]) -> Optional[str]:
        """Format status change alerts"""
        if not changes:
            return None

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        message = "🚨 **Service Status Alert**\n"
        message += f"⏰ {timestamp}\n"
        message += f"{'─' * 40}\n\n"

        for change in changes:
            display_name = change.get('display_name') or change['name']
            if change['current'] == 'UP':
                emoji = "✅"
                message += f"{emoji} **{display_name}** is now UP\n"
                message += f"   Previous: {change['previous']} → Current: {change['current']}\n"
            else:
                emoji = "❌"
                message += f"{emoji} **{display_name}** is now DOWN\n"
                message += f"   Previous: {change['previous']} → Current: {change['current']}\n"
                error = change['result'].get('error', 'Unknown')
                message += f"   Error: {error}\n"

            message += f"   URL: {change['url']}\n\n"

        return message

    @staticmethod
    def _compose_display_name(name: Optional[str], surface: Optional[str]) -> str:
        base = name or 'Unknown'
        if surface:
            return f"{base} ({surface})"
        return base
