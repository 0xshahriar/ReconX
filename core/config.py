# core/config.py
import os
import json
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Config File Path
CONFIG_FILE = BASE_DIR / "data" / "config.json"

class Config:
    def __init__(self):
        self.settings = self.load_config()

    def load_config(self):
        if not CONFIG_FILE.exists():
            # Create default config if not exists
            default_config = {
                "api_keys": {
                    "shodan": "",
                    "google_ai": "",
                    "virustotal": "",
                    "censys_id": "",
                    "censys_secret": ""
                },
                "notification": {
                    "discord_webhook": "",
                    "telegram_bot_token": "",
                    "telegram_chat_id": "",
                    "slack_webhook": ""
                },
                "scan_settings": {
                    "max_concurrency": 5,  # Light for Termux
                    "timeout": 10,
                    "rate_limit": 100,
                    "default_mode": "standard" # quick, standard, deep
                }
            }
            self.save_config(default_config)
            return default_config
        
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

    def save_config(self, config_data):
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, indent=4, fp=f)
        self.settings = config_data

    def get(self, key, default=None):
        # Helper to get nested keys easily
        keys = key.split(".")
        value = self.settings
        try:
            for k in keys:
                value = value[k]
            return value
        except KeyError:
            return default

# Global instance
config = Config()