"""
ReconX Wordlist Manager
Download and manage wordlists from various sources
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp

logger = logging.getLogger(__name__)

class WordlistManager:
    """Manage wordlist downloads and updates"""
    
    def __init__(self, config_path: str = "config/wordlists.json"):
        self.config_path = Path(config_path)
        self.wordlists_dir = Path("wordlists")
        self.wordlists_dir.mkdir(parents=True, exist_ok=True)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load wordlists configuration"""
        if not self.config_path.exists():
            return {"wordlists": {}, "fuzzing_payloads": {}}
        
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    async def download_wordlist(self, name: str, force: bool = False) -> Optional[Path]:
        """Download a specific wordlist"""
        wordlist_config = self.config.get("wordlists", {}).get(name)
        if not wordlist_config:
            logger.error(f"Unknown wordlist: {name}")
            return None
        
        local_path = self.wordlists_dir / wordlist_config["name"]
        
        # Check if already exists
        if local_path.exists() and not force:
            logger.debug(f"Wordlist {name} already exists at {local_path}")
            return local_path
        
        # Download
        url = wordlist_config.get("url")
        if not url:
            logger.error(f"No URL for wordlist {name}")
            return None
        
        logger.info(f"Downloading {name} from {url}...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to download {name}: HTTP {resp.status}")
                        return None
                    
                    content = await resp.text()
                    
                    # Save to file
                    local_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(local_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Verify checksum if provided
                    expected_checksum = wordlist_config.get("checksum")
                    if expected_checksum:
                        actual_checksum = self._calculate_checksum(local_path)
                        if actual_checksum != expected_checksum:
                            logger.warning(f"Checksum mismatch for {name}")
                    
                    logger.info(f"Downloaded {name} ({len(content)} bytes)")
                    return local_path
                    
        except Exception as e:
            logger.error(f"Failed to download {name}: {e}")
            return None
    
    async def download_fuzzing_payloads(self, category: str) -> Optional[Path]:
        """Download fuzzing payloads for specific category"""
        payload_config = self.config.get("fuzzing_payloads", {}).get(category)
        if not payload_config:
            logger.error(f"Unknown payload category: {category}")
            return None
        
        local_path = self.wordlists_dir / "fuzzing" / payload_config["name"]
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        if local_path.exists():
            return local_path
        
        url = payload_config.get("url")
        if not url:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=300) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        with open(local_path, 'w') as f:
                            f.write(content)
                        return local_path
        except Exception as e:
            logger.error(f"Failed to download {category} payloads: {e}")
        
        return None
    
    def get_wordlist_path(self, name: str) -> Optional[Path]:
        """Get local path to wordlist"""
        wordlist_config = self.config.get("wordlists", {}).get(name)
        if not wordlist_config:
            return None
        
        local_path = self.wordlists_dir / wordlist_config["name"]
        if local_path.exists():
            return local_path
        
        return None
    
    def list_available(self) -> List[Dict]:
        """List all available wordlists with download status"""
        wordlists = []
        for name, config in self.config.get("wordlists", {}).items():
            local_path = self.wordlists_dir / config["name"]
            wordlists.append({
                "name": name,
                "description": config.get("description"),
                "downloaded": local_path.exists(),
                "size_estimate": config.get("size_estimate"),
                "line_count": config.get("line_count")
            })
        return wordlists
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    async def update_all(self):
        """Update all wordlists"""
        for name in self.config.get("wordlists", {}).keys():
            await self.download_wordlist(name, force=True)
