"""
ReconX Cache Manager
Manage temporary scan data and tool outputs
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    """Manage cache directories and temporary files"""
    
    def __init__(self, base_dir: str = "data/cache"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Tool-specific cache dirs
        self.httpx_dir = self.base_dir / "httpx"
        self.nuclei_dir = self.base_dir / "nuclei"
        self.downloads_dir = self.base_dir / "downloads"
        self.temp_dir = self.base_dir / "temp"
        
        for d in [self.httpx_dir, self.nuclei_dir, self.downloads_dir, self.temp_dir]:
            d.mkdir(exist_ok=True)
    
    def get_httpx_cache(self, scan_id: str) -> Path:
        """Get cache directory for httpx results"""
        cache_dir = self.httpx_dir / scan_id
        cache_dir.mkdir(exist_ok=True)
        return cache_dir
    
    def get_nuclei_cache(self, scan_id: str) -> Path:
        """Get cache directory for nuclei results"""
        cache_dir = self.nuclei_dir / scan_id
        cache_dir.mkdir(exist_ok=True)
        return cache_dir
    
    def save_json_cache(self, name: str, data: Any, scan_id: Optional[str] = None) -> Path:
        """Save data as JSON cache"""
        if scan_id:
            cache_file = self.base_dir / scan_id / f"{name}.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
        else:
            cache_file = self.temp_dir / f"{name}_{datetime.now().timestamp()}.json"
        
        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        return cache_file
    
    def load_json_cache(self, name: str, scan_id: Optional[str] = None) -> Optional[Any]:
        """Load JSON cache"""
        if scan_id:
            cache_file = self.base_dir / scan_id / f"{name}.json"
        else:
            # Find most recent matching file
            pattern = f"{name}_*.json"
            files = sorted(self.temp_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            if not files:
                return None
            cache_file = files[0]
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load cache {cache_file}: {e}")
            return None
    
    def get_temp_file(self, prefix: str = "reconx", suffix: str = ".tmp") -> Path:
        """Get temporary file path"""
        import tempfile
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=self.temp_dir)
        os.close(fd)
        return Path(path)
    
    def cleanup_scan_cache(self, scan_id: str):
        """Remove cache for specific scan"""
        for subdir in [self.httpx_dir, self.nuclei_dir]:
            scan_cache = subdir / scan_id
            if scan_cache.exists():
                shutil.rmtree(scan_cache)
                logger.debug(f"Cleaned up cache: {scan_cache}")
    
    def cleanup_old_cache(self, max_age_days: int = 7):
        """Remove cache files older than specified days"""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        
        cleaned = 0
        for cache_dir in [self.httpx_dir, self.nuclei_dir, self.temp_dir]:
            for item in cache_dir.iterdir():
                try:
                    if item.is_file():
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        if mtime < cutoff:
                            item.unlink()
                            cleaned += 1
                    elif item.is_dir():
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        if mtime < cutoff:
                            shutil.rmtree(item)
                            cleaned += 1
                except Exception as e:
                    logger.debug(f"Failed to clean {item}: {e}")
        
        logger.info(f"Cleaned up {cleaned} old cache items")
        return cleaned
    
    def get_cache_size(self) -> Dict[str, Any]:
        """Get cache directory sizes"""
        def dir_size(path: Path) -> int:
            total = 0
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
            return total
        
        return {
            "httpx_bytes": dir_size(self.httpx_dir),
            "nuclei_bytes": dir_size(self.nuclei_dir),
            "downloads_bytes": dir_size(self.downloads_dir),
            "temp_bytes": dir_size(self.temp_dir),
            "total_bytes": dir_size(self.base_dir)
        }
    
    def clear_all_cache(self):
        """Clear all cache directories"""
        for subdir in [self.httpx_dir, self.nuclei_dir, self.temp_dir]:
            if subdir.exists():
                shutil.rmtree(subdir)
                subdir.mkdir()
        
        logger.info("All cache cleared")

import os
