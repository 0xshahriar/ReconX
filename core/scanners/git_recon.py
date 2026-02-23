"""
Git Reconnaissance Scanner
Detect and dump exposed .git directories
"""

import logging
import re
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

import aiohttp

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class GitRecon:
    """Git repository reconnaissance"""
    
    GIT_INDICATORS = [
        ".git/HEAD",
        ".git/config",
        ".git/index",
        ".git/logs/HEAD",
        ".git/refs/heads/master",
        ".git/refs/heads/main"
    ]
    
    def __init__(self, subprocess_mgr: SubprocessManager, db: DatabaseManager):
        self.subprocess_mgr = subprocess_mgr
        self.db = db
        self.tool_manager = ToolManager()
    
    async def scan(
        self,
        target_id: str,
        scan_id: str,
        config: Dict[str, Any],
        previous_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Scan for exposed Git repositories"""
        
        # Get live hosts
        http_data = previous_results.get("http_probe", {})
        live_hosts = http_data.get("results", [])
        
        if not live_hosts:
            logger.warning("No live hosts for Git recon")
            return {"checked": 0, "exposed": 0}
        
        exposed_repos = []
        
        async with aiohttp.ClientSession() as session:
            for host in live_hosts[:10]:  # Limit to first 10
                base_url = host.get("url", "")
                if not base_url:
                    continue
                
                # Check for exposed .git
                is_exposed = await self._check_git_exposure(session, base_url)
                
                if is_exposed:
                    logger.warning(f"Exposed .git found at {base_url}")
                    
                    exposed_repos.append({
                        "url": base_url,
                        "severity": "critical"
                    })
                    
                    # Try to dump if enabled
                    if config.get("dump_git", False):
                        await self._dump_git(base_url, scan_id)
                    
                    # Add vulnerability
                    await self.db.add_vulnerability(scan_id, {
                        "title": "Exposed Git Repository",
                        "severity": "critical",
                        "description": f"Git repository exposed at {base_url}/.git/",
                        "affected_url": f"{base_url}/.git/",
                        "tool_source": "git_recon"
                    })
                    
                    # Search for secrets in git
                    if config.get("scan_secrets", True):
                        await self._scan_git_secrets(base_url, scan_id)
        
        logger.info(f"Found {len(exposed_repos)} exposed Git repositories")
        
        return {
            "checked": len(live_hosts),
            "exposed": len(exposed_repos),
            "repositories": exposed_repos
        }
    
    async def _check_git_exposure(self, session: aiohttp.ClientSession, 
                                   base_url: str) -> bool:
        """Check if .git is exposed"""
        test_url = urljoin(base_url, ".git/HEAD")
        
        try:
            async with session.get(test_url, timeout=10) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    # Check if it's a valid git HEAD
                    if content.startswith("ref:") or "commit" in content:
                        return True
        except Exception:
            pass
        
        return False
    
    async def _dump_git(self, base_url: str, scan_id: str):
        """Dump exposed git repository"""
        await self.tool_manager.ensure_tool("git-dumper")
        
        import os
        from pathlib import Path
        
        dump_dir = Path(f"data/cache/git_dumps/{scan_id}")
        dump_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            cmd = f"git-dumper {base_url}/.git {dump_dir}"
            
            await self.subprocess_mgr.run_simple(cmd, timeout=300)
            
            logger.info(f"Git repository dumped to {dump_dir}")
            
            # Run gitleaks on dumped repo
            await self._scan_dumped_repo(dump_dir, base_url, scan_id)
            
        except Exception as e:
            logger.error(f"Git dump failed: {e}")
    
    async def _scan_dumped_repo(self, repo_path: Path, source_url: str, scan_id: str):
        """Scan dumped repo for secrets"""
        try:
            await self.tool_manager.ensure_tool("gitleaks")
            
            cmd = f"gitleaks detect -s {repo_path} -f json -r {repo_path}/gitleaks.json"
            
            await self.subprocess_mgr.run_simple(cmd, timeout=120)
            
            # Parse results if file exists
            results_file = repo_path / "gitleaks.json"
            if results_file.exists():
                import json
                with open(results_file) as f:
                    leaks = json.load(f)
                
                for leak in leaks:
                    await self.db.add_vulnerability(scan_id, {
                        "title": f"Git Secret: {leak.get('RuleID', 'Unknown')}",
                        "severity": "critical",
                        "description": f"Secret found in git history: {leak.get('Description', '')}",
                        "affected_url": source_url,
                        "evidence": leak.get('Match', ''),
                        "tool_source": "gitleaks"
                    })
        
        except Exception as e:
            logger.error(f"Gitleaks scan failed: {e}")
    
    async def _scan_git_secrets(self, base_url: str, scan_id: str):
        """Scan git repository for secrets using trufflehog"""
        try:
            await self.tool_manager.ensure_tool("trufflehog")
            
            cmd = f"trufflehog git {base_url}/.git --json"
            
            stdout = await self.subprocess_mgr.run_simple(cmd, timeout=300)
            
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    import json
                    finding = json.loads(line)
                    
                    await self.db.add_vulnerability(scan_id, {
                        "title": f"TruffleHog: {finding.get('DetectorName', 'Secret')}",
                        "severity": "critical",
                        "description": f"Secret detected in git repository",
                        "affected_url": base_url,
                        "evidence": finding.get('Redacted', ''),
                        "tool_source": "trufflehog"
                    })
                except json.JSONDecodeError:
                    pass
        
        except Exception as e:
            logger.error(f"TruffleHog scan failed: {e}")
