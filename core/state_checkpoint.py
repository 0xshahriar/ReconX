"""
ReconX State Checkpoint
Serialize/deserialize scan state for resume capability
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from api.database import DatabaseManager

logger = logging.getLogger(__name__)

class StateCheckpoint:
    """Manage scan state checkpoints"""
    
    def __init__(self, db: DatabaseManager, scan_id: str, state_dir: str = "data/state"):
        self.db = db
        self.scan_id = scan_id
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / f"{scan_id}.json"
    
    async def save_state(
        self,
        current_module: str,
        completed_modules: list,
        pending_modules: list,
        results_cache: Dict[str, Any],
        module_state: Optional[Dict] = None
    ):
        """Save current scan state"""
        checkpoint = {
            "scan_id": self.scan_id,
            "timestamp": datetime.utcnow().isoformat(),
            "current_module": current_module,
            "completed_modules": completed_modules,
            "pending_modules": pending_modules,
            "module_state": module_state or {},
            "results_cache": self._serialize_results(results_cache),
            "checksum": self._generate_checksum(results_cache)
        }
        
        # Save to file
        try:
            with open(self.state_file, 'w') as f:
                json.dump(checkpoint, f, indent=2, default=str)
            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")
        
        # Save to database
        try:
            await self.db.save_checkpoint(self.scan_id, checkpoint)
        except Exception as e:
            logger.error(f"Failed to save checkpoint to DB: {e}")
    
    async def load_state(self) -> Optional[Dict[str, Any]]:
        """Load scan state from file or database"""
        # Try file first
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                if self._verify_checksum(state):
                    logger.info(f"Loaded state from file for scan {self.scan_id}")
                    return self._deserialize_results(state)
                else:
                    logger.warning("State file checksum mismatch")
            except Exception as e:
                logger.error(f"Failed to load state file: {e}")
        
        # Fallback to database
        try:
            scan = await self.db.get_scan(self.scan_id)
            if scan and scan.get('checkpoint_data'):
                state = json.loads(scan['checkpoint_data'])
                if self._verify_checksum(state):
                    logger.info(f"Loaded state from database for scan {self.scan_id}")
                    return self._deserialize_results(state)
        except Exception as e:
            logger.error(f"Failed to load state from DB: {e}")
        
        return None
    
    async def clear_state(self):
        """Clear checkpoint after successful completion"""
        if self.state_file.exists():
            try:
                self.state_file.unlink()
                logger.debug(f"State file removed: {self.state_file}")
            except Exception as e:
                logger.error(f"Failed to remove state file: {e}")
    
    def _serialize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Serialize results for storage"""
        # Convert non-serializable objects
        serialized = {}
        for key, value in results.items():
            if isinstance(value, (list, dict, str, int, float, bool, type(None))):
                serialized[key] = value
            else:
                serialized[key] = str(value)
        return serialized
    
    def _deserialize_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize results from storage"""
        return {
            "can_resume": True,
            "current_module": state.get("current_module"),
            "completed_modules": state.get("completed_modules", []),
            "pending_modules": state.get("pending_modules", []),
            "module_state": state.get("module_state", {}),
            "results_cache": state.get("results_cache", {})
        }
    
    def _generate_checksum(self, data: Dict[str, Any]) -> str:
        """Generate simple checksum for data integrity"""
        import hashlib
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _verify_checksum(self, state: Dict[str, Any]) -> bool:
        """Verify state integrity"""
        stored_checksum = state.get("checksum")
        if not stored_checksum:
            return False
        
        # Recalculate without checksum field
        data = {k: v for k, v in state.items() if k != "checksum"}
        calculated = self._generate_checksum(data)
        return stored_checksum == calculated
