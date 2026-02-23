"""
ReconX Subprocess Manager
Async subprocess wrapper with timeout and streaming
"""

import asyncio
import logging
import shlex
from dataclasses import dataclass
from typing import Optional, Callable, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str
    duration: float
    command: str

class SubprocessManager:
    """Manage async subprocess execution"""
    
    def __init__(self):
        self.active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self._paused = False
        self._stopped = False
    
    async def run(
        self,
        command: str,
        timeout: int = 300,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        stdout_callback: Optional[Callable[[str], None]] = None,
        stderr_callback: Optional[Callable[[str], None]] = None,
        task_id: Optional[str] = None
    ) -> ProcessResult:
        """Run command with timeout and streaming output"""
        
        start_time = datetime.utcnow()
        
        # Split command safely
        if isinstance(command, str):
            cmd_parts = shlex.split(command)
        else:
            cmd_parts = command
        
        logger.debug(f"Executing: {' '.join(cmd_parts)}")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env
            )
            
            if task_id:
                self.active_processes[task_id] = proc
            
            # Read output with timeout
            stdout_lines = []
            stderr_lines = []
            
            async def read_stream(stream, callback, lines_list):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode('utf-8', errors='replace').rstrip()
                    lines_list.append(decoded)
                    if callback:
                        callback(decoded)
                    
                    # Check for pause/stop
                    if self._stopped:
                        proc.terminate()
                        break
                    while self._paused and not self._stopped:
                        await asyncio.sleep(0.1)
            
            # Wait for completion with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(proc.stdout, stdout_callback, stdout_lines),
                        read_stream(proc.stderr, stderr_callback, stderr_lines)
                    ),
                    timeout=timeout
                )
                
                returncode = await proc.wait()
                
            except asyncio.TimeoutError:
                logger.warning(f"Command timed out after {timeout}s: {command}")
                proc.kill()
                returncode = -1
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return ProcessResult(
                returncode=returncode,
                stdout='\n'.join(stdout_lines),
                stderr='\n'.join(stderr_lines),
                duration=duration,
                command=command
            )
            
        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            raise
        finally:
            if task_id and task_id in self.active_processes:
                del self.active_processes[task_id]
    
    async def run_simple(self, command: str, timeout: int = 60) -> str:
        """Simple execution returning stdout only"""
        result = await self.run(command, timeout=timeout)
        if result.returncode != 0:
            logger.warning(f"Command failed with code {result.returncode}: {result.stderr}")
        return result.stdout
    
    def pause_all(self):
        """Pause all active processes"""
        self._paused = True
    
    def resume_all(self):
        """Resume all paused processes"""
        self._paused = False
    
    def stop_all(self):
        """Stop all active processes"""
        self._stopped = True
        for task_id, proc in self.active_processes.items():
            try:
                proc.terminate()
                logger.info(f"Terminated process {task_id}")
            except Exception as e:
                logger.error(f"Failed to terminate {task_id}: {e}")
