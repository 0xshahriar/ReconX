"""
ReconX Scanner Engine
Main orchestration logic for reconnaissance workflows
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from api.database import DatabaseManager
from api.tasks import ScanTask
from api.state_manager import StateManager
from api.llm_integration import LLMManager
from core.subprocess_manager import SubprocessManager
from core.state_checkpoint import StateCheckpoint
from core.scanners.subdomain_enum import SubdomainEnumerator
from core.scanners.dns_resolver import DNSResolver
from core.scanners.port_scanner import PortScanner
from core.scanners.http_probe import HTTPProber
from core.scanners.fuzzer import Fuzzer
from core.scanners.gf_analyzer import GFAnalyzer
from core.scanners.js_analyzer import JSAnalyzer
from core.scanners.nuclei_wrapper import NucleiScanner
from core.scanners.wayback_machine import WaybackMachine

logger = logging.getLogger(__name__)

class ScannerEngine:
    """Main scanning orchestrator"""
    
    MODULE_ORDER = [
        "subdomain_enum",
        "dns_resolution", 
        "http_probe",
        "port_scan",
        "wayback_urls",
        "js_analysis",
        "gf_patterns",
        "fuzzing",
        "nuclei_scan"
    ]
    
    def __init__(self, db: DatabaseManager, task: ScanTask):
        self.db = db
        self.task = task
        self.scan_id = task.scan_id
        self.target_id = task.target_id
        self.config = task.config
        
        # Initialize components
        self.subprocess_mgr = SubprocessManager()
        self.state_checkpoint = StateCheckpoint(db, self.scan_id)
        self.llm_manager = LLMManager()
        
        # Initialize scanners
        self.scanners = {
            "subdomain_enum": SubdomainEnumerator(self.subprocess_mgr, db),
            "dns_resolution": DNSResolver(self.subprocess_mgr, db),
            "http_probe": HTTPProber(self.subprocess_mgr, db),
            "port_scan": PortScanner(self.subprocess_mgr, db),
            "wayback_urls": WaybackMachine(self.subprocess_mgr, db),
            "js_analysis": JSAnalyzer(self.subprocess_mgr, db),
            "gf_patterns": GFAnalyzer(self.subprocess_mgr, db),
            "fuzzing": Fuzzer(self.subprocess_mgr, db),
            "nuclei_scan": NucleiScanner(self.subprocess_mgr, db, self.llm_manager)
        }
        
        self.results_cache: Dict[str, Any] = {}
        self._paused = False
        self._stopped = False
    
    async def run(self):
        """Execute full scan workflow"""
        logger.info(f"Starting scan {self.scan_id} for target {self.target_id}")
        
        # Check for resume state
        resume_state = await self.state_checkpoint.load_state()
        start_index = 0
        
        if resume_state and resume_state.get("can_resume"):
            logger.info(f"Resuming scan from module: {resume_state.get('current_module')}")
            start_index = self._get_module_index(resume_state.get("current_module"))
            self.results_cache = resume_state.get("results_cache", {})
        
        # Execute modules in order
        for i, module_name in enumerate(self.MODULE_ORDER[start_index:], start=start_index):
            if self._stopped:
                logger.info("Scan stopped by user")
                break
            
            if self._paused:
                logger.info("Scan paused, waiting...")
                await self._wait_for_resume()
            
            if self._stopped:
                break
            
            await self._run_module(module_name, i)
        
        if not self._stopped:
            logger.info(f"Scan {self.scan_id} completed successfully")
            await self.state_checkpoint.clear_state()
    
    async def _run_module(self, module_name: str, index: int):
        """Run a single scanning module"""
        logger.info(f"[{self.scan_id}] Running module: {module_name}")
        
        self.task.current_module = module_name
        self.task.progress[module_name] = 0
        
        await self.db.update_scan_status(
            self.scan_id,
            "running",
            current_task=f"Running {module_name}",
            progress=self.task.progress
        )
        
        try:
            scanner = self.scanners.get(module_name)
            if not scanner:
                logger.warning(f"Unknown module: {module_name}")
                return
            
            # Execute module with dependency injection
            module_results = await scanner.scan(
                target_id=self.target_id,
                scan_id=self.scan_id,
                config=self.config.get(module_name, {}),
                previous_results=self.results_cache
            )
            
            # Cache results for downstream modules
            self.results_cache[module_name] = module_results
            
            # Update progress
            self.task.progress[module_name] = 100
            await self.db.update_scan_status(
                self.scan_id,
                "running",
                progress=self.task.progress
            )
            
            # Save checkpoint
            await self.state_checkpoint.save_state(
                current_module=module_name,
                completed_modules=self.MODULE_ORDER[:index+1],
                pending_modules=self.MODULE_ORDER[index+1:],
                results_cache=self.results_cache
            )
            
        except Exception as e:
            logger.error(f"Module {module_name} failed: {e}")
            # Continue with next module unless critical
            if self.config.get("stop_on_error", False):
                raise
    
    def _get_module_index(self, module_name: Optional[str]) -> int:
        """Get index of module in execution order"""
        if not module_name:
            return 0
        try:
            return self.MODULE_ORDER.index(module_name)
        except ValueError:
            return 0
    
    async def _wait_for_resume(self):
        """Wait for scan to be resumed"""
        while self._paused and not self._stopped:
            await asyncio.sleep(1)
    
    def pause(self):
        """Pause scan execution"""
        self._paused = True
        self.subprocess_mgr.pause_all()
        logger.info(f"Scan {self.scan_id} paused")
    
    def resume(self):
        """Resume scan execution"""
        self._paused = False
        self.subprocess_mgr.resume_all()
        logger.info(f"Scan {self.scan_id} resumed")
    
    def stop(self):
        """Stop scan execution"""
        self._stopped = True
        self.subprocess_mgr.stop_all()
        logger.info(f"Scan {self.scan_id} stopped")
