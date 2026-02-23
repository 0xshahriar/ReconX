"""
Continuous Monitor
Scheduled re-scanning and change detection
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

from api.database import DatabaseManager
from api.tasks import TaskQueue, ScanTask
from api.notifications import NotificationManager

logger = logging.getLogger(__name__)

@dataclass
class MonitorConfig:
    target_id: str
    interval_hours: int = 24
    enabled_modules: List[str] = None
    alert_on_changes: bool = True
    compare_with_last: bool = True

class ContinuousMonitor:
    """Continuous monitoring for targets"""
    
    def __init__(self, db: DatabaseManager, task_queue: TaskQueue):
        self.db = db
        self.task_queue = task_queue
        self.notification_mgr = NotificationManager()
        self.monitors: Dict[str, MonitorConfig] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self):
        """Start continuous monitoring"""
        self._running = True
        logger.info("Continuous monitor started")
        
        # Load existing monitors from database
        await self._load_monitors()
        
        # Start monitoring loop
        self._tasks.append(asyncio.create_task(self._monitoring_loop()))
    
    async def stop(self):
        """Stop continuous monitoring"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        logger.info("Continuous monitor stopped")
    
    async def add_monitor(self, config: MonitorConfig):
        """Add target to continuous monitoring"""
        self.monitors[config.target_id] = config
        
        # Save to database
        await self.db._connection.execute("""
            INSERT OR REPLACE INTO continuous_monitors 
            (target_id, interval_hours, enabled_modules, alert_on_changes, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            config.target_id,
            config.interval_hours,
            json.dumps(config.enabled_modules or []),
            config.alert_on_changes,
            datetime.utcnow().isoformat()
        ))
        await self.db._connection.commit()
        
        logger.info(f"Added monitor for target {config.target_id}")
    
    async def remove_monitor(self, target_id: str):
        """Remove target from monitoring"""
        if target_id in self.monitors:
            del self.monitors[target_id]
            
            await self.db._connection.execute("""
                DELETE FROM continuous_monitors WHERE target_id = ?
            """, (target_id,))
            await self.db._connection.commit()
            
            logger.info(f"Removed monitor for target {target_id}")
    
    async def _load_monitors(self):
        """Load monitors from database"""
        try:
            async with self.db._connection.execute(
                "SELECT * FROM continuous_monitors"
            ) as cursor:
                rows = await cursor.fetchall()
                
                for row in rows:
                    config = MonitorConfig(
                        target_id=row["target_id"],
                        interval_hours=row["interval_hours"],
                        enabled_modules=json.loads(row["enabled_modules"]) if row["enabled_modules"] else None,
                        alert_on_changes=row["alert_on_changes"]
                    )
                    self.monitors[row["target_id"]] = config
        
        except Exception as e:
            logger.error(f"Failed to load monitors: {e}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                now = datetime.utcnow()
                
                for target_id, config in self.monitors.items():
                    # Check if it's time to scan
                    last_scan = await self._get_last_scan_time(target_id)
                    
                    if last_scan:
                        next_scan = last_scan + timedelta(hours=config.interval_hours)
                        if now < next_scan:
                            continue
                    
                    # Trigger scan
                    await self._trigger_scan(target_id, config)
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _get_last_scan_time(self, target_id: str) -> Optional[datetime]:
        """Get last scan time for target"""
        async with self.db._connection.execute("""
            SELECT MAX(created_at) as last_scan 
            FROM scans WHERE target_id = ?
        """, (target_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row["last_scan"]:
                return datetime.fromisoformat(row["last_scan"])
        return None
    
    async def _trigger_scan(self, target_id: str, config: MonitorConfig):
        """Trigger a new scan"""
        logger.info(f"Triggering scheduled scan for {target_id}")
        
        # Create scan task
        task = ScanTask(
            scan_id=str(__import__('uuid').uuid4()),
            target_id=target_id,
            config={
                "modules": config.enabled_modules or ["subdomain_enum", "http_probe"],
                "monitor_scan": True,
                "compare_with_last": config.compare_with_last
            }
        )
        
        await self.task_queue.add_task(task)
        
        # Notify
        if config.alert_on_changes:
            await self.notification_mgr.send_notification(
                title="🔍 Scheduled Scan Started",
                message=f"Continuous monitoring scan started for target {target_id}",
                severity="info"
            )
    
    async def compare_scans(self, old_scan_id: str, new_scan_id: str) -> Dict:
        """Compare two scans and identify changes"""
        # Get results from both scans
        old_subs = await self.db.get_subdomains(old_scan_id)
        new_subs = await self.db.get_subdomains(new_scan_id)
        
        old_set = {s["subdomain"] for s in old_subs}
        new_set = {s["subdomain"] for s in new_subs}
        
        changes = {
            "new_subdomains": list(new_set - old_set),
            "removed_subdomains": list(old_set - new_set),
            "total_old": len(old_set),
            "total_new": len(new_set)
        }
        
        # Alert on new subdomains
        if changes["new_subdomains"]:
            await self.notification_mgr.send_notification(
                title="🆕 New Subdomains Discovered",
                message=f"Found {len(changes['new_subdomains'])} new subdomains",
                severity="medium",
                fields={
                    "Scan ID": new_scan_id,
                    "New": ", ".join(changes["new_subdomains"][:5])
                }
            )
        
        return changes

import uuid
