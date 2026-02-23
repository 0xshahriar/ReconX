"""
ReconX Termux Helpers
Utilities specific to Termux environment
"""

import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class TermuxHelper:
    """Helper functions for Termux environment"""
    
    PREFIX = Path("/data/data/com.termux/files/usr")
    HOME = Path("/data/data/com.termux/files/home")
    
    @classmethod
    def is_termux(cls) -> bool:
        """Check if running in Termux"""
        return "TERMUX_VERSION" in os.environ
    
    @classmethod
    def get_prefix_path(cls, path: str) -> str:
        """Convert path to Termux prefix path"""
        if path.startswith('/usr/'):
            return str(cls.PREFIX / path[5:])
        return path
    
    @classmethod
    async def acquire_wake_lock(cls):
        """Acquire wake lock to prevent sleep"""
        if not cls.is_termux():
            return
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "termux-wake-lock",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await proc.wait()
            logger.info("Wake lock acquired")
        except Exception as e:
            logger.error(f"Failed to acquire wake lock: {e}")
    
    @classmethod
    async def release_wake_lock(cls):
        """Release wake lock"""
        if not cls.is_termux():
            return
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "termux-wake-unlock",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await proc.wait()
            logger.info("Wake lock released")
        except Exception as e:
            logger.error(f"Failed to release wake lock: {e}")
    
    @classmethod
    async def show_notification(cls, title: str, content: str, 
                                 priority: str = "default"):
        """Show Android notification via Termux:API"""
        if not cls.is_termux():
            return
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "termux-notification",
                "--title", title,
                "--content", content,
                "--priority", priority,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await proc.wait()
        except Exception as e:
            logger.error(f"Failed to show notification: {e}")
    
    @classmethod
    def fix_dns_resolution(cls):
        """Fix DNS issues common in Termux"""
        # Create resolv.conf if missing
        resolv_conf = cls.PREFIX / "etc/resolv.conf"
        if not resolv_conf.exists():
            resolv_conf.parent.mkdir(parents=True, exist_ok=True)
            with open(resolv_conf, 'w') as f:
                f.write("nameserver 1.1.1.1\n")
                f.write("nameserver 8.8.8.8\n")
            logger.info("Created resolv.conf")
    
    @classmethod
    def setup_storage(cls):
        """Request storage permission"""
        if not cls.is_termux():
            return
        
        try:
            subprocess.run(["termux-setup-storage"], check=False)
        except Exception as e:
            logger.error(f"Failed to setup storage: {e}")
    
    @classmethod
    def get_battery_status(cls) -> dict:
        """Get battery status via Termux:API"""
        if not cls.is_termux():
            return {}
        
        try:
            result = subprocess.run(
                ["termux-battery-status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Failed to get battery status: {e}")
        
        return {}
    
    @classmethod
    def schedule_job(cls, script_path: str, interval_ms: int = 30000):
        """Schedule script via termux-job-scheduler"""
        if not cls.is_termux():
            return
        
        try:
            subprocess.run([
                "termux-job-scheduler",
                "--job-path", script_path,
                "--period-ms", str(interval_ms),
                "--persisted", "true"
            ], check=False)
            logger.info(f"Scheduled job: {script_path}")
        except Exception as e:
            logger.error(f"Failed to schedule job: {e}")

# Import asyncio at module level for wake lock functions
import asyncio
