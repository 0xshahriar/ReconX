"""
JavaScript Analyzer
Extract secrets, endpoints, and analyze JS files
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, urlparse

import aiohttp

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)

class JSAnalyzer:
    """JavaScript file analysis"""
    
    SECRET_PATTERNS = {
        "aws_access_key": r"AKIA[0-9A-Z]{16}",
        "aws_secret_key": r"[0-9a-zA-Z/+]{40}",
        "google_api_key": r"AIza[0-9A-Za-z_-]{35}",
        "github_token": r"gh[pousr]_[A-Za-z0-9_]{36,}",
        "slack_token": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}(-[a-zA-Z0-9]{24})?",
        "private_key": r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
        "jwt_token": r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*",
        "api_key_generic": r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][a-z0-9]{16,}['\"]",
        "password": r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        "secret": r"(?i)(secret|token)\s*[:=]\s*['\"][a-z0-9]{16,}['\"]"
    }
    
    ENDPOINT_PATTERNS = [
        r"['\"](/api/[a-zA-Z0-9/_-]+)['\"]",
        r"['\"](/v[0-9]+/[a-zA-Z0-9/_-]+)['\"]",
        r"['\"](https?://[^'\"]+/[^'\"]+)['\"]",
        r"fetch\(['\"]([^'\"]+)['\"]",
        r"axios\.(get|post|put|delete)\(['\"]([^'\"]+)['\"]",
        r"\.ajax\(\{[^}]*url:\s*['\"]([^'\"]+)['\"]",
        r"url:\s*['\"]([^'\"]+)['\"]"
    ]
    
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
        """Analyze JavaScript files"""
        
        # Get live hosts
        http_data = previous_results.get("http_probe", {})
        live_hosts = http_data.get("results", [])
        
        if not live_hosts:
            logger.warning("No live hosts for JS analysis")
            return {"analyzed": 0, "secrets": 0, "endpoints": 0}
        
        # Collect JS URLs
        js_urls = []
        
        for host in live_hosts:
            base_url = host.get("url", "")
            if not base_url:
                continue
            
            # Common JS paths
            common_js = [
                "/js/main.js", "/js/app.js", "/static/js/app.js",
                "/assets/js/app.js", "/scripts/main.js",
                "/main.js", "/app.js", "/bundle.js"
            ]
            
            for js_path in common_js:
                js_url = urljoin(base_url, js_path)
                js_urls.append(js_url)
        
        # Remove duplicates
        js_urls = list(set(js_urls))
        
        logger.info(f"Analyzing {len(js_urls)} JavaScript files")
        
        all_secrets = []
        all_endpoints = []
        
        # Download and analyze JS files
        async with aiohttp.ClientSession() as session:
            for js_url in js_urls[:20]:  # Limit to 20 files
                try:
                    content = await self._download_js(session, js_url)
                    if not content:
                        continue
                    
                    # Find secrets
                    secrets = self._find_secrets(content, js_url)
                    all_secrets.extend(secrets)
                    
                    # Find endpoints
                    endpoints = self._find_endpoints(content, js_url)
                    all_endpoints.extend(endpoints)
                    
                    # Check for source maps
                    source_map = await self._check_source_map(session, js_url, content)
                    if source_map:
                        logger.info(f"Found source map for {js_url}")
                    
                except Exception as e:
                    logger.debug(f"Failed to analyze {js_url}: {e}")
        
        # Save secrets as vulnerabilities
        for secret in all_secrets:
            await self.db.add_vulnerability(scan_id, {
                "title": f"Hardcoded {secret['type']} in JavaScript",
                "severity": "critical",
                "description": f"Found potential {secret['type']} in {secret['file']}",
                "affected_url": secret["file"],
                "evidence": f"Pattern match: {secret['pattern'][:50]}...",
                "tool_source": "js_analyzer"
            })
        
        # Save endpoints
        for endpoint in all_endpoints:
            await self.db._connection.execute("""
                INSERT INTO endpoints (id, scan_id, url, method, discovered_via)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(__import__('uuid').uuid4()),
                scan_id,
                endpoint["url"],
                "GET",
                "js_analyzer"
            ))
        await self.db._connection.commit()
        
        logger.info(f"JS analysis: {len(all_secrets)} secrets, {len(all_endpoints)} endpoints")
        
        return {
            "analyzed": len(js_urls),
            "secrets": len(all_secrets),
            "endpoints": len(all_endpoints),
            "secret_findings": all_secrets,
            "endpoint_findings": all_endpoints
        }
    
    async def _download_js(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Download JavaScript file"""
        try:
            async with session.get(url, timeout=30) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    # Check if it's actually JS
                    if len(content) > 100 and ('function' in content or 'var' in content or 'const' in content):
                        return content
        except Exception as e:
            logger.debug(f"Failed to download {url}: {e}")
        
        return None
    
    def _find_secrets(self, content: str, source_url: str) -> List[Dict]:
        """Find secrets in JS content"""
        secrets = []
        
        for secret_type, pattern in self.SECRET_PATTERNS.items():
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                # Get context around match
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                context = content[start:end]
                
                secrets.append({
                    "type": secret_type,
                    "pattern": match.group(),
                    "context": context,
                    "file": source_url,
                    "line": content[:match.start()].count('\n') + 1
                })
        
        return secrets
    
    def _find_endpoints(self, content: str, source_url: str) -> List[Dict]:
        """Find API endpoints in JS content"""
        endpoints = []
        seen = set()
        
        base_domain = urlparse(source_url).netloc
        
        for pattern in self.ENDPOINT_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                # Get the captured group (the URL/path)
                url = match.group(1) if match.groups() else match.group()
                
                if url and url not in seen:
                    seen.add(url)
                    
                    # Resolve relative URLs
                    if url.startswith('/'):
                        full_url = f"https://{base_domain}{url}"
                    elif url.startswith('http'):
                        full_url = url
                    else:
                        full_url = urljoin(source_url, url)
                    
                    endpoints.append({
                        "url": full_url,
                        "source": source_url,
                        "context": match.group()[:100]
                    })
        
        return endpoints
    
    async def _check_source_map(self, session: aiohttp.ClientSession, 
                               js_url: str, content: str) -> Optional[str]:
        """Check for source map reference"""
        # Look for sourceMappingURL comment
        match = re.search(r'//# sourceMappingURL=(.+)$', content, re.MULTILINE)
        
        if match:
            map_url = match.group(1)
            
            # Resolve relative URL
            if not map_url.startswith('http'):
                map_url = urljoin(js_url, map_url)
            
            try:
                async with session.get(map_url, timeout=30) as resp:
                    if resp.status == 200:
                        return map_url
            except Exception:
                pass
        
        return None

import uuid
