"""
Nuclei Scanner Wrapper
Vulnerability scanning with Nuclei templates
"""

import json
import logging
import uuid
from typing import Dict, List, Any, Optional

from api.database import DatabaseManager
from core.subprocess_manager import SubprocessManager
from core.tool_manager import ToolManager
from api.llm_integration import LLMManager

logger = logging.getLogger(__name__)

class NucleiScanner:
    """Nuclei vulnerability scanner integration"""
    
    def __init__(self, subprocess_mgr: SubprocessManager, db: DatabaseManager,
                 llm_manager: Optional[LLMManager] = None):
        self.subprocess_mgr = subprocess_mgr
        self.db = db
        self.tool_manager = ToolManager()
        self.llm_manager = llm_manager
    
    async def scan(
        self,
        target_id: str,
        scan_id: str,
        config: Dict[str, Any],
        previous_results: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run Nuclei vulnerability scan"""
        
        # Get live hosts
        http_data = previous_results.get("http_probe", {})
        live_hosts = http_data.get("results", [])
        
        if not live_hosts:
            logger.warning("No live hosts for Nuclei scan")
            return {"scanned": 0, "findings": 0}
        
        # Prepare targets
        targets = [h["url"] for h in live_hosts if h.get("status_code", 0) > 0]
        
        if not targets:
            logger.warning("No valid targets")
            return {"scanned": 0, "findings": 0}
        
        logger.info(f"Running Nuclei on {len(targets)} targets")
        
        # Ensure nuclei and templates are installed
        await self.tool_manager.ensure_tool("nuclei")
        
        # Update templates
        if config.get("update_templates", True):
            await self._update_templates()
        
        # Build command
        severity = config.get("severity", "critical,high,medium")
        rate_limit = config.get("rate_limit", 150)
        timeout = config.get("timeout", 30)
        
        import tempfile
        import os
        
        # Write targets to file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for target in targets:
                f.write(target + '\n')
            targets_file = f.name
        
        results = []
        
        try:
            cmd = (f"nuclei -l {targets_file} -severity {severity} "
                   f"-rate-limit {rate_limit} -timeout {timeout} "
                   f"-json -silent")
            
            if config.get("tags"):
                cmd += f" -tags {config['tags']}"
            
            if config.get("exclude_tags"):
                cmd += f" -exclude-tags {config['exclude_tags']}"
            
            # Run with output parsing
            stdout_lines = []
            
            def parse_output(line: str):
                stdout_lines.append(line)
                try:
                    data = json.loads(line)
                    results.append(self._parse_nuclei_result(data))
                except json.JSONDecodeError:
                    pass
            
            await self.subprocess_mgr.run(
                cmd,
                timeout=1800,  # 30 minutes max
                stdout_callback=parse_output
            )
            
            # Process results
            verified_results = []
            for result in results:
                if not result:
                    continue
                
                # LLM-based false positive filtering
                if self.llm_manager and config.get("llm_filter", True):
                    is_fp = await self._check_false_positive(result)
                    if is_fp:
                        result["false_positive"] = True
                        logger.debug(f"Filtered likely false positive: {result['name']}")
                
                # Save to database
                await self.db.add_vulnerability(scan_id, {
                    "title": result.get("name", "Unknown"),
                    "severity": result.get("severity", "info"),
                    "description": result.get("description", ""),
                    "affected_url": result.get("url", ""),
                    "evidence": json.dumps(result.get("extracted_results", [])),
                    "tool_source": "nuclei",
                    "template_id": result.get("template_id", ""),
                    "false_positive": result.get("false_positive", False),
                    "llm_analysis": result.get("llm_analysis", ""),
                    "llm_model": self.llm_manager.current_model if self.llm_manager else None
                })
                
                if not result.get("false_positive"):
                    verified_results.append(result)
            
            logger.info(f"Nuclei found {len(results)} issues, {len(verified_results)} after filtering")
            
            return {
                "scanned": len(targets),
                "findings": len(results),
                "verified": len(verified_results),
                "results": verified_results
            }
            
        finally:
            os.unlink(targets_file)
    
    def _parse_nuclei_result(self, data: Dict) -> Dict:
        """Parse Nuclei JSON output"""
        return {
            "name": data.get("info", {}).get("name", "Unknown"),
            "severity": data.get("info", {}).get("severity", "info"),
            "description": data.get("info", {}).get("description", ""),
            "url": data.get("host", ""),
            "template_id": data.get("template-id", ""),
            "matcher_name": data.get("matcher-name", ""),
            "extracted_results": data.get("extracted-results", []),
            "curl_command": data.get("curl-command", ""),
            "false_positive": False
        }
    
    async def _update_templates(self):
        """Update Nuclei templates"""
        try:
            cmd = "nuclei -ut"
            await self.subprocess_mgr.run_simple(cmd, timeout=300)
            logger.info("Nuclei templates updated")
        except Exception as e:
            logger.error(f"Failed to update templates: {e}")
    
    async def _check_false_positive(self, result: Dict) -> bool:
        """Use LLM to check if result is likely false positive"""
        if not self.llm_manager:
            return False
        
        try:
            prompt = f"""
            Analyze this Nuclei finding for false positive likelihood:
            
            Template: {result.get('template_id')}
            Name: {result.get('name')}
            Severity: {result.get('severity')}
            URL: {result.get('url')}
            Evidence: {result.get('extracted_results', [])}
            
            Is this likely a false positive? Consider:
            1. Is the detection pattern specific enough?
            2. Could this be a default page or configuration?
            3. Is there actual security impact?
            
            Respond with: YES (false positive), NO (valid finding), or MAYBE (needs manual review)
            """
            
            response = await self.llm_manager.generate(prompt, temperature=0.3)
            
            if response:
                response_upper = response.upper()
                result["llm_analysis"] = response
                
                if "YES" in response_upper:
                    return True
                elif "MAYBE" in response_upper:
                    result["severity"] = "info"  # Downgrade severity
            
            return False
            
        except Exception as e:
            logger.error(f"LLM false positive check failed: {e}")
            return False

