"""
ReconX State File Manager
Handle scan state JSON files for resume capability
"""

import json
import logging
import gzip
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class StateFileManager:
    """Manage scan state files"""
    
    def __init__(self, state_dir: str = "data/state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def get_state_path(self, scan_id: str) -> Path:
        """Get path to state file"""
        return self.state_dir / f"{scan_id}.json"
    
    def get_compressed_path(self, scan_id: str) -> Path:
        """Get path to compressed state file"""
        return self.state_dir / f"{scan_id}.json.gz"
    
    def save_state(self, scan_id: str, state: Dict[str, Any], compress: bool = False):
        """Save scan state to file"""
        state["saved_at"] = datetime.utcnow().isoformat()
        state["version"] = "1.0"
        
        if compress:
            path = self.get_compressed_path(scan_id)
            with gzip.open(path, 'wt', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
        else:
            path = self.get_state_path(scan_id)
            with open(path, 'w') as f:
                json.dump(state, f, indent=2, default=str)
        
        logger.debug(f"State saved: {path}")
        return path
    
    def load_state(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Load scan state from file"""
        # Try uncompressed first
        path = self.get_state_path(scan_id)
        if path.exists():
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state {path}: {e}")
        
        # Try compressed
        compressed_path = self.get_compressed_path(scan_id)
        if compressed_path.exists():
            try:
                with gzip.open(compressed_path, 'rt', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load compressed state {compressed_path}: {e}")
        
        return None
    
    def delete_state(self, scan_id: str):
        """Delete state file(s)"""
        path = self.get_state_path(scan_id)
        compressed = self.get_compressed_path(scan_id)
        
        deleted = False
        if path.exists():
            path.unlink()
            deleted = True
        if compressed.exists():
            compressed.unlink()
            deleted = True
        
        if deleted:
            logger.debug(f"Deleted state for {scan_id}")
        
        return deleted
    
    def list_states(self) -> List[Dict[str, Any]]:
        """List all saved states"""
        states = []
        
        for path in self.state_dir.glob("*.json*"):
            try:
                stat = path.stat()
                states.append({
                    "scan_id": path.stem.replace('.json', ''),
                    "path": str(path),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception as e:
                logger.debug(f"Failed to stat {path}: {e}")
        
        return sorted(states, key=lambda x: x["modified"], reverse=True)
    
    def cleanup_old_states(self, max_age_days: int = 30):
        """Remove state files older than specified days"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=max_age_days)
        cleaned = 0
        
        for path in self.state_dir.glob("*.json*"):
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime < cutoff:
                    path.unlink()
                    cleaned += 1
            except Exception as e:
                logger.debug(f"Failed to clean {path}: {e}")
        
        logger.info(f"Cleaned up {cleaned} old state files")
        return cleaned
    
    def get_total_state_size(self) -> int:
        """Get total size of all state files"""
        total = 0
        for path in self.state_dir.glob("*.json*"):
            try:
                total += path.stat().st_size
            except Exception:
                pass
        return total
