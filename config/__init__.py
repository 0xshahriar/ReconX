"""
ReconX Configuration Package
"""

from config.settings import Settings, get_settings, settings
from pathlib import Path
import json
import yaml

__all__ = [
    "Settings",
    "get_settings",
    "settings",
    "load_tools_config",
    "load_wordlists_config",
    "load_tunnel_config",
    "ensure_configs_exist"
]

def load_tools_config() -> dict:
    """Load tools configuration from JSON"""
    config_path = Path(__file__).parent / "tools.json"
    if not config_path.exists():
        return {}
    
    with open(config_path, 'r') as f:
        return json.load(f)

def load_wordlists_config() -> dict:
    """Load wordlists configuration from JSON"""
    config_path = Path(__file__).parent / "wordlists.json"
    if not config_path.exists():
        return {}
    
    with open(config_path, 'r') as f:
        return json.load(f)

def load_tunnel_config() -> dict:
    """Load tunnel configuration from YAML"""
    config_path = Path(__file__).parent / "tunnel.yaml"
    if not config_path.exists():
        return {}
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def ensure_configs_exist():
    """Ensure all config files exist, create defaults if missing"""
    config_dir = Path(__file__).parent
    
    files_to_check = [
        "settings.py",
        "tools.json",
        "wordlists.json",
        "tunnel.yaml"
    ]
    
    missing = []
    for filename in files_to_check:
        if not (config_dir / filename).exists():
            missing.append(filename)
    
    if missing:
        raise FileNotFoundError(
            f"Missing config files: {', '.join(missing)}. "
            f"Please ensure all configuration files exist in {config_dir}"
        )
    
    return True

# Config singletons
_tools_config = None
_wordlists_config = None
_tunnel_config = None

def get_tools_config() -> dict:
    """Get cached tools config"""
    global _tools_config
    if _tools_config is None:
        _tools_config = load_tools_config()
    return _tools_config

def get_wordlists_config() -> dict:
    """Get cached wordlists config"""
    global _wordlists_config
    if _wordlists_config is None:
        _wordlists_config = load_wordlists_config()
    return _wordlists_config

def get_tunnel_config() -> dict:
    """Get cached tunnel config"""
    global _tunnel_config
    if _tunnel_config is None:
        _tunnel_config = load_tunnel_config()
    return _tunnel_config
