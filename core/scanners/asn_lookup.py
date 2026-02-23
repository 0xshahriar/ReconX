"""
ASN Lookup Scanner
ASN and IP range enumeration
"""

import logging
from typing import Dict, List, Any, Optional

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class ASNLookup:
    """ASN and BGP data lookup"""
    
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
        """Perform ASN lookup"""
        
        target = await self.db.get_target(target_id)
        if not target:
            raise ValueError(f"Target {target_id} not found")
        
        domain = target["primary_domain"]
        
        # Get IPs from DNS resolution
        dns_data = previous_results.get("dns_resolution", {})
        resolutions = dns_data.get("resolutions", {})
        
        # Get first IP for ASN lookup
        sample_ip = None
        for subdomain, ips in resolutions.items():
            if ips:
                sample_ip = ips[0]
                break
        
        if not sample_ip:
            logger.warning("No IPs available for ASN lookup")
            return {"asns_found": 0}
        
        # Run asnmap
        await self.tool_manager.ensure_tool("asnmap")
        
        cmd = f"asnmap -ip {sample_ip} -json"
        
        try:
            stdout = await self.subprocess_mgr.run_simple(cmd, timeout=60)
            
            import json
            asn_data = json.loads(stdout.strip())
            
            asns = []
            for entry in asn_data:
                asn_info = {
                    "asn": entry.get("asn"),
                    "ip": entry.get("ip"),
                    "desc": entry.get("desc", ""),
                    "country": entry.get("country", "")
                }
                asns.append(asn_info)
                
                # Update target with ASN info
                await self._update_target_asn(target_id, asn_info)
            
            logger.info(f"Found {len(asns)} ASN entries")
            
            return {
                "asns_found": len(asns),
                "asns": asns
            }
            
        except Exception as e:
            logger.error(f"ASN lookup failed: {e}")
            return {"asns_found": 0}
    
    async def _update_target_asn(self, target_id: str, asn_info: Dict):
        """Update target with ASN information"""
        try:
            target = await self.db.get_target(target_id)
            if target:
                asn_list = target.get("asn_list", [])
                if isinstance(asn_list, str):
                    import json
                    asn_list = json.loads(asn_list)
                
                if asn_info["asn"] not in asn_list:
                    asn_list.append(asn_info["asn"])
                
                await self.db._connection.execute("""
                    UPDATE targets SET asn_list = ? WHERE id = ?
                """, (json.dumps(asn_list), target_id))
                await self.db._connection.commit()
        except Exception as e:
            logger.error(f"Failed to update target ASN: {e}")
