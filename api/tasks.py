"""
ReconX Task Queue Manager
Manages scan tasks using asyncio.Queue
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from api.database import DatabaseManager

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class ScanTask:
    scan_id: str
    target_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_module: Optional[str] = None
    progress: Dict[str, int] = field(default_factory=dict)
    error_message: Optional[str] = None

class TaskQueue:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, ScanTask] = {}
        self.paused_tasks: Dict[str, ScanTask] = {}
        self._processing = False
        self._current_task: Optional[ScanTask] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
    
    async def add_task(self, task: ScanTask):
        """Add task to queue"""
        await self.queue.put(task)
        self.active_tasks[task.scan_id] = task
        logger.info(f"Task {task.scan_id} added to queue")
        
        # Update database status
        await self.db.update_scan_status(task.scan_id, "pending")
    
    async def pause_task(self, scan_id: str):
        """Pause specific task"""
        if scan_id in self.active_tasks:
            task = self.active_tasks[scan_id]
            task.status = TaskStatus.PAUSED
            self.paused_tasks[scan_id] = task
            logger.info(f"Task {scan_id} paused")
            
            if self._current_task and self._current_task.scan_id == scan_id:
                self._pause_event.clear()
    
    async def resume_task(self, scan_id: str):
        """Resume specific task"""
        if scan_id in self.paused_tasks:
            task = self.paused_tasks.pop(scan_id)
            task.status = TaskStatus.RUNNING
            self.active_tasks[scan_id] = task
            self._pause_event.set()
            logger.info(f"Task {scan_id} resumed")
    
    async def stop_task(self, scan_id: str):
        """Stop/cancel specific task"""
        if scan_id in self.active_tasks:
            task = self.active_tasks[scan_id]
            task.status = TaskStatus.CANCELLED
            
            if self._current_task and self._current_task.scan_id == scan_id:
                # Cancel current execution
                self._current_task = None
            
            logger.info(f"Task {scan_id} stopped")
    
    async def process_loop(self):
        """Main processing loop"""
        self._processing = True
        logger.info("Task processor started")
        
        while self._processing:
            try:
                # Wait if paused
                await self._pause_event.wait()
                
                # Get task from queue with timeout
                try:
                    task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                self._current_task = task
                await self._execute_task(task)
                
            except Exception as e:
                logger.error(f"Error in process loop: {e}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, task: ScanTask):
        """Execute scan task"""
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            
            # Update database
            await self.db.update_scan_status(
                task.scan_id, 
                "running",
                current_task="Initializing"
            )
            
            logger.info(f"Starting scan {task.scan_id} for target {task.target_id}")
            
            # Import here to avoid circular imports
            from core.scanner_engine import ScannerEngine
            
            engine = ScannerEngine(self.db, task)
            await engine.run()
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            await self.db.update_scan_status(task.scan_id, "completed")
            logger.info(f"Scan {task.scan_id} completed")
            
        except Exception as e:
            logger.error(f"Scan {task.scan_id} failed: {e}")
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            await self.db.update_scan_status(
                task.scan_id, 
                "failed",
                error_message=str(e)
            )
        finally:
            self._current_task = None
            if task.scan_id in self.active_tasks:
                del self.active_tasks[task.scan_id]
    
    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        return {
            "queue_size": self.queue.qsize(),
            "active_tasks": len(self.active_tasks),
            "paused_tasks": len(self.paused_tasks),
            "current_task": {
                "scan_id": self._current_task.scan_id,
                "module": self._current_task.current_module,
                "progress": self._current_task.progress
            } if self._current_task else None
        }
    
    async def shutdown(self):
        """Graceful shutdown"""
        self._processing = False
        logger.info("Task processor shutting down")
