import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MONITOR_CONFIG = BASE_DIR / "monitor_urls.yaml"
RAW_MONITOR_CONFIG_PATH = os.getenv("MONITOR_CONFIG_PATH")


class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Bot Server Configuration
    WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", 5000))
    WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")

    # Health Check Configuration
    HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", 300))
    HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", 10))

    # Monitoring Configuration
    MONITOR_CONFIG_PATH_DEFINED = bool(RAW_MONITOR_CONFIG_PATH)
    MONITOR_CONFIG_PATH = Path(
        RAW_MONITOR_CONFIG_PATH or str(DEFAULT_MONITOR_CONFIG)
    ).expanduser()
    MONITOR_URLS = [
        url.strip()
        for url in os.getenv("MONITOR_URLS", "").split(",")
        if url.strip()
    ]

    @classmethod
    def load_monitor_entries(cls) -> List[Dict[str, Any]]:
        """Load monitor entries from YAML, falling back to MONITOR_URLS."""
        entries: List[Dict[str, Any]] = []
        yaml_path = cls.MONITOR_CONFIG_PATH

        if yaml_path.is_file():
            try:
                with yaml_path.open("r", encoding="utf-8") as fh:
                    payload = yaml.safe_load(fh) or {}
            except (OSError, yaml.YAMLError) as exc:
                raise ValueError(
                    f"Failed to read monitor config from {yaml_path}: {exc}"
                ) from exc

            for idx, raw_entry in enumerate(payload.get("monitors", []), start=1):
                url = (raw_entry.get("url") or "").strip()
                if not url:
                    continue
                entries.append(
                    {
                        "name": raw_entry.get("name") or f"Monitor-{idx}",
                        "env": (raw_entry.get("env") or "").strip(),
                        "surface": (raw_entry.get("surface") or "").strip(),
                        "method": (raw_entry.get("method") or "GET").upper(),
                        "expected_status": cls._coerce_expected_status(
                            raw_entry.get("expected_status")
                        ),
                        "url": url,
                        "description": (raw_entry.get("description") or "").strip(),
                    }
                )
        else:
            if cls.MONITOR_CONFIG_PATH_DEFINED:
                raise ValueError(
                    f"MONITOR_CONFIG_PATH points to {yaml_path} but the file does not exist"
                )

        if not entries and cls.MONITOR_URLS:
            for idx, url in enumerate(cls.MONITOR_URLS, start=1):
                entries.append(
                    {
                        "name": f"Monitor-{idx}",
                        "env": "",
                        "surface": "custom",
                        "method": "GET",
                        "expected_status": 200,
                        "url": url,
                        "description": "",
                    }
                )

        return entries

    @staticmethod
    def _coerce_expected_status(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 200

    @classmethod
    def validate(cls):
        """Validate required configuration."""
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not cls.TELEGRAM_CHAT_ID:
            raise ValueError("TELEGRAM_CHAT_ID is required")

        # Ensure monitor configuration is readable
        cls.load_monitor_entries()
        return True
