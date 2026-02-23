"""
ReconX Configuration Settings
Pydantic-based configuration management
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from pydantic import BaseSettings, Field, validator
from functools import lru_cache

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    url: str = "sqlite+aiosqlite:///data/recon.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    
    class Config:
        env_prefix = "DB_"

class LLMSettings(BaseSettings):
    """LLM/Ollama configuration"""
    ollama_url: str = "http://localhost:11434"
    default_model: str = "llama3.1:8b"
    fallback_model: str = "gemma3:4b"
    emergency_model: str = "gemma3:1b"
    auto_scale: bool = True
    unload_idle_minutes: int = 5
    temperature: float = 0.7
    max_tokens: int = 4096
    
    # Memory thresholds (MB)
    memory_thresholds: Dict[str, int] = {
        "llama3.1:8b": 6000,
        "gemma3:4b": 3500,
        "gemma3:1b": 1500
    }
    
    class Config:
        env_prefix = "LLM_"

class APISettings(BaseSettings):
    """API Server configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1
    websocket_ping_interval: int = 20
    cors_origins: List[str] = ["*"]
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    
    class Config:
        env_prefix = "API_"

class ScanSettings(BaseSettings):
    """Scanning configuration"""
    max_concurrent_scans: int = 2
    default_rate_limit: int = 50  # requests per second
    default_timeout: int = 30  # seconds
    max_retries: int = 3
    checkpoint_interval: int = 30  # seconds
    
    # Default scan profiles
    profiles: Dict[str, Dict[str, Any]] = {
        "stealthy": {
            "rate_limit": 10,
            "timeout": 60,
            "user_agent_rotation": True,
            "delay_between_requests": 2.0,
            "tools": {
                "subfinder": True,
                "amass": False,  # Too aggressive for stealth
                "naabu": True,
                "nuclei": True,
                "ffuf": False
            }
        },
        "normal": {
            "rate_limit": 50,
            "timeout": 30,
            "user_agent_rotation": True,
            "delay_between_requests": 0.5,
            "tools": {
                "subfinder": True,
                "amass": True,
                "naabu": True,
                "nuclei": True,
                "ffuf": True
            }
        },
        "aggressive": {
            "rate_limit": 200,
            "timeout": 10,
            "user_agent_rotation": False,
            "delay_between_requests": 0.1,
            "tools": {
                "subfinder": True,
                "amass": True,
                "naabu": True,
                "nuclei": True,
                "ffuf": True,
                "massdns": True
            }
        }
    }
    
    class Config:
        env_prefix = "SCAN_"

class ResilienceSettings(BaseSettings):
    """Power/network outage resilience settings"""
    check_interval: int = 10  # seconds
    pause_after_offline: int = 30  # seconds
    state_save_interval: int = 30  # seconds
    resume_delay: int = 10  # seconds after reconnect
    
    # Battery management
    pause_on_low_battery: bool = True
    low_battery_threshold: int = 15  # percent
    
    # Thermal management
    pause_on_overheat: bool = True
    max_temperature: float = 45.0  # celsius
    
    # Auto-resume
    auto_resume: bool = True
    max_resume_attempts: int = 3
    
    class Config:
        env_prefix = "RESILIENCE_"

class TunnelSettings(BaseSettings):
    """Remote tunnel configuration"""
    primary: str = "cloudflare"  # cloudflare | ngrok | localtunnel
    auto_start: bool = True
    auto_restart: bool = True
    notify_on_start: bool = True
    notify_on_reconnect: bool = True
    
    # Security
    require_auth: bool = True
    allowed_ips: List[str] = []
    auto_shutdown: int = 7200  # seconds (2 hours)
    
    # Cloudflare specific
    cloudflare_custom_domain: Optional[str] = None
    cloudflare_tunnel_name: str = "reconx"
    
    # Ngrok specific
    ngrok_auth_token: Optional[str] = None
    ngrok_subdomain: Optional[str] = None
    
    # Retry logic
    max_retry_attempts: int = 5
    retry_delay_seconds: int = 60
    
    class Config:
        env_prefix = "TUNNEL_"

class NotificationSettings(BaseSettings):
    """Notification channel settings"""
    enabled_channels: List[str] = ["discord", "telegram"]
    
    # Discord
    discord_webhook: Optional[str] = None
    discord_username: str = "ReconX"
    discord_avatar: Optional[str] = None
    
    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # Slack
    slack_webhook: Optional[str] = None
    slack_channel: Optional[str] = None
    
    # Triggers
    notify_on_scan_complete: bool = True
    notify_on_critical_finding: bool = True
    notify_on_power_restored: bool = True
    notify_on_tunnel_start: bool = True
    notify_on_error: bool = True
    
    class Config:
        env_prefix = "NOTIFY_"

class WordlistSettings(BaseSettings):
    """Wordlist configuration"""
    auto_update: bool = True
    update_interval_days: int = 7
    sources: Dict[str, str] = {
        "seclists": "https://github.com/danielmiessler/SecLists.git",
        "payloads_all_things": "https://github.com/swisskyrepo/PayloadsAllTheThings.git"
    }
    
    # Default wordlist selections
    defaults: Dict[str, str] = {
        "subdomains": "subdomains-medium.txt",
        "directories": "directories.txt",
        "files": "files.txt",
        "parameters": "parameters.txt"
    }
    
    class Config:
        env_prefix = "WORDLIST_"

class Settings(BaseSettings):
    """Main ReconX settings"""
    
    # App info
    app_name: str = "ReconX"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"  # development | production
    
    # Paths
    base_dir: Path = Path.home() / "ReconX"
    data_dir: Path = Field(default_factory=lambda: Path.home() / "ReconX" / "data")
    logs_dir: Path = Field(default_factory=lambda: Path.home() / "ReconX" / "logs")
    reports_dir: Path = Field(default_factory=lambda: Path.home() / "ReconX" / "reports")
    wordlists_dir: Path = Field(default_factory=lambda: Path.home() / "ReconX" / "wordlists")
    
    # Sub-configs
    database: DatabaseSettings = DatabaseSettings()
    llm: LLMSettings = LLMSettings()
    api: APISettings = APISettings()
    scan: ScanSettings = ScanSettings()
    resilience: ResilienceSettings = ResilienceSettings()
    tunnel: TunnelSettings = TunnelSettings()
    notification: NotificationSettings = NotificationSettings()
    wordlist: WordlistSettings = WordlistSettings()
    
    # API Keys (load from env or file)
    shodan_api_key: Optional[str] = None
    github_token: Optional[str] = None
    gitlab_token: Optional[str] = None
    censys_api_id: Optional[str] = None
    censys_api_secret: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @validator('base_dir', 'data_dir', 'logs_dir', 'reports_dir', 'wordlists_dir')
    def create_directories(cls, v):
        """Ensure directories exist"""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    def save_to_file(self, filepath: str = "config/settings.json"):
        """Save current settings to JSON file"""
        config_path = Path(filepath)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict, handling Path objects
        data = self.dict()
        self._convert_paths_to_strings(data)
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _convert_paths_to_strings(self, obj):
        """Recursively convert Path objects to strings"""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, Path):
                    obj[k] = str(v)
                elif isinstance(v, (dict, list)):
                    self._convert_paths_to_strings(v)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, Path):
                    obj[i] = str(item)
                elif isinstance(item, (dict, list)):
                    self._convert_paths_to_strings(item)
    
    @classmethod
    def load_from_file(cls, filepath: str = "config/settings.json"):
        """Load settings from JSON file"""
        config_path = Path(filepath)
        if not config_path.exists():
            return cls()
        
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        return cls(**data)

# Global settings instance
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Convenience function
settings = get_settings()
