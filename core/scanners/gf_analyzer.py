"""
GF Pattern Analyzer
Pattern matching for vulnerabilities in URLs
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)

class GFAnalyzer:
    """GF pattern matching for vulnerability indicators"""
    
    PATTERNS = {
        "xss": {
            "pattern": r"[?&][^=]*=([^&]*)(<|>|\"|'|%3C|%3E|%22|%27)",
            "severity": "high",
            "description": "Potential XSS - reflected special characters in parameter"
        },
        "sqli": {
            "pattern": r"[?&][^=]*=([^&]*)(union|select|insert|update|delete|drop|--+|#|%23|and|or)",
            "severity": "critical",
            "description": "Potential SQL Injection - SQL keywords in parameter"
        },
        "ssrf": {
            "pattern": r"(url|path|dest|redirect|uri|src|next|continue)=([^&]*)",
            "severity": "high",
            "description": "Potential SSRF - URL-like parameter names"
        },
        "lfi": {
            "pattern": r"[?&][^=]*=([^&]*)(\.\.|%2e%2e|/etc/|/var/|/proc/|/home/|\\.\.)",
            "severity": "high",
            "description": "Potential LFI - path traversal patterns"
        },
        "rce": {
            "pattern": r"[?&][^=]*=([^&]*)(;|`|\$\(|\&\&|\|\||wget|curl|bash|sh|cmd|powershell)",
            "severity": "critical",
            "description": "Potential RCE - command injection patterns"
        },
        "idor": {
            "pattern": r"[?&](id|user|account|number|order|item|profile|doc|file)=([0-9]+)",
            "severity": "medium",
            "description": "Potential IDOR - numeric ID parameter"
        },
        "debug": {
            "pattern": r"(debug|test|dev|staging|admin|internal|local|beta|gamma)",
            "severity": "low",
            "description": "Debug/development endpoint"
        },
        "api_key": {
            "pattern": r"[?&](api[_-]?key|token|secret|password|passwd|pwd|auth)=([^&]{8,})",
            "severity": "critical",
            "description": "Potential API key or credential in URL"
        },
        "s3_bucket": {
            "pattern": r"s3\.amazonaws\.com|\.s3-[a-z0-9-]+\.amazonaws\.com|s3://",
            "severity": "medium",
            "description": "S3 bucket reference"
        }
    }
    
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
        """Analyze URLs for vulnerability patterns"""
        
        # Collect URLs from previous results
        urls = []
        
        # From HTTP probe
        http_data = previous_results.get("http_probe", {})
        for result in http_data.get("results", []):
            url = result.get("url", "")
            if url:
                urls.append(url)
        
        # From fuzzing
        fuzz_data = previous_results.get("fuzzing", {})
        for result in fuzz_data.get("results", []):
            url = result.get("url", "")
            if url:
                urls.append(url)
        
        # From wayback
        wayback_data = previous_results.get("wayback_urls", {})
        for url in wayback_data.get("urls", []):
            urls.append(url)
        
        if not urls:
            logger.warning("No URLs to analyze")
            return {"analyzed": 0, "matches": 0}
        
        # Remove duplicates
        urls = list(set(urls))
        
        logger.info(f"Analyzing {len(urls)} URLs for patterns")
        
        matches = []
        
        for url in urls:
            for pattern_name, pattern_info in self.PATTERNS.items():
                if re.search(pattern_info["pattern"], url, re.IGNORECASE):
                    matches.append({
                        "url": url,
                        "pattern": pattern_name,
                        "severity": pattern_info["severity"],
                        "description": pattern_info["description"]
                    })
                    
                    # Save to database as potential vulnerability
                    await self.db.add_vulnerability(scan_id, {
                        "title": f"Potential {pattern_name.upper()} - Pattern Match",
                        "severity": pattern_info["severity"],
                        "description": pattern_info["description"],
                        "affected_url": url,
                        "tool_source": "gf",
                        "false_positive": True  # Mark as potential FP until verified
                    })
        
        # Try to use gf tool if available
        try:
            await self.tool_manager.ensure_tool("gf")
            gf_matches = await self._run_gf_tool(urls)
            matches.extend(gf_matches)
        except Exception as e:
            logger.debug(f"gf tool not available: {e}")
        
        logger.info(f"Found {len(matches)} pattern matches")
        
        return {
            "analyzed": len(urls),
            "matches": len(matches),
            "patterns_found": matches
        }
    
    async def _run_gf_tool(self, urls: List[str]) -> List[Dict]:
        """Run gf tool for pattern matching"""
        import tempfile
        import os
        
        # Write URLs to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for url in urls:
                f.write(url + '\n')
            temp_file = f.name
        
        matches = []
        
        try:
            for pattern in ["xss", "sqli", "ssrf", "lfi", "rce"]:
                cmd = f"cat {temp_file} | gf {pattern}"
                
                stdout = await self.subprocess_mgr.run_simple(cmd, timeout=60)
                
                for line in stdout.strip().split('\n'):
                    if line:
                        matches.append({
                            "url": line,
                            "pattern": pattern,
                            "source": "gf"
                        })
        
        finally:
            os.unlink(temp_file)
        
        return matches
