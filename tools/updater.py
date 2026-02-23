"""
ReconX Tool Updater (Python)
Programmatic tool updates
"""

import asyncio
import logging
from typing import Dict, List, Tuple

from tools.installer import ToolInstaller

logger = logging.getLogger(__name__)

class ToolUpdater:
    """Update installed tools"""
    
    def __init__(self):
        self.installer = ToolInstaller()
    
    async def update_all_go_tools(self) -> Dict[str, Tuple[bool, str]]:
        """Update all Go-based tools"""
        results = {}
        
        tools = self.installer.tools_config.get("tools", {})
        
        for name, tool in tools.items():
            if tool.get("source") == "go" and tool.get("enabled", True):
                logger.info(f"Updating {name}...")
                results[name] = await self.installer.update_tool(name)
        
        return results
    
    async def update_nuclei_templates(self) -> bool:
        """Update Nuclei templates"""
        try:
            from core.subprocess_manager import SubprocessManager
            
            mgr = SubprocessManager()
            result = await mgr.run_simple("nuclei -ut", timeout=300)
            
            logger.info("Nuclei templates updated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update nuclei templates: {e}")
            return False
    
    async def update_wordlists(self) -> bool:
        """Update wordlist repositories"""
        import subprocess
        
        wordlist_dir = Path("wordlists/SecLists")
        
        if not wordlist_dir.exists():
            logger.warning("SecLists not found, skipping update")
            return False
        
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=wordlist_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info("Wordlists updated")
                return True
            else:
                logger.error(f"Wordlist update failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Wordlist update error: {e}")
            return False
    
    async def update_ollama_models(self) -> Dict[str, bool]:
        """Update Ollama models"""
        results = {}
        
        try:
            # List models
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            models = []
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)
            
            # Update each model
            for model in models:
                logger.info(f"Updating model: {model}")
                try:
                    update_result = subprocess.run(
                        ["ollama", "pull", model],
                        capture_output=True,
                        text=True,
                        timeout=600
                    )
                    results[model] = update_result.returncode == 0
                except Exception as e:
                    results[model] = False
                    logger.error(f"Failed to update {model}: {e}")
        
        except Exception as e:
            logger.error(f"Ollama update failed: {e}")
        
        return results
    
    async def run_full_update(self) -> Dict[str, any]:
        """Run complete update process"""
        return {
            "go_tools": await self.update_all_go_tools(),
            "nuclei_templates": await self.update_nuclei_templates(),
            "wordlists": await self.update_wordlists(),
            "ollama_models": await self.update_ollama_models()
        }
