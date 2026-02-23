"""
ReconX State Manager
Handles scan state serialization and resume capability
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from api.database import DatabaseManager

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, db: DatabaseManager, state_dir: str = "data/state"):
        self.db = db
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoint_interval = 30  # seconds
        self._last_checkpoint: Dict[str, datetime] = {}
    
    async def save_checkpoint(self, scan_id: str, state_data: Dict[str, Any]):
        """Save scan checkpoint to file and database"""
        timestamp = datetime.utcnow()
        
        checkpoint = {
            "scan_id": scan_id,
            "timestamp": timestamp.isoformat(),
            "timestamp_unix": timestamp.timestamp(),
            "current_module": state_data.get("current_module"),
            "current_target": state_data.get("current_target"),
            "completed_modules": state_data.get("completed_modules", []),
            "pending_modules": state_data.get("pending_modules", []),
            "module_state": state_data.get("module_state", {}),
            "queue_snapshot": state_data.get("queue_snapshot", []),
            "partial_results": state_data.get("partial_results", {}),
            "checksum": self._generate_checksum(state_data)
        }
        
        # Save to file
        state_file = self.state_dir / f"{scan_id}.json"
        try:
            with open(state_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            logger.debug(f"Checkpoint saved to {state_file}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint file: {e}")
        
        # Save to database
        try:
            await self.db.save_checkpoint(scan_id, checkpoint)
            self._last_checkpoint[scan_id] = timestamp
            logger.debug(f"Checkpoint saved to database for scan {scan_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint to database: {e}")
    
    async def load_checkpoint(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Load scan checkpoint from file or database"""
        # Try file first
        state_file = self.state_dir / f"{scan_id}.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    checkpoint = json.load(f)
                
                if self._verify_checksum(checkpoint):
                    logger.info(f"Checkpoint loaded from file for scan {scan_id}")
                    return checkpoint
                else:
                    logger.warning(f"Checksum mismatch for scan {scan_id}")
            except Exception as e:
                logger.error(f"Failed to load checkpoint from file: {e}")
        
        # Fallback to database
        try:
            scan = await self.db.get_scan(scan_id)
            if scan and scan.get('checkpoint_data'):
                checkpoint = json.loads(scan['checkpoint_data'])
                if self._verify_checksum(checkpoint):
                    logger.info(f"Checkpoint loaded from database for scan {scan_id}")
                    return checkpoint
        except Exception as e:
            logger.error(f"Failed to load checkpoint from database: {e}")
        
        return None
    
    async def should_checkpoint(self, scan_id: str) -> bool:
        """Check if enough time has passed to save new checkpoint"""
        if scan_id not in self._last_checkpoint:
            return True
        
        elapsed = (datetime.utcnow() - self._last_checkpoint[scan_id]).total_seconds()
        return elapsed >= self._checkpoint_interval
    
    async def clear_checkpoint(self, scan_id: str):
        """Clear checkpoint after successful completion"""
        state_file = self.state_dir / f"{scan_id}.json"
        if state_file.exists():
            state_file.unlink()
            logger.debug(f"Checkpoint file removed for scan {scan_id}")
        
        if scan_id in self._last_checkpoint:
            del self._last_checkpoint[scan_id]
    
    def _generate_checksum(self, data: Dict) -> str:
        """Generate simple checksum for data integrity"""
        import hashlib
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _verify_checksum(self, checkpoint: Dict) -> bool:
        """Verify checkpoint data integrity"""
        stored_checksum = checkpoint.get('checksum')
        if not stored_checksum:
            return False
        
        # Remove checksum from data before verifying
        data = {k: v for k, v in checkpoint.items() if k != 'checksum'}
        calculated = self._generate_checksum(data)
        return stored_checksum == calculated
    
    async def get_resume_state(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get state to resume scan from"""
        checkpoint = await self.load_checkpoint(scan_id)
        if not checkpoint:
            return None
        
        return {
            "current_module": checkpoint.get("current_module"),
            "completed_modules": checkpoint.get("completed_modules", []),
            "pending_modules": checkpoint.get("pending_modules", []),
            "module_state": checkpoint.get("module_state", {}),
            "can_resume": True
        }
