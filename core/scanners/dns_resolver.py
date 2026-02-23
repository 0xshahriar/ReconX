"""
DNS Resolver Scanner
Resolves subdomains to IPs using dnsx and massdns
"""

import json
import logging
from typing import Dict, List, Any, Optional

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class DNSResolver:
    """DNS resolution and validation"""
    
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
        """Resolve DNS for discovered subdomains"""
        
        # Get subdomains from previous results
        subdomain_data = previous_results.get("subdomain_enum", {})
        subdomains = subdomain_data.get("subdomains", [])
        
        if not subdomains:
            logger.warning("No subdomains to resolve")
            return {"resolved": 0}
        
        logger.info(f"Resolving {len(subdomains)} subdomains")
        
        # Extract subdomain names
        subdomain_names = [s["subdomain"] for s in subdomains]
        
        # Resolve using dnsx
        resolved = await self._resolve_dnsx(subdomain_names)
        
        # Update database with IP addresses
        updated_count = 0
        for sub_name, ip_list in resolved.items():
            # Find and update subdomain record
            for sub_data in subdomains:
                if sub_data["subdomain"] == sub_name:
                    # Update in database
                    await self._update_subdomain_ip(scan_id, sub_name, ip_list)
                    updated_count += 1
                    break
        
        # Wildcard detection
        wildcards = await self._detect_wildcards(domain=subdomain_names[0].split('.')[-2] + '.' + subdomain_names[0].split('.')[-1])
        
        logger.info(f"Resolved {updated_count} subdomains")
        
        return {
            "resolved": updated_count,
            "wildcards": wildcards,
            "resolutions": resolved
        }
    
    async def _resolve_dnsx(self, subdomains: List[str]) -> Dict[str, List[str]]:
        """Resolve subdomains using dnsx"""
        await self.tool_manager.ensure_tool("dnsx")
        
        import tempfile
        import os
        
        # Write subdomains to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for sub in subdomains:
                f.write(sub + '\n')
            temp_file = f.name
        
        try:
            cmd = f"dnsx -l {temp_file} -a -aaaa -silent -json"
            
            stdout = await self.subprocess_mgr.run_simple(cmd, timeout=300)
            
            results = {}
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    host = data.get("host", "")
                    ips = []
                    
                    # Collect A and AAAA records
                    if "a" in data:
                        ips.extend(data["a"])
                    if "aaaa" in data:
                        ips.extend(data["aaaa"])
                    
                    if host and ips:
                        results[host] = ips
                        
                except json.JSONDecodeError:
                    pass
            
            return results
            
        finally:
            os.unlink(temp_file)
    
    async def _update_subdomain_ip(self, scan_id: str, subdomain: str, ips: List[str]):
        """Update subdomain record with IP addresses"""
        # Get existing record
        existing = await self.db.get_subdomains(scan_id)
        
        for sub in existing:
            if sub["subdomain"] == subdomain:
                # Update with IPs
                await self.db._connection.execute("""
                    UPDATE subdomains SET ip_addresses = ? 
                    WHERE scan_id = ? AND subdomain = ?
                """, (json.dumps(ips), scan_id, subdomain))
                await self.db._connection.commit()
                break
    
    async def _detect_wildcards(self, domain: str) -> List[str]:
        """Detect wildcard DNS entries"""
        import random
        import string
        
        # Generate random subdomain
        random_sub = ''.join(random.choices(string.ascii_lowercase, k=20))
        test_domain = f"{random_sub}.{domain}"
        
        await self.tool_manager.ensure_tool("dnsx")
        
        cmd = f"dnsx -d {test_domain} -a -silent"
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=30)
        
        if stdout.strip():
            logger.warning(f"Wildcard detected for {domain}")
            return [domain]
        
        return []
