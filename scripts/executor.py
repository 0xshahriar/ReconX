"""
ReconX Script Executor
Execute shell scripts from Python with proper error handling
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class ScriptExecutor:
    """Execute ReconX shell scripts"""
    
    def __init__(self, scripts_dir: str = "scripts"):
        self.scripts_dir = Path(scripts_dir)
    
    async def run_script(self, script_name: str, *args, 
                         timeout: int = 300) -> Dict[str, Any]:
        """Execute a shell script"""
        script_path = self.scripts_dir / script_name
        
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        # Make executable if needed
        if not script_path.stat().st_mode & 0o111:
            script_path.chmod(0o755)
        
        cmd = [str(script_path)] + list(args)
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout
            )
            
            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace')
            }
            
        except asyncio.TimeoutError:
            proc.kill()
            return {
                "success": False,
                "error": f"Script timed out after {timeout}s"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def backup(self) -> Dict[str, Any]:
        """Run backup script"""
        return await self.run_script("backup.sh", timeout=600)
    
    async def restore(self) -> Dict[str, Any]:
        """Run restore script"""
        return await self.run_script("restore.sh", timeout=600)
    
    async def cleanup(self, **options) -> Dict[str, Any]:
        """Run cleanup script with options"""
        args = []
        
        if options.get("all"):
            args.append("--all")
        if options.get("logs"):
            args.append("--logs")
        if options.get("cache"):
            args.append("--cache")
        if options.get("days"):
            args.extend(["--days", str(options["days"])])
        
        return await self.run_script("cleanup.sh", *args, timeout=300)
    
    async def health_check(self) -> Dict[str, Any]:
        """Run health check"""
        return await self.run_script("health_check.sh", timeout=60)
    
    async def setup_tunnel(self) -> Dict[str, Any]:
        """Run tunnel setup"""
        return await self.run_script("tunnel_setup.sh", timeout=300)
    
    async def start_tunnel(self) -> Dict[str, Any]:
        """Start tunnel"""
        return await self.run_script("start_tunnel.sh", timeout=60)
    
    def list_scripts(self) -> List[Dict[str, str]]:
        """List available scripts"""
        scripts = []
        
        for script in self.scripts_dir.glob("*.sh"):
            scripts.append({
                "name": script.name,
                "path": str(script),
                "description": self._get_description(script)
            })
        
        return scripts
    
    def _get_description(self, script_path: Path) -> str:
        """Extract description from script comments"""
        try:
            with open(script_path) as f:
                for line in f:
                    if line.startswith('#') and not line.startswith('#!/'):
                        return line.lstrip('# ').strip()
        except Exception:
            pass
        
        return "No description"
