from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


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
    tps: float = 20.0  # Ticks per second


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
    gamemode: Optional[str] = None
    health: Optional[float] = None
    food_level: Optional[int] = None
    level: Optional[int] = None
    location: Optional[Dict[str, Any]] = None


class PlayerAction(str, Enum):
    """Player action types"""
    KICK = "kick"
    BAN = "ban"
    UNBAN = "unban"
    OP = "op"
    DEOP = "deop"
    WHITELIST_ADD = "whitelist_add"
    WHITELIST_REMOVE = "whitelist_remove"
    TELEPORT = "teleport"
    GAMEMODE = "gamemode"


class ItemStack(BaseModel):
    """Item stack model"""
    material: str
    amount: int
    slot: int
    display_name: Optional[str] = None
    enchantments: Optional[List[str]] = None


class PlayerInventory(BaseModel):
    """Player inventory model"""
    player_name: str
    items: List[ItemStack]


class WorldInfo(BaseModel):
    """World information model"""
    name: str
    size: int  # bytes
    last_modified: datetime
    seed: Optional[str] = None
    spawn_location: Optional[Dict[str, Any]] = None


class ScheduledTask(BaseModel):
    """Scheduled task model"""
    id: str
    name: str
    task_type: str  # backup, restart, command
    schedule: str  # cron format
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    params: Optional[Dict[str, Any]] = None


class FileEntry(BaseModel):
    """File entry model for file manager"""
    name: str
    path: str
    is_directory: bool
    size: int
    modified: datetime
    permissions: Optional[str] = None


class ModrinthProject(BaseModel):
    """Modrinth project model"""
    id: str
    slug: str
    title: str
    description: str
    categories: List[str]
    project_type: str  # mod, plugin, datapack
    downloads: int
    icon_url: Optional[str] = None
    author: str
    versions: Optional[List[str]] = None


class ModrinthVersion(BaseModel):
    """Modrinth version model"""
    id: str
    project_id: str
    name: str
    version_number: str
    game_versions: List[str]
    loaders: List[str]
    files: List[Dict[str, Any]]
    downloads: int
    date_published: str


class InstalledMod(BaseModel):
    """Installed mod/plugin/datapack model"""
    filename: str
    project_id: Optional[str] = None
    version_id: Optional[str] = None
    name: str
    type: str  # mod, plugin, datapack
    size: int
    installed_date: datetime
