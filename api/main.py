"""
ReconX FastAPI Application
Main entry point for the API server
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from api.database import DatabaseManager, db, get_db
from api.tasks import TaskQueue, ScanTask
from api.state_manager import StateManager
from api.resilience_manager import ResilienceManager
from api.tunnel_manager import TunnelManager
from api.llm_integration import LLMManager
from api.notifications import NotificationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global managers
task_queue: Optional[TaskQueue] = None
state_manager: Optional[StateManager] = None
resilience_manager: Optional[ResilienceManager] = None
tunnel_manager: Optional[TunnelManager] = None
llm_manager: Optional[LLMManager] = None
notification_manager: Optional[NotificationManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global task_queue, state_manager, resilience_manager, tunnel_manager, llm_manager, notification_manager
    
    # Startup
    logger.info("🚀 Starting ReconX API...")
    
    # Initialize database
    await db.connect()
    logger.info("✅ Database connected")
    
    # Initialize managers
    task_queue = TaskQueue(db)
    state_manager = StateManager(db)
    resilience_manager = ResilienceManager(db, task_queue)
    tunnel_manager = TunnelManager()
    llm_manager = LLMManager()
    notification_manager = NotificationManager()
    
    # Start background tasks
    asyncio.create_task(resilience_manager.monitor_loop())
    asyncio.create_task(task_queue.process_loop())
    
    logger.info("✅ All managers initialized")
    logger.info(f"🌐 API available at http://0.0.0.0:8000")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down ReconX API...")
    await db.disconnect()
    logger.info("✅ Database disconnected")

app = FastAPI(
    title="ReconX API",
    description="Termux-Optimized Bug Bounty Automation Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="web"), name="static")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

# REST API Endpoints

@app.get("/")
async def root():
    return {"message": "ReconX API", "version": "1.0.0", "status": "running"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",
        "llm_status": llm_manager.current_model if llm_manager else "unknown"
    }

# Target endpoints
@app.get("/api/targets")
async def get_targets():
    """Get all targets"""
    targets = await db.get_all_targets()
    return {"targets": targets}

@app.post("/api/targets")
async def create_target(target_data: dict):
    """Create new target"""
    try:
        target_id = await db.create_target(target_data)
        return {"id": target_id, "message": "Target created successfully"}
    except Exception as e:
        logger.error(f"Error creating target: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/targets/{target_id}")
async def get_target(target_id: str):
    """Get target by ID"""
    target = await db.get_target(target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target

@app.delete("/api/targets/{target_id}")
async def delete_target(target_id: str):
    """Delete target"""
    # Implementation needed
    return {"message": "Target deleted"}

# Scan endpoints
@app.get("/api/scans")
async def get_scans():
    """Get all scans"""
    # Implementation: get all scans from DB
    return {"scans": []}

@app.post("/api/scans")
async def create_scan(scan_data: dict, background_tasks: BackgroundTasks):
    """Start new scan"""
    try:
        scan_id = await db.create_scan(scan_data)
        
        # Add to task queue
        task = ScanTask(
            scan_id=scan_id,
            target_id=scan_data['target_id'],
            config=scan_data.get('config', {})
        )
        await task_queue.add_task(task)
        
        # Notify
        await notification_manager.send_notification(
            title="Scan Started",
            message=f"New scan started for target {scan_data.get('target_id')}",
            severity="info"
        )
        
        return {"id": scan_id, "message": "Scan created and queued"}
    except Exception as e:
        logger.error(f"Error creating scan: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/scans/{scan_id}")
async def get_scan(scan_id: str):
    """Get scan status"""
    scan = await db.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan

@app.post("/api/scans/{scan_id}/pause")
async def pause_scan(scan_id: str):
    """Pause scan"""
    await task_queue.pause_task(scan_id)
    await db.update_scan_status(scan_id, "paused")
    return {"message": "Scan paused"}

@app.post("/api/scans/{scan_id}/resume")
async def resume_scan(scan_id: str):
    """Resume scan"""
    await task_queue.resume_task(scan_id)
    await db.update_scan_status(scan_id, "running")
    return {"message": "Scan resumed"}

@app.post("/api/scans/{scan_id}/stop")
async def stop_scan(scan_id: str):
    """Stop scan"""
    await task_queue.stop_task(scan_id)
    await db.update_scan_status(scan_id, "failed", error_message="Stopped by user")
    return {"message": "Scan stopped"}

# Results endpoints
@app.get("/api/scans/{scan_id}/subdomains")
async def get_scan_subdomains(scan_id: str):
    """Get subdomains for scan"""
    subdomains = await db.get_subdomains(scan_id)
    return {"subdomains": subdomains}

@app.get("/api/scans/{scan_id}/vulnerabilities")
async def get_scan_vulnerabilities(scan_id: str, severity: Optional[str] = None):
    """Get vulnerabilities for scan"""
    vulnerabilities = await db.get_vulnerabilities(scan_id, severity)
    return {"vulnerabilities": vulnerabilities}

# System endpoints
@app.get("/api/system/status")
async def get_system_status():
    """Get current system status"""
    state = await db.get_system_state()
    return state or {"status": "unknown"}

@app.post("/api/system/pause")
async def system_pause(reason: str = "manual"):
    """System-wide pause (network loss)"""
    await resilience_manager.trigger_pause(reason)
    return {"message": f"System paused: {reason}"}

@app.post("/api/system/resume")
async def system_resume():
    """System-wide resume"""
    await resilience_manager.trigger_resume()
    return {"message": "System resumed"}

# Tunnel endpoints
@app.post("/api/tunnel/start")
async def start_tunnel():
    """Start tunnel manually"""
    try:
        tunnel_info = await tunnel_manager.start_tunnel()
        await db.update_system_state({
            "tunnel_url": tunnel_info["url"],
            "tunnel_service": tunnel_info["service"]
        })
        return tunnel_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tunnel/stop")
async def stop_tunnel():
    """Stop tunnel"""
    await tunnel_manager.stop_tunnel()
    return {"message": "Tunnel stopped"}

@app.get("/api/tunnel/status")
async def get_tunnel_status():
    """Get tunnel status"""
    return tunnel_manager.get_status()

# LLM endpoints
@app.get("/api/llm/status")
async def get_llm_status():
    """Get LLM status"""
    return {
        "current_model": llm_manager.current_model if llm_manager else None,
        "loaded": llm_manager.is_loaded if llm_manager else False,
        "memory_usage": llm_manager.get_memory_usage() if llm_manager else None
    }

@app.post("/api/llm/switch")
async def switch_llm_model(model: str):
    """Switch LLM model"""
    try:
        await llm_manager.switch_model(model)
        return {"message": f"Switched to {model}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/llm/unload")
async def unload_llm():
    """Unload LLM to free memory"""
    await llm_manager.unload_model()
    return {"message": "LLM unloaded"}

# WebSocket endpoints
@app.websocket("/ws/scans/{scan_id}")
async def websocket_scan(websocket: WebSocket, scan_id: str):
    """WebSocket for real-time scan updates"""
    await manager.connect(websocket, f"scan_{scan_id}")
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            await websocket.send_json({"type": "ping", "scan_id": scan_id})
    except WebSocketDisconnect:
        manager.disconnect(f"scan_{scan_id}")

@app.websocket("/ws/system")
async def websocket_system(websocket: WebSocket):
    """WebSocket for system health updates"""
    await manager.connect(websocket, "system")
    try:
        while True:
            state = await db.get_system_state()
            await websocket.send_json({
                "type": "system_status",
                "data": state or {}
            })
            await asyncio.sleep(10)  # Send updates every 10 seconds
    except WebSocketDisconnect:
        manager.disconnect("system")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
