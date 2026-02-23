"""
ReconX Tunnel Manager
Manages Cloudflare, Ngrok, and LocalTunnel for remote access
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TunnelInfo:
    service: str
    url: str
    process: Optional[asyncio.subprocess.Process] = None

class TunnelManager:
    def __init__(self):
        self.current_tunnel: Optional[TunnelInfo] = None
        self._preferred_service = "cloudflare"  # cloudflare | ngrok | localtunnel
    
    async def start_tunnel(self, preferred_service: Optional[str] = None) -> Dict:
        """Start tunnel with auto-fallback"""
        service = preferred_service or self._preferred_service
        
        # Try services in order
        services = [service]
        if service != "cloudflare":
            services.append("cloudflare")
        if service != "ngrok":
            services.append("ngrok")
        if service != "localtunnel":
            services.append("localtunnel")
        
        for svc in services:
            try:
                if svc == "cloudflare" and await self._is_cloudflare_available():
                    return await self._start_cloudflare()
                elif svc == "ngrok" and await self._is_ngrok_available():
                    return await self._start_ngrok()
                elif svc == "localtunnel":
                    return await self._start_localtunnel()
            except Exception as e:
                logger.warning(f"Failed to start {svc}: {e}")
                continue
        
        raise Exception("All tunnel services failed")
    
    async def _is_cloudflare_available(self) -> bool:
        """Check if cloudflared is installed and configured"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "which", "cloudflared",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False
    
    async def _is_ngrok_available(self) -> bool:
        """Check if ngrok is installed"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "which", "ngrok",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False
    
    async def _start_cloudflare(self) -> Dict:
        """Start Cloudflare tunnel"""
        logger.info("Starting Cloudflare tunnel...")
        
        proc = await asyncio.create_subprocess_exec(
            "cloudflared", "tunnel", "--url", "http://localhost:8000",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for URL
        url = await self._extract_cloudflare_url(proc)
        
        self.current_tunnel = TunnelInfo(
            service="cloudflare",
            url=url,
            process=proc
        )
        
        logger.info(f"Cloudflare tunnel started: {url}")
        return {"service": "cloudflare", "url": url}
    
    async def _extract_cloudflare_url(self, proc: asyncio.subprocess.Process, 
                                       timeout: int = 30) -> str:
        """Extract tunnel URL from cloudflared output"""
        pattern = r'https://[a-zA-Z0-9-]+\.trycloudflare\.com'
        
        try:
            while True:
                line = await asyncio.wait_for(
                    proc.stderr.readline(), 
                    timeout=timeout
                )
                line = line.decode('utf-8', errors='ignore')
                
                match = re.search(pattern, line)
                if match:
                    return match.group(0)
                
                if "failed" in line.lower() or "error" in line.lower():
                    raise Exception(f"Cloudflare error: {line}")
                    
        except asyncio.TimeoutError:
            proc.terminate()
            raise Exception("Timeout waiting for Cloudflare URL")
    
    async def _start_ngrok(self) -> Dict:
        """Start Ngrok tunnel"""
        logger.info("Starting Ngrok tunnel...")
        
        proc = await asyncio.create_subprocess_exec(
            "ngrok", "http", "8000", "--log=stdout",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait a bit for ngrok to start
        await asyncio.sleep(3)
        
        # Get URL from ngrok API
        url = await self._get_ngrok_url()
        
        self.current_tunnel = TunnelInfo(
            service="ngrok",
            url=url,
            process=proc
        )
        
        logger.info(f"Ngrok tunnel started: {url}")
        return {"service": "ngrok", "url": url}
    
    async def _get_ngrok_url(self) -> str:
        """Get ngrok URL from local API"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:4040/api/tunnels") as resp:
                    data = await resp.json()
                    tunnels = data.get("tunnels", [])
                    if tunnels:
                        return tunnels[0]["public_url"]
        except Exception as e:
            raise Exception(f"Failed to get ngrok URL: {e}")
        
        raise Exception("No ngrok tunnels found")
    
    async def _start_localtunnel(self) -> Dict:
        """Start LocalTunnel"""
        logger.info("Starting LocalTunnel...")
        
        proc = await asyncio.create_subprocess_exec(
            "npx", "localtunnel", "--port", "8000",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        url = await self._extract_localtunnel_url(proc)
        
        self.current_tunnel = TunnelInfo(
            service="localtunnel",
            url=url,
            process=proc
        )
        
        logger.info(f"LocalTunnel started: {url}")
        return {"service": "localtunnel", "url": url}
    
    async def _extract_localtunnel_url(self, proc: asyncio.subprocess.Process,
                                        timeout: int = 30) -> str:
        """Extract URL from localtunnel output"""
        pattern = r'https://[a-zA-Z0-9-]+\.loca\.lt'
        
        try:
            while True:
                line = await asyncio.wait_for(
                    proc.stdout.readline(),
                    timeout=timeout
                )
                line = line.decode('utf-8', errors='ignore')
                
                match = re.search(pattern, line)
                if match:
                    return match.group(0)
                    
        except asyncio.TimeoutError:
            proc.terminate()
            raise Exception("Timeout waiting for LocalTunnel URL")
    
    async def stop_tunnel(self):
        """Stop active tunnel"""
        if self.current_tunnel and self.current_tunnel.process:
            self.current_tunnel.process.terminate()
            try:
                await asyncio.wait_for(
                    self.current_tunnel.process.wait(), 
                    timeout=5
                )
            except asyncio.TimeoutError:
                self.current_tunnel.process.kill()
            
            logger.info(f"Tunnel stopped: {self.current_tunnel.url}")
            self.current_tunnel = None
    
    def get_status(self) -> Dict:
        """Get current tunnel status"""
        if not self.current_tunnel:
            return {"active": False, "service": None, "url": None}
        
        return {
            "active": True,
            "service": self.current_tunnel.service,
            "url": self.current_tunnel.url
        }
    
    async def restart_tunnel(self) -> Dict:
        """Restart tunnel"""
        await self.stop_tunnel()
        return await self.start_tunnel()
