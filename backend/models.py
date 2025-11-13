from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ServerStatus(BaseModel):
    """Server status model"""
    is_running: bool
    uptime: Optional[int] = None  # seconds
    player_count: int = 0
    max_players: int = 20
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_total: float = 0.0
    version: Optional[str] = None


class ServerConfig(BaseModel):
    """Server configuration model"""
    server_name: str = "CraftServer"
    max_players: int = 20
    gamemode: str = "survival"
    difficulty: str = "normal"
    pvp: bool = True
    online_mode: bool = True
    motd: str = "A Minecraft Server"
    view_distance: int = 10
    spawn_protection: int = 16
    memory: str = "2G"
    minecraft_version: str = "1.20.1"


class BackupInfo(BaseModel):
    """Backup information model"""
    name: str
    created_at: datetime
    size: int  # bytes
    path: str


class Player(BaseModel):
    """Player information model"""
    uuid: str
    name: str
    online: bool
    last_seen: Optional[datetime] = None
