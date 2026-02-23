"""
Shodan Integration Scanner
Shodan API for host information
"""

import logging
from typing import Dict, List, Any, Optional

import aiohttp

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)

class ShodanIntegration:
    """Shodan API integration"""
    
    def __init__(self, subprocess_mgr: SubprocessManager, db: DatabaseManager):
        self.subprocess_mgr = subprocess_mgr
        self.db = db
        self.api_key = None
        self._load_api_key()
    
    def _load_api_key(self):
        """Load Shodan API key from config"""
        try:
            import json
            with open('config/settings.json') as f:
                config = json.load(f)
                self.api_key = config.get('shodan_api_key')
        except Exception:
            pass
    
    async def scan(
        self,
        target_id: str,
        scan_id: str,
        config: Dict[str, Any],
        previous_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Query Shodan for host information"""
        
        if not self.api_key:
            logger.warning("No Shodan API key configured")
            return {"error": "No API key"}
        
        # Get IPs from previous results
        dns_data = previous_results.get("dns_resolution", {})
        resolutions = dns_data.get("resolutions", {})
        
        all_results = []
        
        async with aiohttp.ClientSession() as session:
            for subdomain, ips in list(resolutions.items())[:5]:  # Limit to 5 hosts
                for ip in ips[:2]:  # Limit to 2 IPs per host
                    result = await self._query_host(session, ip)
                    if result:
                        all_results.append(result)
                        
                        # Add vulnerabilities from Shodan
                        for vuln in result.get("vulns", []):
                            await self.db.add_vulnerability(scan_id, {
                                "title": f"Shodan: {vuln}",
                                "severity": "high",
                                "description": f"Vulnerability detected by Shodan for {ip}",
                                "affected_url": f"http://{ip}",
                                "tool_source": "shodan"
                            })
        
        return {
            "hosts_queried": len(all_results),
            "results": all_results
        }
    
    async def _query_host(self, session: aiohttp.ClientSession, ip: str) -> Optional[Dict]:
        """Query Shodan for specific IP"""
        url = f"https://api.shodan.io/shodan/host/{ip}?key={self.api_key}"
        
        try:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 404:
                    logger.debug(f"No Shodan data for {ip}")
                else:
                    logger.warning(f"Shodan API error: {resp.status}")
        except Exception as e:
            logger.error(f"Shodan query failed for {ip}: {e}")
        
        return None
