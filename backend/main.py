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
from .server_manager import ServerManager
from .models import (
    ServerStatus, ServerConfig, BackupInfo, Player, PlayerInventory,
    WorldInfo, ScheduledTask, FileEntry, PlayerAction, ModrinthProject,
    ModrinthVersion, InstalledMod
)

app = FastAPI(title="CraftServer Manager", version="2.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Server Manager (manages multiple Minecraft servers)
server_manager = ServerManager()


# Helper function to get current manager
async def get_current_manager(server_id: Optional[str] = None) -> MinecraftManager:
    """Get the MinecraftManager for the specified or current server"""
    manager = await server_manager.get_manager(server_id)
    if manager is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return manager

# Mount static files
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    index_file = frontend_path / "index.html"
    return FileResponse(str(index_file))


# Server Management Endpoints
@app.get("/api/servers")
async def list_servers():
    """List all servers"""
    try:
        servers = server_manager.list_servers()
        current_id = server_manager.get_current_server_id()
        return {
            "servers": servers,
            "current_server_id": current_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/servers/{server_id}")
async def get_server(server_id: str):
    """Get server information"""
    try:
        server = server_manager.get_server_info(server_id)
        if server is None:
            raise HTTPException(status_code=404, detail="Server not found")
        return server
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/servers")
async def create_server(server_data: dict):
    """Create a new server"""
    try:
        name = server_data.get("name", "New Server")
        port = server_data.get("port")
        minecraft_version = server_data.get("minecraft_version", "1.20.1")
        server_type = server_data.get("server_type", "vanilla")

        server = await server_manager.create_server(
            name=name,
            port=port,
            minecraft_version=minecraft_version,
            server_type=server_type
        )
        return {"status": "success", "server": server}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/servers/{server_id}")
async def delete_server(server_id: str):
    """Delete a server"""
    try:
        success = await server_manager.delete_server(server_id)
        if not success:
            raise HTTPException(status_code=404, detail="Server not found")
        return {"status": "success", "message": "Server deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/servers/{server_id}/select")
async def select_server(server_id: str):
    """Select a server as the current active server"""
    try:
        success = server_manager.set_current_server(server_id)
        if not success:
            raise HTTPException(status_code=404, detail="Server not found")
        return {"status": "success", "current_server_id": server_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/servers/{server_id}")
async def update_server(server_id: str, update_data: dict):
    """Update server information"""
    try:
        name = update_data.get("name")
        port = update_data.get("port")

        success = await server_manager.update_server_info(
            server_id=server_id,
            name=name,
            port=port
        )
        if not success:
            raise HTTPException(status_code=404, detail="Server not found")
        return {"status": "success", "message": "Server updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status(server_id: Optional[str] = None) -> ServerStatus:
    """Get current server status"""
    manager = await get_current_manager(server_id)
    return manager.get_status()


@app.post("/api/server/start")
async def start_server(server_id: Optional[str] = None):
    """Start the Minecraft server"""
    try:
        manager = await get_current_manager(server_id)
        await manager.start_server()
        return {"status": "success", "message": "Server starting..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/server/stop")
async def stop_server(server_id: Optional[str] = None):
    """Stop the Minecraft server"""
    try:
        manager = await get_current_manager(server_id)
        await manager.stop_server()
        return {"status": "success", "message": "Server stopping..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/server/restart")
async def restart_server(server_id: Optional[str] = None):
    """Restart the Minecraft server"""
    try:
        manager = await get_current_manager(server_id)
        await manager.restart_server()
        return {"status": "success", "message": "Server restarting..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/server/command")
async def send_command(command: dict, server_id: Optional[str] = None):
    """Send command to Minecraft server console"""
    try:
        manager = await get_current_manager(server_id)
        cmd = command.get("command", "")
        await manager.send_command(cmd)
        return {"status": "success", "message": f"Command sent: {cmd}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config")
async def get_config(server_id: Optional[str] = None) -> ServerConfig:
    """Get server configuration"""
    manager = await get_current_manager(server_id)
    return manager.get_config()


@app.post("/api/config")
async def update_config(config: ServerConfig, server_id: Optional[str] = None):
    """Update server configuration"""
    try:
        manager = await get_current_manager(server_id)
        manager.update_config(config)
        return {"status": "success", "message": "Configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backups")
async def list_backups(server_id: Optional[str] = None) -> List[BackupInfo]:
    """List all available backups"""
    manager = await get_current_manager(server_id)
    return manager.list_backups()


@app.post("/api/backup")
async def create_backup(server_id: Optional[str] = None):
    """Create a new backup"""
    try:
        manager = await get_current_manager(server_id)
        backup_name = await manager.create_backup()
        return {"status": "success", "message": "Backup created", "backup": backup_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/backup/restore")
async def restore_backup(backup: dict, server_id: Optional[str] = None):
    """Restore from a backup"""
    try:
        manager = await get_current_manager(server_id)
        backup_name = backup.get("name", "")
        await manager.restore_backup(backup_name)
        return {"status": "success", "message": f"Restored from backup: {backup_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/console")
async def websocket_console(websocket: WebSocket, server_id: Optional[str] = None):
    """WebSocket endpoint for real-time console logs"""
    await websocket.accept()
    try:
        manager = await get_current_manager(server_id)
        # Start sending console logs
        async for log_line in manager.stream_console_logs():
            await websocket.send_text(log_line)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


# Performance Profiler Endpoints
@app.get("/api/profiler/metrics")
async def get_profiler_metrics(server_id: Optional[str] = None):
    """Get current performance metrics"""
    try:
        manager = await get_current_manager(server_id)
        return manager.get_profiler_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profiler/history")
async def get_profiler_history(duration: int = 60, server_id: Optional[str] = None):
    """Get performance history"""
    try:
        manager = await get_current_manager(server_id)
        return manager.get_profiler_history(duration)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profiler/statistics")
async def get_profiler_statistics(server_id: Optional[str] = None):
    """Get performance statistics"""
    try:
        manager = await get_current_manager(server_id)
        return manager.get_profiler_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/profiler/alerts")
async def get_profiler_alerts(server_id: Optional[str] = None):
    """Get performance alerts"""
    try:
        manager = await get_current_manager(server_id)
        return manager.get_profiler_alerts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/profiler")
async def websocket_profiler(websocket: WebSocket, server_id: Optional[str] = None):
    """WebSocket endpoint for real-time performance metrics"""
    await websocket.accept()
    try:
        manager = await get_current_manager(server_id)
        # Send performance metrics in real-time
        async for metrics in manager.stream_profiler_metrics():
            import json
            await websocket.send_text(json.dumps(metrics))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    # Server manager is already initialized
    # Individual servers are loaded lazily as needed
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await server_manager.cleanup()


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


# Multi-Source Endpoints
@app.get("/api/projects/search")
async def search_projects(
    query: str,
    source: str = "modrinth",  # modrinth, curseforge, spigot, all
    project_type: Optional[str] = None
) -> List[ModrinthProject]:
    """Search for mods/plugins/datapacks from multiple sources"""
    try:
        return await mc_manager.search_projects(query, source, project_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Modrinth Endpoints (kept for backwards compatibility)
@app.get("/api/modrinth/search")
async def search_modrinth(
    query: str,
    project_type: Optional[str] = None,
    source: str = "modrinth"  # Added source parameter
) -> List[ModrinthProject]:
    """Search for mods/plugins/datapacks"""
    try:
        return await mc_manager.search_projects(query, source, project_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/modrinth/project/{project_id}/versions")
async def get_project_versions(
    project_id: str,
    loader: Optional[str] = None
) -> List[ModrinthVersion]:
    """Get versions for a Modrinth project"""
    try:
        return await mc_manager.get_project_versions(project_id, loader)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/modrinth/install")
async def install_from_modrinth(install_data: dict):
    """Install a mod/plugin/datapack from Modrinth"""
    try:
        version_id = install_data.get("version_id")
        install_type = install_data.get("type", "mods")

        installed = await mc_manager.install_from_modrinth(version_id, install_type)
        return {
            "status": "success",
            "message": f"Installed {installed.name}",
            "installed": installed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/modrinth/installed/{mod_type}")
async def list_installed_mods(mod_type: str) -> List[InstalledMod]:
    """List installed mods/plugins/datapacks"""
    try:
        return await mc_manager.list_installed_mods(mod_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/modrinth/installed/{mod_type}/{filename}")
async def uninstall_mod(mod_type: str, filename: str):
    """Uninstall a mod/plugin/datapack"""
    try:
        success = await mc_manager.uninstall_mod(filename, mod_type)
        if success:
            return {"status": "success", "message": f"Uninstalled {filename}"}
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/modrinth/create-modpack-server")
async def create_modpack_server(modpack_data: dict):
    """Create a new server from a Modrinth modpack"""
    try:
        version_id = modpack_data.get("version_id")
        server_name = modpack_data.get("server_name", "Modpack Server")
        memory = modpack_data.get("memory", "4G")

        if not version_id:
            raise HTTPException(status_code=400, detail="version_id is required")

        result = await mc_manager.create_modpack_server(version_id, server_name, memory)
        return {
            "status": "success",
            "message": "Modpack server created successfully",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Java Management Endpoints
@app.get("/api/java/info")
async def get_java_info(server_id: Optional[str] = None):
    """Get information about installed Java versions"""
    try:
        manager = await get_current_manager(server_id)
        return manager.java_manager.get_java_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/java/required/{minecraft_version}")
async def get_required_java_version(minecraft_version: str, server_id: Optional[str] = None):
    """Get the required Java version for a Minecraft version"""
    try:
        manager = await get_current_manager(server_id)
        version = manager.java_manager.get_required_java_version(minecraft_version)
        is_installed = await manager.java_manager.is_java_installed(version)
        java_path = manager.java_manager.get_java_path(version)

        return {
            "minecraft_version": minecraft_version,
            "required_java_version": version,
            "is_installed": is_installed,
            "java_path": str(java_path) if java_path else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/java/install/{version}")
async def install_java(version: int, server_id: Optional[str] = None):
    """Install a specific Java version"""
    try:
        manager = await get_current_manager(server_id)

        # Check if already installed
        if await manager.java_manager.is_java_installed(version):
            return {
                "status": "success",
                "message": f"Java {version} is already installed",
                "already_installed": True
            }

        # Install Java
        success, message = await manager.java_manager.install_java(version)

        if success:
            return {
                "status": "success",
                "message": message,
                "version": version,
                "java_path": str(manager.java_manager.get_java_path(version))
            }
        else:
            raise HTTPException(status_code=500, detail=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/java/auto-install")
async def auto_install_java(install_data: dict, server_id: Optional[str] = None):
    """Automatically install the required Java version for a Minecraft version"""
    try:
        manager = await get_current_manager(server_id)
        minecraft_version = install_data.get("minecraft_version")

        if not minecraft_version:
            raise HTTPException(status_code=400, detail="minecraft_version is required")

        success, message, java_version = await manager.java_manager.auto_install_for_minecraft(
            minecraft_version
        )

        if success:
            return {
                "status": "success",
                "message": message,
                "minecraft_version": minecraft_version,
                "java_version": java_version,
                "java_path": str(manager.java_manager.get_java_path(java_version))
            }
        else:
            raise HTTPException(status_code=500, detail=message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/java/install/{version}")
async def websocket_java_install(websocket: WebSocket, version: int, server_id: Optional[str] = None):
    """WebSocket endpoint for Java installation with progress updates"""
    await websocket.accept()
    try:
        manager = await get_current_manager(server_id)

        async def progress_callback(progress: float, status: str):
            await websocket.send_json({
                "progress": progress,
                "status": status
            })

        success = await manager.java_manager.download_java(version, progress_callback)

        if success:
            await websocket.send_json({
                "progress": 100,
                "status": "completed",
                "message": f"Java {version} installed successfully"
            })
        else:
            await websocket.send_json({
                "progress": 0,
                "status": "failed",
                "message": f"Failed to install Java {version}"
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "progress": 0,
            "status": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()


@app.delete("/api/java/version/{version}")
async def delete_java_version(version: int, server_id: Optional[str] = None):
    """Delete a specific Java version"""
    try:
        manager = await get_current_manager(server_id)
        java_dir = manager.java_manager.java_base_dir / f"jdk-{version}"

        if not java_dir.exists():
            raise HTTPException(status_code=404, detail=f"Java {version} is not installed")

        shutil.rmtree(java_dir)

        return {
            "status": "success",
            "message": f"Java {version} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
