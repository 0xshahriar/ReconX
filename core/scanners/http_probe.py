"""
HTTP Prober
HTTP/HTTPS probing with httpx for live host detection
"""

import json
import logging
from typing import Dict, List, Any, Optional

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class HTTPProber:
    """HTTP/HTTPS probing and technology detection"""
    
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
        """Probe hosts for HTTP/HTTPS services"""
        
        # Get subdomains from previous results
        subdomain_data = previous_results.get("subdomain_enum", {})
        subdomains = subdomain_data.get("subdomains", [])
        
        if not subdomains:
            logger.warning("No subdomains to probe")
            return {"probed": 0, "live": 0}
        
        logger.info(f"Probing {len(subdomains)} hosts")
        
        # Prepare target list
        targets = [s["subdomain"] for s in subdomains]
        
        # Also add IPs from port scan if available
        port_data = previous_results.get("port_scan", {})
        for ip, ports in port_data.get("results", {}).items():
            for port_info in ports:
                if port_info["port"] in [80, 443, 8080, 8443, 3000, 8000]:
                    if port_info["port"] == 443:
                        targets.append(f"https://{ip}:{port_info['port']}")
                    else:
                        targets.append(f"http://{ip}:{port_info['port']}")
        
        # Run httpx
        results = await self._run_httpx(targets, config)
        
        # Update database
        live_count = 0
        for result in results:
            if result.get("status_code", 0) > 0:
                live_count += 1
                await self._update_subdomain(scan_id, result)
        
        logger.info(f"Found {live_count} live hosts")
        
        return {
            "probed": len(targets),
            "live": live_count,
            "results": results
        }
    
    async def _run_httpx(self, targets: List[str], config: Dict) -> List[Dict]:
        """Run httpx on targets"""
        await self.tool_manager.ensure_tool("httpx")
        
        import tempfile
        import os
        
        # Write targets to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for target in targets:
                # Clean target (remove protocol if present for input)
                clean_target = target.replace("http://", "").replace("https://", "")
                f.write(clean_target + '\n')
            temp_file = f.name
        
        try:
            # Build httpx command
            flags = [
                "-l", temp_file,
                "-silent",
                "-json",
                "-timeout", str(config.get("timeout", 10)),
                "-retries", str(config.get("retries", 1)),
                "-status-code",
                "-title",
                "-tech-detect",
                "-content-length",
                "-web-server",
                "-location"
            ]
            
            if config.get("follow_redirects", True):
                flags.append("-follow-redirects")
            
            cmd = f"httpx {' '.join(flags)}"
            
            stdout = await self.subprocess_mgr.run_simple(cmd, timeout=600)
            
            results = []
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    results.append({
                        "url": data.get("url", ""),
                        "status_code": data.get("status_code", 0),
                        "title": data.get("title", ""),
                        "tech": data.get("tech", []),
                        "content_length": data.get("content_length", 0),
                        "webserver": data.get("webserver", ""),
                        "location": data.get("location", ""),
                        "host": data.get("host", "")
                    })
                except json.JSONDecodeError:
                    pass
            
            return results
            
        finally:
            os.unlink(temp_file)
    
    async def _update_subdomain(self, scan_id: str, result: Dict):
        """Update subdomain with HTTP info"""
        host = result.get("host", "")
        if not host:
            return
        
        # Find and update subdomain
        subdomains = await self.db.get_subdomains(scan_id)
        
        for sub in subdomains:
            if sub["subdomain"] == host:
                await self.db._connection.execute("""
                    UPDATE subdomains SET 
                        status_code = ?,
                        title = ?,
                        tech_stack = ?,
                        is_live = ?,
                        headers = ?
                    WHERE scan_id = ? AND subdomain = ?
                """, (
                    result.get("status_code"),
                    result.get("title"),
                    json.dumps(result.get("tech", [])),
                    True,
                    json.dumps({"content_length": result.get("content_length")}),
                    scan_id,
                    host
                ))
                await self.db._connection.commit()
                break
