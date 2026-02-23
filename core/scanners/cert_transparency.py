"""
Certificate Transparency Scanner
Query CT logs for subdomain discovery
"""

import logging
from typing import Dict, List, Any, Optional

import aiohttp

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)

class CertTransparency:
    """Certificate transparency log queries"""
    
    CT_SOURCES = {
        "crtsh": "https://crt.sh/?q=%.{domain}&output=json",
        "certspotter": "https://api.certspotter.com/v1/issuances?domain={domain}&include_subdomains=true&expand=dns_names",
        "facebook": "https://graph.facebook.com/certificates?query={domain}&fields=certificate_pem&access_token="  # Requires token
    }
    
    def __init__(self, subprocess_mgr: SubprocessManager, db: DatabaseManager):
        self.subprocess_mgr = subprocess_mgr
        self.db = db
    
    async def scan(
        self,
        target_id: str,
        scan_id: str,
        config: Dict[str, Any],
        previous_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Query certificate transparency logs"""
        
        target = await self.db.get_target(target_id)
        if not target:
            raise ValueError(f"Target {target_id} not found")
        
        domain = target["primary_domain"]
        
        all_certs = []
        
        # crt.sh
        if config.get("use_crtsh", True):
            crtsh_results = await self._query_crtsh(domain)
            all_certs.extend(crtsh_results)
        
        # CertSpotter
        if config.get("use_certspotter", False):  # Requires API key
            spotter_results = await self._query_certspotter(domain)
            all_certs.extend(spotter_results)
        
        # Parse and extract subdomains
        subdomains = set()
        for cert in all_certs:
            for name in cert.get("dns_names", []):
                if domain in name:
                    subdomains.add(name)
        
        logger.info(f"CT logs: {len(all_certs)} certs, {len(subdomains)} unique subdomains")
        
        return {
            "certificates": len(all_certs),
            "subdomains_found": len(subdomains),
            "subdomains": list(subdomains)
        }
    
    async def _query_crtsh(self, domain: str) -> List[Dict]:
        """Query crt.sh"""
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=120) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        certs = []
                        for entry in data:
                            cert = {
                                "id": entry.get("id"),
                                "issuer": entry.get("issuer_name"),
                                "dns_names": entry.get("name_value", "").split("\n"),
                                "not_before": entry.get("not_before"),
                                "not_after": entry.get("not_after")
                            }
                            certs.append(cert)
                        
                        return certs
            except Exception as e:
                logger.error(f"crt.sh query failed: {e}")
        
        return []
    
    async def _query_certspotter(self, domain: str) -> List[Dict]:
        """Query CertSpotter API"""
        # Requires API key
        api_key = ""  # Would load from config
        
        if not api_key:
            logger.debug("No CertSpotter API key configured")
            return []
        
        url = f"https://api.certspotter.com/v1/issuances?domain={domain}&include_subdomains=true"
        
        async with aiohttp.ClientSession() as session:
            try:
                headers = {"Authorization": f"Bearer {api_key}"}
                async with session.get(url, headers=headers, timeout=60) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except Exception as e:
                logger.error(f"CertSpotter query failed: {e}")
        
        return []
