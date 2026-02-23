"""
Port Scanner
Fast port scanning with naabu and nmap
"""

import json
import logging
from typing import Dict, List, Any, Optional

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class PortScanner:
    """Port scanning with multiple tools"""
    
    TOP_PORTS = [80, 443, 8080, 8443, 3000, 8000, 8888, 9000, 5000, 7000,
                 22, 21, 23, 25, 53, 110, 143, 993, 995, 3306, 5432, 6379,
                 27017, 9200, 5601, 9090, 9092, 8081, 8082, 8083, 8880]
    
    def __init__(self, subprocess_mgr: SubprocessManager, db: DatabaseManager):
        self.subprocess_mgr = subprocess_mgr
        self.db = db
        self.tool_manager = ToolManager()
        self.results: Dict[str, List[Dict]] = {}
    
    async def scan(
        self,
        target_id: str,
        scan_id: str,
        config: Dict[str, Any],
        previous_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Scan ports on discovered hosts"""
        
        # Get IPs from DNS resolution
        dns_data = previous_results.get("dns_resolution", {})
        resolutions = dns_data.get("resolutions", {})
        
        # Also check subdomains with IPs
        subdomain_data = previous_results.get("subdomain_enum", {})
        subdomains = subdomain_data.get("subdomains", [])
        
        # Collect unique IPs
        targets = set()
        
        for subdomain, ips in resolutions.items():
            for ip in ips:
                targets.add(ip)
        
        # Add root domain if available
        target = await self.db.get_target(target_id)
        if target:
            targets.add(target["primary_domain"])
        
        if not targets:
            logger.warning("No targets for port scanning")
            return {"scanned": 0, "open_ports": 0}
        
        logger.info(f"Scanning ports on {len(targets)} targets")
        
        # Determine scan type
        scan_type = config.get("scan_type", "fast")  # fast, full, custom
        
        if scan_type == "fast":
            ports = config.get("ports", ",".join(map(str, self.TOP_PORTS)))
        elif scan_type == "full":
            ports = "1-65535"
        else:
            ports = config.get("ports", ",".join(map(str, self.TOP_PORTS)))
        
        # Use naabu for fast scanning
        total_open = 0
        
        for target in targets:
            open_ports = await self._scan_naabu(target, ports)
            
            if open_ports:
                self.results[target] = open_ports
                total_open += len(open_ports)
                
                # Save to database
                for port_data in open_ports:
                    await self.db._connection.execute("""
                        INSERT INTO ports (id, scan_id, ip, port, protocol, service, state)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        scan_id,
                        target,
                        port_data["port"],
                        "tcp",
                        port_data.get("service", "unknown"),
                        "open"
                    ))
                await self.db._connection.commit()
        
        # Service detection with nmap for top ports
        if config.get("service_detection", True) and total_open > 0:
            await self._service_detection(scan_id, self.results)
        
        logger.info(f"Found {total_open} open ports across {len(self.results)} hosts")
        
        return {
            "scanned": len(targets),
            "open_ports": total_open,
            "results": self.results
        }
    
    async def _scan_naabu(self, target: str, ports: str) -> List[Dict]:
        """Scan with naabu"""
        await self.tool_manager.ensure_tool("naabu")
        
        cmd = f"naabu -host {target} -port {ports} -silent -json"
        
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=300)
        
        results = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                results.append({
                    "port": data.get("port", 0),
                    "ip": data.get("ip", target),
                    "service": self._guess_service(data.get("port", 0))
                })
            except json.JSONDecodeError:
                # Parse plain text format
                if ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        try:
                            port = int(parts[1].strip())
                            results.append({
                                "port": port,
                                "ip": target,
                                "service": self._guess_service(port)
                            })
                        except ValueError:
                            pass
        
        return results
    
    async def _service_detection(self, scan_id: str, port_results: Dict[str, List[Dict]]):
        """Run nmap service detection on open ports"""
        await self.tool_manager.ensure_tool("nmap")
        
        # Limit to top 10 ports per host to save time
        for ip, ports in port_results.items():
            if len(ports) > 10:
                ports = ports[:10]
            
            port_list = ",".join([str(p["port"]) for p in ports])
            
            cmd = f"nmap -sV -p {port_list} --version-intensity 5 {ip} -oX -"
            
            try:
                stdout = await self.subprocess_mgr.run_simple(cmd, timeout=300)
                
                # Parse XML output (simplified)
                # Full implementation would use proper XML parsing
                
                # Update database with service info
                for port_data in ports:
                    # Try to extract service from nmap output
                    service = self._extract_service_from_nmap(stdout, port_data["port"])
                    if service:
                        await self.db._connection.execute("""
                            UPDATE ports SET service = ? 
                            WHERE scan_id = ? AND ip = ? AND port = ?
                        """, (service, scan_id, ip, port_data["port"]))
                        await self.db._connection.commit()
                        
            except Exception as e:
                logger.error(f"nmap service detection failed for {ip}: {e}")
    
    def _guess_service(self, port: int) -> str:
        """Guess service from common port numbers"""
        common_ports = {
            80: "http", 443: "https", 8080: "http-proxy", 8443: "https-alt",
            22: "ssh", 21: "ftp", 23: "telnet", 25: "smtp", 53: "dns",
            110: "pop3", 143: "imap", 993: "imaps", 995: "pop3s",
            3306: "mysql", 5432: "postgresql", 6379: "redis",
            27017: "mongodb", 9200: "elasticsearch", 5601: "kibana",
            3000: "http", 5000: "http", 8000: "http", 9000: "http"
        }
        return common_ports.get(port, "unknown")
    
    def _extract_service_from_nmap(self, xml_output: str, port: int) -> Optional[str]:
        """Extract service name from nmap XML output"""
        import re
        
        # Simple regex extraction
        pattern = rf'<port protocol="tcp" portid="{port}".*?<service name="([^"]*)"'
        match = re.search(pattern, xml_output)
        
        if match:
            return match.group(1)
        
        return None

import uuid
