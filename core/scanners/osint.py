"""
OSINT Gatherer
Email harvesting, employee enumeration, social media discovery
"""

import logging
from typing import Dict, List, Any, Optional

import aiohttp

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class OSINTGatherer:
    """Open Source Intelligence gathering"""
    
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
        """Gather OSINT data"""
        
        target = await self.db.get_target(target_id)
        if not target:
            raise ValueError(f"Target {target_id} not found")
        
        domain = target["primary_domain"]
        
        results = {
            "emails": [],
            "employees": [],
            "social_media": [],
            "breach_data": []
        }
        
        # Email harvesting
        if config.get("harvest_emails", True):
            results["emails"] = await self._harvest_emails(domain)
        
        # theHarvester
        if config.get("use_theharvester", False):
            harvester_results = await self._run_theharvester(domain)
            results["emails"].extend(harvester_results.get("emails", []))
            results["employees"].extend(harvester_results.get("employees", []))
        
        # Social media
        if config.get("social_media", True):
            results["social_media"] = await self._check_social_media(domain)
        
        # Breach checking
        if config.get("check_breaches", True):
            results["breach_data"] = await self._check_breaches(results["emails"])
        
        logger.info(f"OSINT: {len(results['emails'])} emails, "
                   f"{len(results['employees'])} employees, "
                   f"{len(results['social_media'])} social profiles")
        
        return results
    
    async def _harvest_emails(self, domain: str) -> List[str]:
        """Harvest emails from various sources"""
        emails = set()
        
        # Common patterns
        patterns = ["info", "admin", "support", "contact", "sales", "hello", "security"]
        for pattern in patterns:
            emails.add(f"{pattern}@{domain}")
        
        # Try to find emails from web pages
        # This would require crawling which is resource intensive
        # Skipping for mobile optimization
        
        return list(emails)
    
    async def _run_theharvester(self, domain: str) -> Dict[str, List[str]]:
        """Run theHarvester tool"""
        await self.tool_manager.ensure_tool("theHarvester")
        
        try:
            cmd = f"theHarvester -d {domain} -b all -f /tmp/theharvester_{domain}"
            
            await self.subprocess_mgr.run_simple(cmd, timeout=600)
            
            # Parse results
            import xml.etree.ElementTree as ET
            
            xml_file = f"/tmp/theharvester_{domain}.xml"
            results = {"emails": [], "employees": []}
            
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
                
                for email in root.findall(".//email"):
                    results["emails"].append(email.text)
                
                for host in root.findall(".//host"):
                    # Extract potential employee names
                    hostname = host.text
                    if "@" in hostname:
                        results["employees"].append(hostname.split("@")[0])
            
            except Exception as e:
                logger.error(f"Failed to parse theHarvester output: {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"theHarvester failed: {e}")
            return {"emails": [], "employees": []}
    
    async def _check_social_media(self, domain: str) -> List[Dict]:
        """Check for social media presence"""
        name = domain.replace(".", "")
        
        profiles = []
        
        # Check common platforms
        checks = [
            ("twitter", f"https://twitter.com/{name}"),
            ("github", f"https://github.com/{name}"),
            ("linkedin", f"https://linkedin.com/company/{name}"),
        ]
        
        async with aiohttp.ClientSession() as session:
            for platform, url in checks:
                try:
                    async with session.get(url, timeout=10, allow_redirects=True) as resp:
                        if resp.status == 200:
                            # Check if it's not a "not found" page
                            text = await resp.text()
                            if "not found" not in text.lower() and "page doesn't exist" not in text.lower():
                                profiles.append({
                                    "platform": platform,
                                    "url": str(resp.url),
                                    "exists": True
                                })
                except Exception:
                    pass
        
        return profiles
    
    async def _check_breaches(self, emails: List[str]) -> List[Dict]:
        """Check emails against breach databases"""
        breaches = []
        
        # Use HaveIBeenPwned API (requires key)
        # Limited implementation without API key
        
        for email in emails[:5]:  # Limit to first 5
            # Placeholder - real implementation needs API key
            pass
        
        return breaches
