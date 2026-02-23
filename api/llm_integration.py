"""
ReconX LLM Integration
Manages Ollama models with auto-scaling based on system resources
"""

import asyncio
import json
import logging
import psutil
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LLMManager:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.current_model: Optional[str] = None
        self.is_loaded = False
        self._memory_thresholds = {
            "llama3.1:8b": 6000,   # 6GB free RAM required
            "gemma3:4b": 3500,      # 3.5GB free RAM required
            "gemma3:1b": 1500,      # 1.5GB free RAM required
        }
        self._unload_task: Optional[asyncio.Task] = None
        self._idle_timeout = 300  # 5 minutes
    
    def get_free_memory_mb(self) -> int:
        """Get available system memory in MB"""
        memory = psutil.virtual_memory()
        return int(memory.available / (1024 * 1024))
    
    def get_memory_usage(self) -> Optional[Dict]:
        """Get current memory usage stats"""
        memory = psutil.virtual_memory()
        return {
            "total_mb": int(memory.total / (1024 * 1024)),
            "available_mb": int(memory.available / (1024 * 1024)),
            "percent_used": memory.percent
        }
    
    def select_optimal_model(self) -> str:
        """Select best model based on available memory"""
        free_mem = self.get_free_memory_mb()
        
        if free_mem >= self._memory_thresholds["llama3.1:8b"]:
            return "llama3.1:8b"
        elif free_mem >= self._memory_thresholds["gemma3:4b"]:
            return "gemma3:4b"
        else:
            return "gemma3:1b"
    
    async def load_model(self, model_name: str) -> bool:
        """Load specific model into Ollama"""
        import aiohttp
        
        try:
            logger.info(f"Loading LLM model: {model_name}")
            
            async with aiohttp.ClientSession() as session:
                # Pull model if not exists
                async with session.post(
                    f"{self.ollama_url}/api/pull",
                    json={"name": model_name, "stream": False}
                ) as resp:
                    if resp.status not in [200, 409]:  # 409 = already exists
                        logger.warning(f"Model pull returned {resp.status}")
            
            # Load model
            async with session.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model_name, "prompt": "Hello", "stream": False}
            ) as resp:
                if resp.status == 200:
                    self.current_model = model_name
                    self.is_loaded = True
                    logger.info(f"Model {model_name} loaded successfully")
                    return True
                    
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
        
        return False
    
    async def unload_model(self):
        """Unload model to free memory"""
        if not self.is_loaded:
            return
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Ollama doesn't have explicit unload, but we can stop using it
                pass
            
            self.current_model = None
            self.is_loaded = False
            logger.info("LLM model unloaded")
            
        except Exception as e:
            logger.error(f"Error unloading model: {e}")
    
    async def switch_model(self, model_name: str) -> bool:
        """Switch to different model"""
        if self.current_model == model_name:
            return True
        
        await self.unload_model()
        return await self.load_model(model_name)
    
    async def auto_scale(self) -> str:
        """Automatically select and load optimal model"""
        optimal = self.select_optimal_model()
        
        if self.current_model != optimal:
            logger.info(f"Auto-scaling LLM: {self.current_model} -> {optimal}")
            await self.switch_model(optimal)
        
        return optimal
    
    async def generate(self, prompt: str, system: Optional[str] = None,
                       temperature: float = 0.7) -> Optional[str]:
        """Generate text using current model"""
        if not self.is_loaded:
            await self.auto_scale()
        
        # Cancel any pending unload
        if self._unload_task and not self._unload_task.done():
            self._unload_task.cancel()
        
        # Schedule new unload
        self._unload_task = asyncio.create_task(self._delayed_unload())
        
        import aiohttp
        
        try:
            payload = {
                "model": self.current_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }
            
            if system:
                payload["system"] = system
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("response", "")
                    else:
                        logger.error(f"LLM generation failed: {resp.status}")
                        
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
        
        return None
    
    async def analyze_vulnerability(self, vuln_data: Dict) -> Dict:
        """Analyze vulnerability for false positives and severity"""
        prompt = f"""
        Analyze this security finding:
        
        Title: {vuln_data.get('title')}
        Tool: {vuln_data.get('tool_source')}
        Severity: {vuln_data.get('severity')}
        Evidence: {vuln_data.get('evidence', 'N/A')}
        
        Tasks:
        1. Is this likely a false positive? (yes/no/maybe)
        2. Adjusted severity (critical/high/medium/low/info)
        3. Brief explanation (2-3 sentences)
        4. Remediation advice
        
        Respond in JSON format.
        """
        
        response = await self.generate(prompt, temperature=0.3)
        
        if response:
            try:
                # Try to parse JSON from response
                # Handle cases where LLM wraps JSON in markdown
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0]
                
                analysis = json.loads(json_str.strip())
                return {
                    "false_positive": analysis.get("false_positive", "maybe") == "yes",
                    "adjusted_severity": analysis.get("adjusted_severity", vuln_data.get('severity')),
                    "explanation": analysis.get("explanation", ""),
                    "remediation": analysis.get("remediation", ""),
                    "model_used": self.current_model
                }
            except Exception as e:
                logger.error(f"Failed to parse LLM analysis: {e}")
        
        return {
            "false_positive": False,
            "adjusted_severity": vuln_data.get('severity'),
            "explanation": "Analysis failed",
            "remediation": "",
            "model_used": self.current_model
        }
    
    async def _delayed_unload(self):
        """Unload model after idle timeout"""
        await asyncio.sleep(self._idle_timeout)
        await self.unload_model()
