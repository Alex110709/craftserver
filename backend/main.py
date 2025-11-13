from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import os
from pathlib import Path

from .minecraft_manager import MinecraftManager
from .models import (
    ServerStatus, ServerConfig, BackupInfo, Player, PlayerInventory,
    WorldInfo, ScheduledTask, FileEntry, PlayerAction
)

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


# Player Management Endpoints
@app.get("/api/players")
async def get_players() -> List[Player]:
    """Get list of all players"""
    try:
        return await mc_manager.get_players()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/players/online")
async def get_online_players() -> List[Player]:
    """Get list of online players"""
    try:
        return await mc_manager.get_online_players()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/players/{player_name}/action")
async def perform_player_action(player_name: str, action_data: dict):
    """Perform action on player"""
    try:
        action = PlayerAction(action_data.get("action"))
        params = action_data.get("params", {})
        await mc_manager.player_action(player_name, action, params)
        return {"status": "success", "message": f"Action {action.value} performed on {player_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/players/{player_name}/inventory")
async def get_player_inventory(player_name: str) -> Optional[PlayerInventory]:
    """Get player inventory"""
    try:
        inventory = await mc_manager.get_player_inventory(player_name)
        if not inventory:
            raise HTTPException(status_code=404, detail="Player not found")
        return inventory
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/players/{player_name}/give")
async def give_item_to_player(player_name: str, item_data: dict):
    """Give item to player"""
    try:
        item = item_data.get("item", "")
        amount = item_data.get("amount", 1)
        await mc_manager.give_item(player_name, item, amount)
        return {"status": "success", "message": f"Gave {amount} {item} to {player_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/players/{player_name}/clear")
async def clear_player_inventory(player_name: str):
    """Clear player inventory"""
    try:
        await mc_manager.clear_inventory(player_name)
        return {"status": "success", "message": f"Cleared inventory for {player_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# World Management Endpoints
@app.get("/api/worlds")
async def get_worlds() -> List[WorldInfo]:
    """Get list of worlds"""
    try:
        return await mc_manager.get_worlds()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/worlds/{world_name}")
async def delete_world(world_name: str):
    """Delete a world"""
    try:
        await mc_manager.delete_world(world_name)
        return {"status": "success", "message": f"Deleted world: {world_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/worlds/{world_name}/reset")
async def reset_world(world_name: str):
    """Reset a world"""
    try:
        await mc_manager.reset_world(world_name)
        return {"status": "success", "message": f"Reset world: {world_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Scheduled Tasks Endpoints
@app.get("/api/tasks")
async def get_tasks() -> List[ScheduledTask]:
    """Get all scheduled tasks"""
    try:
        return await mc_manager.get_scheduled_tasks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks")
async def create_task(task: ScheduledTask):
    """Create a new scheduled task"""
    try:
        created_task = await mc_manager.create_scheduled_task(task)
        return {"status": "success", "message": "Task created", "task": created_task}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, task: ScheduledTask):
    """Update a scheduled task"""
    try:
        await mc_manager.update_scheduled_task(task_id, task)
        return {"status": "success", "message": "Task updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a scheduled task"""
    try:
        await mc_manager.delete_scheduled_task(task_id)
        return {"status": "success", "message": "Task deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# File Manager Endpoints
@app.get("/api/files")
async def list_files(path: str = "") -> List[FileEntry]:
    """List files in a directory"""
    try:
        return await mc_manager.list_files(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files/read", response_class=PlainTextResponse)
async def read_file(path: str):
    """Read file content"""
    try:
        content = await mc_manager.read_file(path)
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/write")
async def write_file(file_data: dict):
    """Write file content"""
    try:
        path = file_data.get("path", "")
        content = file_data.get("content", "")
        await mc_manager.write_file(path, content)
        return {"status": "success", "message": "File saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/files")
async def delete_file(path: str):
    """Delete a file"""
    try:
        await mc_manager.delete_file(path)
        return {"status": "success", "message": "File deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
