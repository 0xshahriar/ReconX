"""
ReconX Backup Manager
Database backup, restore, and integrity checks
"""

import json
import logging
import shutil
import sqlite3
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class BackupManager:
    """Manage database backups and restores"""
    
    def __init__(self, db_path: str = "data/recon.db", backup_dir: str = "data/backups"):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, include_files: bool = True) -> Optional[Path]:
        """Create full backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"reconx_backup_{timestamp}"
        
        try:
            # Create temp directory for backup contents
            import tempfile
            temp_dir = Path(tempfile.mkdtemp())
            
            # Backup database
            db_backup = temp_dir / "recon.db"
            self._backup_database_file(self.db_path, db_backup)
            
            # Create manifest
            manifest = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "database": "recon.db",
                "files_included": include_files
            }
            
            with open(temp_dir / "manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Include additional files if requested
            if include_files:
                files_dir = temp_dir / "files"
                files_dir.mkdir()
                
                # Copy wordlists
                wordlists_src = Path("wordlists")
                if wordlists_src.exists():
                    shutil.copytree(wordlists_src, files_dir / "wordlists", ignore=lambda x, y: ['.git'])
                
                # Copy reports
                reports_src = Path("reports")
                if reports_src.exists():
                    shutil.copytree(reports_src, files_dir / "reports")
            
            # Create tar archive
            backup_path = self.backup_dir / f"{backup_name}.tar.gz"
            
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(temp_dir, arcname=".")
            
            # Cleanup temp
            shutil.rmtree(temp_dir)
            
            logger.info(f"Backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None
    
    def _backup_database_file(self, src: Path, dst: Path):
        """Create consistent database backup"""
        # Use SQLite backup API for consistency
        src_conn = sqlite3.connect(str(src))
        dst_conn = sqlite3.connect(str(dst))
        
        with dst_conn:
            src_conn.backup(dst_conn)
        
        src_conn.close()
        dst_conn.close()
    
    def restore_backup(self, backup_path: Path, restore_dir: Optional[Path] = None) -> bool:
        """Restore from backup"""
        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_path}")
            return False
        
        restore_dir = restore_dir or Path("restores") / datetime.now().strftime("%Y%m%d_%H%M%S")
        restore_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Extract archive
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(restore_dir)
            
            # Read manifest
            manifest_path = restore_dir / "manifest.json"
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            # Restore database
            db_backup = restore_dir / "recon.db"
            if db_backup.exists():
                # Close any existing connections
                import time
                time.sleep(1)  # Give time for connections to close
                
                # Backup current DB first
                if self.db_path.exists():
                    safety_backup = self.db_path.with_suffix('.db.bak')
                    shutil.copy2(self.db_path, safety_backup)
                
                # Restore
                shutil.copy2(db_backup, self.db_path)
                logger.info(f"Database restored from backup")
            
            # Restore files if included
            if manifest.get("files_included"):
                files_dir = restore_dir / "files"
                if files_dir.exists():
                    for item in files_dir.iterdir():
                        dst = Path(item.name)
                        if dst.exists():
                            shutil.rmtree(dst) if dst.is_dir() else dst.unlink()
                        shutil.copytree(item, dst) if item.is_dir() else shutil.copy2(item, dst)
            
            logger.info(f"Restore completed to {restore_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = []
        
        for path in sorted(self.backup_dir.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True):
            stat = path.stat()
            backups.append({
                "path": str(path),
                "name": path.name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return backups
    
    def cleanup_old_backups(self, keep_count: int = 10):
        """Keep only N most recent backups"""
        backups = sorted(self.backup_dir.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        removed = 0
        for old_backup in backups[keep_count:]:
            old_backup.unlink()
            removed += 1
        
        if removed:
            logger.info(f"Removed {removed} old backups")
        
        return removed
    
    def verify_database_integrity(self) -> bool:
        """Check database integrity"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            conn.close()
            
            if result[0] == "ok":
                logger.info("Database integrity check passed")
                return True
            else:
                logger.error(f"Database integrity check failed: {result[0]}")
                return False
                
        except Exception as e:
            logger.error(f"Integrity check error: {e}")
            return False
