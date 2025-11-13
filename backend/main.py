from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import os
from pathlib import Path

from .minecraft_manager import MinecraftManager
from .models import ServerStatus, ServerConfig, BackupInfo

app = FastAPI(title="CraftServer Manager", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Minecraft Manager
mc_manager = MinecraftManager()

# Mount static files
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    index_file = frontend_path / "index.html"
    return FileResponse(str(index_file))


@app.get("/api/status")
async def get_status() -> ServerStatus:
    """Get current server status"""
    return mc_manager.get_status()


@app.post("/api/server/start")
async def start_server():
    """Start the Minecraft server"""
    try:
        await mc_manager.start_server()
        return {"status": "success", "message": "Server starting..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/server/stop")
async def stop_server():
    """Stop the Minecraft server"""
    try:
        await mc_manager.stop_server()
        return {"status": "success", "message": "Server stopping..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/server/restart")
async def restart_server():
    """Restart the Minecraft server"""
    try:
        await mc_manager.restart_server()
        return {"status": "success", "message": "Server restarting..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/server/command")
async def send_command(command: dict):
    """Send command to Minecraft server console"""
    try:
        cmd = command.get("command", "")
        await mc_manager.send_command(cmd)
        return {"status": "success", "message": f"Command sent: {cmd}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config() -> ServerConfig:
    """Get server configuration"""
    return mc_manager.get_config()


@app.post("/api/config")
async def update_config(config: ServerConfig):
    """Update server configuration"""
    try:
        mc_manager.update_config(config)
        return {"status": "success", "message": "Configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backups")
async def list_backups() -> List[BackupInfo]:
    """List all available backups"""
    return mc_manager.list_backups()


@app.post("/api/backup")
async def create_backup():
    """Create a new backup"""
    try:
        backup_name = await mc_manager.create_backup()
        return {"status": "success", "message": "Backup created", "backup": backup_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/backup/restore")
async def restore_backup(backup: dict):
    """Restore from a backup"""
    try:
        backup_name = backup.get("name", "")
        await mc_manager.restore_backup(backup_name)
        return {"status": "success", "message": f"Restored from backup: {backup_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/console")
async def websocket_console(websocket: WebSocket):
    """WebSocket endpoint for real-time console logs"""
    await websocket.accept()
    try:
        # Start sending console logs
        async for log_line in mc_manager.stream_console_logs():
            await websocket.send_text(log_line)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    await mc_manager.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await mc_manager.cleanup()
