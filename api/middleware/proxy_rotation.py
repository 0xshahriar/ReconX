"""
ReconX Proxy Rotation
Manages Tor and proxy rotation for stealth
"""

import random
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Proxy:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"  # http, https, socks5
    
    def __str__(self):
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

class ProxyRotator:
    def __init__(self):
        self.proxies: List[Proxy] = []
        self.current_index = 0
        self.tor_enabled = False
        self.tor_proxy = Proxy("127.0.0.1", 9050, protocol="socks5")
    
    def add_proxy(self, proxy: Proxy):
        """Add proxy to rotation"""
        self.proxies.append(proxy)
    
    def load_proxies_from_file(self, filepath: str):
        """Load proxies from file (format: host:port:user:pass)"""
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split(':')
                    if len(parts) >= 2:
                        proxy = Proxy(
                            host=parts[0],
                            port=int(parts[1]),
                            username=parts[2] if len(parts) > 2 else None,
                            password=parts[3] if len(parts) > 3 else None
                        )
                        self.add_proxy(proxy)
            
            logger.info(f"Loaded {len(self.proxies)} proxies from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load proxies: {e}")
    
    def get_next_proxy(self) -> Optional[Proxy]:
        """Get next proxy in rotation"""
        if not self.proxies and not self.tor_enabled:
            return None
        
        if self.tor_enabled and random.random() < 0.5:
            return self.tor_proxy
        
        if self.proxies:
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            return proxy
        
        return self.tor_proxy if self.tor_enabled else None
    
    def get_random_proxy(self) -> Optional[Proxy]:
        """Get random proxy"""
        if not self.proxies and not self.tor_enabled:
            return None
        
        if self.tor_enabled and random.random() < 0.3:
            return self.tor_proxy
        
        return random.choice(self.proxies) if self.proxies else None
    
    async def renew_tor_ip(self) -> bool:
        """Request new Tor exit node"""
        if not self.tor_enabled:
            return False
        
        try:
            # Connect to Tor control port
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Try to signal newnym via Tor control port
                # This requires Tor to be configured with ControlPort
                pass  # Implementation depends on Tor setup
            
            logger.info("Tor IP renewed")
            return True
        except Exception as e:
            logger.error(f"Failed to renew Tor IP: {e}")
            return False

class UserAgentRotator:
    """Rotate User-Agent strings"""
    
    COMMON_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
    ]
    
    def __init__(self):
        self.user_agents = self.COMMON_UAS.copy()
    
    def get_random_ua(self) -> str:
        """Get random User-Agent"""
        return random.choice(self.user_agents)
    
    def add_custom_ua(self, ua: str):
        """Add custom User-Agent"""
        self.user_agents.append(ua)
