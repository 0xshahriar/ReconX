"""
Subdomain Enumeration Scanner
Integrates subfinder, amass, assetfinder, findomain, crt.sh
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager

logger = logging.getLogger(__name__)

@dataclass
class SubdomainResult:
    subdomain: str
    sources: List[str]
    ip_addresses: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "subdomain": self.subdomain,
            "sources": self.sources,
            "ip_addresses": self.ip_addresses or []
        }

class SubdomainEnumerator:
    """Multi-source subdomain enumeration"""
    
    def __init__(self, subprocess_mgr: SubprocessManager, db: DatabaseManager):
        self.subprocess_mgr = subprocess_mgr
        self.db = db
        self.tool_manager = ToolManager()
        self.results: Dict[str, SubdomainResult] = {}
    
    async def scan(
        self,
        target_id: str,
        scan_id: str,
        config: Dict[str, Any],
        previous_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run subdomain enumeration"""
        
        target = await self.db.get_target(target_id)
        if not target:
            raise ValueError(f"Target {target_id} not found")
        
        domain = target["primary_domain"]
        logger.info(f"Starting subdomain enumeration for {domain}")
        
        # Passive enumeration tasks
        tasks = []
        
        if config.get("use_subfinder", True):
            tasks.append(self._run_subfinder(domain))
        
        if config.get("use_amass", True):
            tasks.append(self._run_amass(domain))
        
        if config.get("use_assetfinder", True):
            tasks.append(self._run_assetfinder(domain))
        
        if config.get("use_findomain", True):
            tasks.append(self._run_findomain(domain))
        
        if config.get("use_crtsh", True):
            tasks.append(self._run_crtsh(domain))
        
        # Run all passive sources concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Subdomain tool failed: {result}")
                continue
            
            for subdomain_data in result:
                subdomain = subdomain_data["subdomain"]
                source = subdomain_data["source"]
                
                if subdomain in self.results:
                    if source not in self.results[subdomain].sources:
                        self.results[subdomain].sources.append(source)
                else:
                    self.results[subdomain] = SubdomainResult(
                        subdomain=subdomain,
                        sources=[source]
                    )
        
        # Brute force if enabled
        if config.get("brute_force", False):
            wordlist = config.get("wordlist", "subdomains-medium")
            await self._brute_force(domain, wordlist)
        
        # Permutation generation
        if config.get("permutations", False):
            await self._generate_permutations(domain)
        
        # Save results to database
        await self._save_results(scan_id)
        
        logger.info(f"Found {len(self.results)} unique subdomains")
        
        return {
            "total_found": len(self.results),
            "subdomains": [r.to_dict() for r in self.results.values()]
        }
    
    async def _run_subfinder(self, domain: str) -> List[Dict]:
        """Run subfinder"""
        await self.tool_manager.ensure_tool("subfinder")
        
        cmd = f"subfinder -d {domain} -all -silent -json"
        
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=300)
        
        results = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                results.append({
                    "subdomain": data.get("host", ""),
                    "source": "subfinder"
                })
            except json.JSONDecodeError:
                # Fallback to plain text parsing
                if line and not line.startswith('['):
                    results.append({"subdomain": line.strip(), "source": "subfinder"})
        
        logger.info(f"subfinder found {len(results)} subdomains")
        return results
    
    async def _run_amass(self, domain: str) -> List[Dict]:
        """Run amass (passive mode)"""
        await self.tool_manager.ensure_tool("amass")
        
        cmd = f"amass enum -passive -d {domain} -json"
        
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=600)
        
        results = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                name = data.get("name", "")
                if name:
                    results.append({"subdomain": name, "source": "amass"})
            except json.JSONDecodeError:
                pass
        
        logger.info(f"amass found {len(results)} subdomains")
        return results
    
    async def _run_assetfinder(self, domain: str) -> List[Dict]:
        """Run assetfinder"""
        await self.tool_manager.ensure_tool("assetfinder")
        
        cmd = f"assetfinder --subs-only {domain}"
        
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=180)
        
        results = []
        for line in stdout.strip().split('\n'):
            subdomain = line.strip()
            if subdomain and domain in subdomain:
                results.append({"subdomain": subdomain, "source": "assetfinder"})
        
        logger.info(f"assetfinder found {len(results)} subdomains")
        return results
    
    async def _run_findomain(self, domain: str) -> List[Dict]:
        """Run findomain"""
        await self.tool_manager.ensure_tool("findomain")
        
        cmd = f"findomain -t {domain} -q"
        
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=180)
        
        results = []
        for line in stdout.strip().split('\n'):
            subdomain = line.strip()
            if subdomain:
                results.append({"subdomain": subdomain, "source": "findomain"})
        
        logger.info(f"findomain found {len(results)} subdomains")
        return results
    
    async def _run_crtsh(self, domain: str) -> List[Dict]:
        """Query crt.sh certificate transparency logs"""
        import aiohttp
        
        results = []
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://crt.sh/?q=%.{domain}&output=json"
                
                async with session.get(url, timeout=60) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        seen = set()
                        for entry in data:
                            name = entry.get("name_value", "")
                            for sub in name.split('\n'):
                                sub = sub.strip()
                                if sub and sub not in seen and domain in sub:
                                    seen.add(sub)
                                    results.append({
                                        "subdomain": sub,
                                        "source": "crt.sh"
                                    })
            
            logger.info(f"crt.sh found {len(results)} subdomains")
            
        except Exception as e:
            logger.error(f"crt.sh query failed: {e}")
        
        return results
    
    async def _brute_force(self, domain: str, wordlist_name: str):
        """DNS brute force with wordlist"""
        from core.wordlist_manager import WordlistManager
        
        wordlist_mgr = WordlistManager()
        wordlist_path = wordlist_mgr.get_wordlist_path(wordlist_name)
        
        if not wordlist_path:
            logger.warning(f"Wordlist {wordlist_name} not found")
            return
        
        await self.tool_manager.ensure_tool("dnsx")
        
        cmd = f"dnsx -d {domain} -w {wordlist_path} -silent -json"
        
        stdout = await self.subprocess_mgr.run_simple(cmd, timeout=600)
        
        count = 0
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                subdomain = data.get("host", "")
                if subdomain and subdomain not in self.results:
                    self.results[subdomain] = SubdomainResult(
                        subdomain=subdomain,
                        sources=["brute-force"]
                    )
                    count += 1
            except json.JSONDecodeError:
                pass
        
        logger.info(f"Brute force found {count} new subdomains")
    
    async def _generate_permutations(self, domain: str):
        """Generate permutations like dev-api, api-staging, etc."""
        prefixes = ["dev", "staging", "test", "api", "admin", "portal", "app", "web"]
        suffixes = ["dev", "staging", "test", "prod", "1", "2", "old", "new"]
        
        permutations = set()
        base_subdomains = [s for s in self.results.keys() if s != domain]
        
        for sub in base_subdomains:
            parts = sub.replace(f".{domain}", "").split('.')
            base = parts[-1]
            
            for prefix in prefixes:
                permutations.add(f"{prefix}-{base}.{domain}")
                permutations.add(f"{prefix}{base}.{domain}")
            
            for suffix in suffixes:
                permutations.add(f"{base}-{suffix}.{domain}")
                permutations.add(f"{base}{suffix}.{domain}")
        
        # Check which permutations resolve
        if permutations:
            await self.tool_manager.ensure_tool("dnsx")
            
            # Write permutations to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for perm in permutations:
                    f.write(perm + '\n')
                temp_file = f.name
            
            cmd = f"dnsx -l {temp_file} -silent -json"
            stdout = await self.subprocess_mgr.run_simple(cmd, timeout=120)
            
            count = 0
            for line in stdout.strip().split('\n'):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    subdomain = data.get("host", "")
                    if subdomain and subdomain not in self.results:
                        self.results[subdomain] = SubdomainResult(
                            subdomain=subdomain,
                            sources=["permutation"]
                        )
                        count += 1
                except json.JSONDecodeError:
                    pass
            
            # Cleanup temp file
            import os
            os.unlink(temp_file)
            
            logger.info(f"Permutations found {count} new subdomains")
    
    async def _save_results(self, scan_id: str):
        """Save results to database"""
        for result in self.results.values():
            await self.db.add_subdomain(scan_id, result.to_dict())
