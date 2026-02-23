"""
Web Fuzzer
Directory and file discovery with ffuf
"""

import json
import logging
from typing import Dict, List, Any, Optional

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager
from core.wordlist_manager import WordlistManager

logger = logging.getLogger(__name__)

class Fuzzer:
    """Web fuzzing for directories and files"""
    
    def __init__(self, subprocess_mgr: SubprocessManager, db: DatabaseManager):
        self.subprocess_mgr = subprocess_mgr
        self.db = db
        self.tool_manager = ToolManager()
        self.wordlist_mgr = WordlistManager()
    
    async def scan(
        self,
        target_id: str,
        scan_id: str,
        config: Dict[str, Any],
        previous_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Fuzz web endpoints"""
        
        # Get live URLs from HTTP probe
        http_data = previous_results.get("http_probe", {})
        live_hosts = http_data.get("results", [])
        
        if not live_hosts:
            logger.warning("No live hosts to fuzz")
            return {"fuzzed": 0, "found": 0}
        
        # Filter to interesting status codes
        targets = [h["url"] for h in live_hosts if h.get("status_code", 0) in [200, 301, 302, 403, 401]]
        
        if not targets:
            targets = [h["url"] for h in live_hosts if h.get("status_code", 0) > 0]
        
        logger.info(f"Fuzzing {len(targets)} targets")
        
        all_results = []
        
        for target in targets[:5]:  # Limit to first 5 to save time
            # Directory fuzzing
            dir_results = await self._fuzz_directories(target, config)
            all_results.extend(dir_results)
            
            # File fuzzing
            file_results = await self._fuzz_files(target, config)
            all_results.extend(file_results)
            
            # API endpoint fuzzing if API detected
            if any(tech in str(target).lower() for tech in ["api", "rest", "graphql"]):
                api_results = await self._fuzz_api(target, config)
                all_results.extend(api_results)
        
        # Save results
        for result in all_results:
            await self.db._connection.execute("""
                INSERT INTO endpoints (id, scan_id, url, method, status_code, 
                                     content_type, content_length, discovered_via)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(__import__('uuid').uuid4()),
                scan_id,
                result["url"],
                result.get("method", "GET"),
                result.get("status_code", 0),
                result.get("content_type", ""),
                result.get("content_length", 0),
                "ffuf"
            ))
        await self.db._connection.commit()
        
        logger.info(f"Fuzzing found {len(all_results)} endpoints")
        
        return {
            "fuzzed": len(targets),
            "found": len(all_results),
            "results": all_results
        }
    
    async def _fuzz_directories(self, target: str, config: Dict) -> List[Dict]:
        """Fuzz for directories"""
        await self.tool_manager.ensure_tool("ffuf")
        
        wordlist = self.wordlist_mgr.get_wordlist_path("directories")
        if not wordlist:
            return []
        
        cmd = f"ffuf -u {target}/FUZZ -w {wordlist} -mc 200,301,302,403 -json -s"
        
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=180)
        
        results = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                results.append({
                    "url": data.get("url", "").replace("/FUZZ", data.get("input", {}).get("FUZZ", "")),
                    "status_code": data.get("status", 0),
                    "content_length": data.get("length", 0),
                    "method": "GET",
                    "type": "directory"
                })
            except json.JSONDecodeError:
                pass
        
        return results
    
    async def _fuzz_files(self, target: str, config: Dict) -> List[Dict]:
        """Fuzz for files"""
        await self.tool_manager.ensure_tool("ffuf")
        
        wordlist = self.wordlist_mgr.get_wordlist_path("files")
        if not wordlist:
            return []
        
        cmd = f"ffuf -u {target}/FUZZ -w {wordlist} -mc 200 -json -s"
        
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=180)
        
        results = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                results.append({
                    "url": data.get("url", "").replace("/FUZZ", data.get("input", {}).get("FUZZ", "")),
                    "status_code": data.get("status", 0),
                    "content_length": data.get("length", 0),
                    "method": "GET",
                    "type": "file"
                })
            except json.JSONDecodeError:
                pass
        
        return results
    
    async def _fuzz_api(self, target: str, config: Dict) -> List[Dict]:
        """Fuzz API endpoints"""
        # Common API paths
        api_paths = ["v1", "v2", "api", "rest", "graphql", "swagger", "openapi.json"]
        
        results = []
        for path in api_paths:
            url = f"{target}/{path}"
            # Quick check with httpx
            cmd = f"httpx -u {url} -silent -status-code"
            stdout = await self.subprocess_mgr.run_simple(cmd, timeout=10)
            
            if stdout.strip() and "200" in stdout:
                results.append({
                    "url": url,
                    "status_code": 200,
                    "type": "api"
                })
        
        return results
