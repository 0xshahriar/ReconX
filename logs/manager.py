"""
ReconX Log Manager
Log file management, rotation, and cleanup
"""

import gzip
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class LogManager:
    """Manage log files"""
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.scans_dir = self.logs_dir / "scans"
        self.errors_dir = self.logs_dir / "errors"
    
    def list_logs(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all log files"""
        logs = {
            "main": [],
            "scans": [],
            "errors": []
        }
        
        # Main logs
        for log_file in sorted(self.logs_dir.glob("*.log*")):
            stat = log_file.stat()
            logs["main"].append({
                "path": str(log_file),
                "name": log_file.name,
                "size_kb": round(stat.st_size / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        # Scan logs
        for log_file in sorted(self.scans_dir.glob("*.log*")):
            stat = log_file.stat()
            logs["scans"].append({
                "path": str(log_file),
                "name": log_file.name,
                "scan_id": log_file.stem,
                "size_kb": round(stat.st_size / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        # Error logs
        for log_file in sorted(self.errors_dir.glob("*.log*")):
            stat = log_file.stat()
            logs["errors"].append({
                "path": str(log_file),
                "name": log_file.name,
                "size_kb": round(stat.st_size / 1024, 2),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return logs
    
    def get_scan_log(self, scan_id: str, lines: int = 100) -> List[str]:
        """Get recent lines from scan log"""
        log_file = self.scans_dir / f"{scan_id}.log"
        
        if not log_file.exists():
            return []
        
        try:
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            logger.error(f"Failed to read scan log: {e}")
            return []
    
    def compress_old_logs(self, max_age_days: int = 7):
        """Compress log files older than specified days"""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        compressed = 0
        
        for log_dir in [self.logs_dir, self.scans_dir, self.errors_dir]:
            for log_file in log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff.timestamp():
                    # Compress
                    gz_path = log_file.with_suffix('.log.gz')
                    try:
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(gz_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        log_file.unlink()
                        compressed += 1
                        logger.debug(f"Compressed {log_file}")
                    except Exception as e:
                        logger.error(f"Failed to compress {log_file}: {e}")
        
        if compressed:
            logger.info(f"Compressed {compressed} old log files")
        
        return compressed
    
    def cleanup_old_logs(self, max_age_days: int = 30, keep_compressed: bool = True):
        """Remove old log files"""
        cutoff = datetime.now() - timedelta(days=max_age_days)
        removed = 0
        
        for log_dir in [self.logs_dir, self.scans_dir, self.errors_dir]:
            for log_file in log_dir.glob("*.log*"):
                # Skip compressed files if keep_compressed
                if keep_compressed and log_file.suffix == '.gz':
                    continue
                
                if log_file.stat().st_mtime < cutoff.timestamp():
                    try:
                        log_file.unlink()
                        removed += 1
                    except Exception as e:
                        logger.error(f"Failed to remove {log_file}: {e}")
        
        if removed:
            logger.info(f"Removed {removed} old log files")
        
        return removed
    
    def get_total_size(self) -> Dict[str, float]:
        """Get total size of logs in MB"""
        def dir_size(path: Path) -> float:
            total = 0
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
            return round(total / (1024 * 1024), 2)
        
        return {
            "main_mb": dir_size(self.logs_dir),
            "scans_mb": dir_size(self.scans_dir),
            "errors_mb": dir_size(self.errors_dir)
        }
    
    def tail_log(self, log_name: str, lines: int = 50) -> List[str]:
        """Tail a specific log file"""
        if log_name == "api":
            log_file = self.logs_dir / "api.log"
        elif log_name == "error":
            log_file = self.errors_dir / "error.log"
        else:
            log_file = self.logs_dir / log_name
        
        if not log_file.exists():
            return []
        
        try:
            with open(log_file, 'r') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
        except Exception as e:
            logger.error(f"Failed to tail {log_file}: {e}")
            return []
    
    def archive_scan_logs(self, scan_ids: Optional[List[str]] = None) -> Path:
        """Archive scan logs to tar.gz"""
        import tarfile
        import tempfile
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"scan_logs_{timestamp}.tar.gz"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = Path(tmpdir) / archive_name
            
            with tarfile.open(archive_path, "w:gz") as tar:
                if scan_ids:
                    # Archive specific scans
                    for scan_id in scan_ids:
                        log_file = self.scans_dir / f"{scan_id}.log"
                        if log_file.exists():
                            tar.add(log_file, arcname=log_file.name)
                else:
                    # Archive all scan logs
                    for log_file in self.scans_dir.glob("*.log"):
                        tar.add(log_file, arcname=log_file.name)
            
            # Move to logs directory
            final_path = self.logs_dir / "archives"
            final_path.mkdir(exist_ok=True)
            final_path = final_path / archive_name
            
            shutil.move(archive_path, final_path)
            
            logger.info(f"Archived scan logs to {final_path}")
            return final_path
    
    def clear_all_logs(self, confirm: bool = False):
        """Clear all log files (use with caution)"""
        if not confirm:
            logger.warning("Set confirm=True to clear all logs")
            return False
        
        cleared = 0
        for log_dir in [self.logs_dir, self.scans_dir, self.errors_dir]:
            for log_file in log_dir.glob("*.log*"):
                try:
                    log_file.unlink()
                    cleared += 1
                except Exception as e:
                    logger.error(f"Failed to clear {log_file}: {e}")
        
        logger.info(f"Cleared {cleared} log files")
        return cleared
