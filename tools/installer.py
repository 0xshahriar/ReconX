"""
ReconX Tool Installer (Python)
Programmatic tool installation
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)

class ToolInstaller:
    """Install and manage security tools"""
    
    def __init__(self, config_path: str = "config/tools.json"):
        self.config_path = Path(config_path)
        self.subprocess_mgr = SubprocessManager()
        self.tools_config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load tools configuration"""
        if not self.config_path.exists():
            return {"tools": {}}
        
        with open(self.config_path) as f:
            return json.load(f)
    
    async def install_tool(self, tool_name: str) -> Tuple[bool, str]:
        """Install a specific tool"""
        tool = self.tools_config.get("tools", {}).get(tool_name)
        
        if not tool:
            return False, f"Tool {tool_name} not found in config"
        
        if not tool.get("enabled", True):
            return False, f"Tool {tool_name} is disabled"
        
        install_cmd = tool.get("install_cmd")
        if not install_cmd:
            return False, f"No install command for {tool_name}"
        
        logger.info(f"Installing {tool_name}...")
        
        try:
            result = await self.subprocess_mgr.run(
                install_cmd,
                timeout=300,
                stdout_callback=lambda x: logger.debug(f"[{tool_name}] {x}"),
                stderr_callback=lambda x: logger.warning(f"[{tool_name}] {x}")
            )
            
            if result.returncode == 0:
                return True, f"Successfully installed {tool_name}"
            else:
                return False, f"Installation failed: {result.stderr}"
                
        except Exception as e:
            return False, f"Installation error: {str(e)}"
    
    async def install_category(self, category: str) -> Dict[str, Tuple[bool, str]]:
        """Install all tools in a category"""
        results = {}
        
        for name, tool in self.tools_config.get("tools", {}).items():
            if tool.get("category") == category and tool.get("enabled", True):
                results[name] = await self.install_tool(name)
        
        return results
    
    async def install_all(self) -> Dict[str, Tuple[bool, str]]:
        """Install all enabled tools"""
        results = {}
        
        for name in self.tools_config.get("tools", {}):
            results[name] = await self.install_tool(name)
        
        return results
    
    def check_installed(self, tool_name: str) -> Tuple[bool, Optional[str]]:
        """Check if tool is installed and get version"""
        tool = self.tools_config.get("tools", {}).get(tool_name)
        
        if not tool:
            return False, None
        
        binary = tool.get("binary_path", tool_name)
        binary = Path(binary).expanduser()
        
        # Check in PATH
        if not binary.exists():
            # Try which
            try:
                result = subprocess.run(
                    ["which", tool_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode != 0:
                    return False, None
                binary = Path(result.stdout.strip())
            except Exception:
                return False, None
        
        # Get version
        version_check = tool.get("version_check")
        if version_check:
            try:
                result = subprocess.run(
                    version_check.split(),
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                version = (result.stdout + result.stderr).strip().split('\n')[0]
                return True, version
            except Exception:
                return True, "unknown"
        
        return True, "unknown"
    
    async def update_tool(self, tool_name: str) -> Tuple[bool, str]:
        """Update a tool to latest version"""
        # Most Go tools update via reinstall
        return await self.install_tool(tool_name)
    
    def get_install_status(self) -> List[Dict]:
        """Get installation status of all tools"""
        status = []
        
        for name, tool in self.tools_config.get("tools", {}).items():
            installed, version = self.check_installed(name)
            status.append({
                "name": name,
                "category": tool.get("category"),
                "installed": installed,
                "version": version,
                "enabled": tool.get("enabled", True)
            })
        
        return status
