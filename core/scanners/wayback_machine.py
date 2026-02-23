"""
Wayback Machine Scanner
Historical URL discovery and analysis
"""

import logging
from typing import Dict, List, Any, Optional, Set

import aiohttp

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class WaybackMachine:
    """Wayback Machine URL discovery"""
    
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
        """Discover historical URLs"""
        
        target = await self.db.get_target(target_id)
        if not target:
            raise ValueError(f"Target {target_id} not found")
        
        domain = target["primary_domain"]
        
        urls = set()
        
        # Use gau
        if config.get("use_gau", True):
            gau_urls = await self._run_gau(domain)
            urls.update(gau_urls)
        
        # Use waybackurls
        if config.get("use_waybackurls", True):
            wb_urls = await self._run_waybackurls(domain)
            urls.update(wb_urls)
        
        # Direct Wayback API
        if config.get("use_wayback_api", True):
            api_urls = await self._query_wayback_api(domain)
            urls.update(api_urls)
        
        # Process URLs
        processed = self._process_urls(urls)
        
        # Extract parameters for fuzzing
        parameters = self._extract_parameters(urls)
        
        # Save to database
        for url in list(urls)[:1000]:  # Limit to 1000
            await self.db._connection.execute("""
                INSERT INTO endpoints (id, scan_id, url, method, discovered_via)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(__import__('uuid').uuid4()),
                scan_id,
                url,
                "GET",
                "wayback"
            ))
        await self.db._connection.commit()
        
        logger.info(f"Wayback: {len(urls)} URLs, {len(parameters)} unique parameters")
        
        return {
            "urls_discovered": len(urls),
            "unique_parameters": len(parameters),
            "urls": list(urls)[:100],
            "parameters": list(parameters)
        }
    
    async def _run_gau(self, domain: str) -> Set[str]:
        """Run GetAllUrls (gau)"""
        await self.tool_manager.ensure_tool("gau")
        
        cmd = f"gau {domain} --subs --threads 5"
        
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=300)
        
        urls = set()
        for line in stdout.strip().split('\n'):
            url = line.strip()
            if url and url.startswith('http'):
                urls.add(url)
        
        return urls
    
    async def _run_waybackurls(self, domain: str) -> Set[str]:
        """Run waybackurls"""
        await self.tool_manager.ensure_tool("waybackurls")
        
        cmd = f"echo {domain} | waybackurls"
        
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=300)
        
        urls = set()
        for line in stdout.strip().split('\n'):
            url = line.strip()
            if url and url.startswith('http'):
                urls.add(url)
        
        return urls
    
    async def _query_wayback_api(self, domain: str) -> Set[str]:
        """Query Wayback Machine API directly"""
        url = f"http://web.archive.org/cdx/search/cdx?url=*.{domain}/*&output=json&fl=original&collapse=urlkey"
        
        urls = set()
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=120) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Skip header row
                        for entry in data[1:]:
                            if entry:
                                urls.add(entry[0])
            except Exception as e:
                logger.error(f"Wayback API query failed: {e}")
        
        return urls
    
    def _process_urls(self, urls: Set[str]) -> Dict[str, List[str]]:
        """Categorize URLs by type"""
        categories = {
            "js": [],
            "api": [],
            "doc": [],
            "other": []
        }
        
        for url in urls:
            lower = url.lower()
            if lower.endswith('.js'):
                categories["js"].append(url)
            elif '/api/' in lower or '/v1/' in lower or '/v2/' in lower:
                categories["api"].append(url)
            elif any(lower.endswith(ext) for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
                categories["doc"].append(url)
            else:
                categories["other"].append(url)
        
        return categories
    
    def _extract_parameters(self, urls: Set[str]) -> Set[str]:
        """Extract unique parameter names from URLs"""
        from urllib.parse import urlparse, parse_qs
        
        parameters = set()
        
        for url in urls:
            try:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                parameters.update(params.keys())
            except Exception:
                pass
        
        return parameters

import uuid
