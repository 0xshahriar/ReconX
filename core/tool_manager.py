"""
ReconX Tool Manager
Auto-install and verify security tools
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)

class ToolManager:
    """Manage security tool installation and updates"""
    
    def __init__(self, config_path: str = "config/tools.json"):
        self.config_path = Path(config_path)
        self.tools_config = self._load_config()
        self.subprocess_mgr = SubprocessManager()
        self.installed_tools: Dict[str, bool] = {}
    
    def _load_config(self) -> Dict:
        """Load tools configuration"""
        if not self.config_path.exists():
            logger.error(f"Tools config not found: {self.config_path}")
            return {"tools": {}}
        
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def check_tool(self, tool_name: str) -> Tuple[bool, Optional[str]]:
        """Check if tool is installed and get version"""
        tool_config = self.tools_config.get("tools", {}).get(tool_name)
        if not tool_config:
            return False, None
        
        binary_path = self._resolve_path(tool_config.get("binary_path", tool_name))
        
        # Check if binary exists
        if not shutil.which(binary_path):
            return False, None
        
        # Check version if possible
        version_check = tool_config.get("version_check")
        if version_check:
            try:
                import subprocess
                result = subprocess.run(
                    version_check.split(),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                version = result.stdout.strip() or result.stderr.strip()
                return True, version
            except Exception as e:
                logger.debug(f"Version check failed for {tool_name}: {e}")
                return True, "unknown"
        
        return True, "unknown"
    
    async def install_tool(self, tool_name: str) -> bool:
        """Install a tool"""
        tool_config = self.tools_config.get("tools", {}).get(tool_name)
        if not tool_config:
            logger.error(f"Unknown tool: {tool_name}")
            return False
        
        install_cmd = tool_config.get("install_cmd")
        if not install_cmd:
            logger.warning(f"No install command for {tool_name}")
            return False
        
        logger.info(f"Installing {tool_name}...")
        
        try:
            result = await self.subprocess_mgr.run(
                install_cmd,
                timeout=300,
                stdout_callback=lambda x: logger.debug(f"[{tool_name}] {x}"),
                stderr_callback=lambda x: logger.warning(f"[{tool_name}] {x}")
            )
            
            success = result.returncode == 0
            if success:
                logger.info(f"Successfully installed {tool_name}")
                self.installed_tools[tool_name] = True
            else:
                logger.error(f"Failed to install {tool_name}: {result.stderr}")
            
            return success
            
        except Exception as e:
            logger.error(f"Installation error for {tool_name}: {e}")
            return False
    
    async def ensure_tool(self, tool_name: str) -> bool:
        """Ensure tool is installed, install if missing"""
        if tool_name in self.installed_tools:
            return self.installed_tools[tool_name]
        
        is_installed, version = self.check_tool(tool_name)
        
        if is_installed:
            logger.debug(f"{tool_name} is already installed: {version}")
            self.installed_tools[tool_name] = True
            return True
        
        logger.info(f"{tool_name} not found, attempting installation...")
        return await self.install_tool(tool_name)
    
    async def install_all(self, category: Optional[str] = None) -> Dict[str, bool]:
        """Install all tools or tools in category"""
        tools = self.tools_config.get("tools", {})
        results = {}
        
        for tool_name, tool_config in tools.items():
            if category and tool_config.get("category") != category:
                continue
            
            if not tool_config.get("enabled", True):
                logger.debug(f"Skipping disabled tool: {tool_name}")
                continue
            
            results[tool_name] = await self.install_tool(tool_name)
        
        return results
    
    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """Get resolved path to tool binary"""
        tool_config = self.tools_config.get("tools", {}).get(tool_name)
        if not tool_config:
            return shutil.which(tool_name)
        
        binary_path = tool_config.get("binary_path", tool_name)
        return self._resolve_path(binary_path)
    
    def _resolve_path(self, path: str) -> str:
        """Resolve path with ~ expansion"""
        return str(Path(path).expanduser())
    
    def list_tools(self) -> List[Dict]:
        """List all tools with status"""
        tools = []
        for name, config in self.tools_config.get("tools", {}).items():
            is_installed, version = self.check_tool(name)
            tools.append({
                "name": name,
                "category": config.get("category"),
                "description": config.get("description"),
                "installed": is_installed,
                "version": version,
                "enabled": config.get("enabled", True)
            })
        return tools
