"""
ReconX Resilience Manager
Handles power outages, network disconnections, and auto-resume
"""

import asyncio
import logging
import subprocess
from datetime import datetime
from typing import Optional

from api.database import DatabaseManager
from api.tasks import TaskQueue

logger = logging.getLogger(__name__)

class ResilienceManager:
    def __init__(self, db: DatabaseManager, task_queue: TaskQueue,
                 check_interval: int = 10):
        self.db = db
        self.task_queue = task_queue
        self.check_interval = check_interval
        self.is_running = False
        self._offline_since: Optional[datetime] = None
        self._was_paused_by_outage = False
        self._pause_threshold = 30  # seconds before pausing
        self._resume_delay = 10  # seconds after reconnect before resuming
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        self.is_running = True
        logger.info("Resilience manager started")
        
        while self.is_running:
            try:
                is_online = await self._check_internet()
                await self._handle_network_state(is_online)
                
                # Update system state in database
                await self.db.update_system_state({
                    "network_status": "online" if is_online else "offline",
                    "last_seen": datetime.utcnow().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in resilience monitor: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def _check_internet(self) -> bool:
        """Check internet connectivity"""
        # Try multiple DNS servers
        hosts = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
        
        for host in hosts:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "ping", "-c", "1", "-W", "5", host,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                await asyncio.wait_for(proc.wait(), timeout=6.0)
                if proc.returncode == 0:
                    return True
            except Exception:
                continue
        
        return False
    
    async def _handle_network_state(self, is_online: bool):
        """Handle network state changes"""
        if not is_online:
            if not self._offline_since:
                self._offline_since = datetime.utcnow()
                logger.warning("Network connection lost")
            
            # Check if we should pause
            offline_duration = (datetime.utcnow() - self._offline_since).total_seconds()
            if offline_duration >= self._pause_threshold and not self._was_paused_by_outage:
                await self._auto_pause()
        else:
            if self._offline_since:
                offline_duration = (datetime.utcnow() - self._offline_since).total_seconds()
                logger.info(f"Network restored after {offline_duration:.0f}s")
                self._offline_since = None
                
                if self._was_paused_by_outage:
                    await asyncio.sleep(self._resume_delay)
                    await self._auto_resume()
    
    async def _auto_pause(self):
        """Automatically pause scans due to network outage"""
        logger.warning("Auto-pausing scans due to network outage")
        self._was_paused_by_outage = True
        
        # Pause all active tasks
        for scan_id in list(self.task_queue.active_tasks.keys()):
            await self.task_queue.pause_task(scan_id)
            await self.db.update_scan_status(scan_id, "paused")
        
        # Save system state
        await self.db.update_system_state({
            "network_status": "offline",
            "pause_reason": "network_outage"
        })
    
    async def _auto_resume(self):
        """Automatically resume scans after network restoration"""
        logger.info("Auto-resuming scans after network restoration")
        self._was_paused_by_outage = False
        
        # Resume all paused tasks
        for scan_id in list(self.task_queue.paused_tasks.keys()):
            await self.task_queue.resume_task(scan_id)
            await self.db.update_scan_status(scan_id, "running")
        
        # Update system state
        await self.db.update_system_state({
            "network_status": "online"
        })
    
    async def trigger_pause(self, reason: str = "manual"):
        """Manual pause trigger"""
        logger.info(f"Manual pause triggered: {reason}")
        for scan_id in list(self.task_queue.active_tasks.keys()):
            await self.task_queue.pause_task(scan_id)
    
    async def trigger_resume(self):
        """Manual resume trigger"""
        logger.info("Manual resume triggered")
        for scan_id in list(self.task_queue.paused_tasks.keys()):
            await self.task_queue.resume_task(scan_id)
    
    async def check_battery(self) -> Optional[int]:
        """Check battery level (Termux specific)"""
        try:
            # Try Termux API
            result = subprocess.run(
                ["termux-battery-status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                return data.get("percentage")
        except Exception:
            pass
        return None
    
    async def check_temperature(self) -> Optional[float]:
        """Check device temperature"""
        try:
            # Try to read thermal zone
            for i in range(10):
                path = f"/sys/class/thermal/thermal_zone{i}/temp"
                if Path(path).exists():
                    with open(path, 'r') as f:
                        temp = int(f.read().strip())
                        if temp > 1000:  # Millidegrees
                            temp = temp / 1000
                        return float(temp)
        except Exception:
            pass
        return None
    
    def stop(self):
        """Stop monitoring"""
        self.is_running = False
