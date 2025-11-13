import asyncio
import os
import shutil
import psutil
import re
import uuid as uuid_module
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, AsyncIterator, Dict, Any
import subprocess
import time
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .models import (
    ServerStatus, ServerConfig, BackupInfo, Player, PlayerInventory,
    ItemStack, WorldInfo, ScheduledTask, FileEntry, PlayerAction,
    ModrinthProject, ModrinthVersion, InstalledMod
)
from .modrinth_client import ModrinthClient
from .curseforge_client import CurseForgeClient
from .spigot_client import SpigotClient
from .profiler import PerformanceProfiler


class MinecraftManager:
    """Manager for Minecraft server operations"""

    def __init__(self):
        self.minecraft_dir = Path("/app/minecraft")
        self.backups_dir = Path("/app/backups")
        self.logs_dir = Path("/app/logs")
        self.server_process: Optional[subprocess.Popen] = None
        self.start_time: Optional[float] = None
        self.config: ServerConfig = ServerConfig()
        self.log_file = self.logs_dir / "server.log"
        self.players_cache: List[Player] = []
        self.scheduler = AsyncIOScheduler()
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.modrinth_client = ModrinthClient()
        self.curseforge_client = CurseForgeClient()
        self.spigot_client = SpigotClient()
        self.profiler = PerformanceProfiler()

    async def initialize(self):
        """Initialize the manager"""
        # Create directories
        self.minecraft_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.minecraft_dir / "world").mkdir(exist_ok=True)
        (self.minecraft_dir / "plugins").mkdir(exist_ok=True)

        # Download server jar if not exists
        server_jar = self.minecraft_dir / "server.jar"
        if not server_jar.exists():
            await self._download_server_jar()

        # Create/load server properties
        self._load_config()

        # Start scheduler
        self.scheduler.start()
        self._load_scheduled_tasks()

        # Initialize and start profiler
        await self.profiler.initialize()
        await self.profiler.start_monitoring()

    async def _download_server_jar(self):
        """Download Minecraft server jar"""
        version = os.getenv("MINECRAFT_VERSION", "1.20.1")
        server_jar = self.minecraft_dir / "server.jar"

        # For simplicity, using a direct download URL
        # In production, use proper version manifest API
        download_url = f"https://piston-data.mojang.com/v1/objects/84194a2f286ef7c14ed60ce89ce1502b2e1e6e6/server.jar"

        print(f"Downloading Minecraft server {version}...")

        # Create a placeholder for now
        # In production, implement actual download
        server_jar.touch()

    def _load_config(self):
        """Load server configuration from server.properties"""
        props_file = self.minecraft_dir / "server.properties"
        if props_file.exists():
            # Parse server.properties
            with open(props_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            if key == 'max-players':
                                self.config.max_players = int(value)
                            elif key == 'gamemode':
                                self.config.gamemode = value
                            elif key == 'difficulty':
                                self.config.difficulty = value
                            elif key == 'pvp':
                                self.config.pvp = value.lower() == 'true'
                            elif key == 'motd':
                                self.config.motd = value
                            elif key == 'view-distance':
                                self.config.view_distance = int(value)

    def _save_config(self):
        """Save server configuration to server.properties"""
        props_file = self.minecraft_dir / "server.properties"

        properties = {
            'server-name': self.config.server_name,
            'max-players': self.config.max_players,
            'gamemode': self.config.gamemode,
            'difficulty': self.config.difficulty,
            'pvp': str(self.config.pvp).lower(),
            'online-mode': str(self.config.online_mode).lower(),
            'motd': self.config.motd,
            'view-distance': self.config.view_distance,
            'spawn-protection': self.config.spawn_protection,
            'server-port': '25565',
        }

        with open(props_file, 'w') as f:
            f.write("# Minecraft server properties\n")
            for key, value in properties.items():
                f.write(f"{key}={value}\n")

    async def start_server(self):
        """Start the Minecraft server"""
        if self.is_running():
            raise Exception("Server is already running")

        # Accept EULA
        eula_file = self.minecraft_dir / "eula.txt"
        with open(eula_file, 'w') as f:
            f.write("eula=true\n")

        # Save config
        self._save_config()

        # Prepare command
        memory = os.getenv("SERVER_MEMORY", self.config.memory)
        cmd = [
            "java",
            f"-Xmx{memory}",
            f"-Xms{memory}",
            "-jar",
            "server.jar",
            "nogui"
        ]

        # Start server process
        self.server_process = subprocess.Popen(
            cmd,
            cwd=str(self.minecraft_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True
        )

        self.start_time = time.time()

        # Start log monitoring
        asyncio.create_task(self._monitor_logs())

    async def stop_server(self):
        """Stop the Minecraft server"""
        if not self.is_running():
            raise Exception("Server is not running")

        # Send stop command
        await self.send_command("stop")

        # Wait for graceful shutdown
        try:
            self.server_process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.server_process.kill()

        self.server_process = None
        self.start_time = None

    async def restart_server(self):
        """Restart the Minecraft server"""
        if self.is_running():
            await self.stop_server()
        await asyncio.sleep(2)
        await self.start_server()

    async def send_command(self, command: str):
        """Send command to server console"""
        if not self.is_running():
            raise Exception("Server is not running")

        self.server_process.stdin.write(f"{command}\n")
        self.server_process.stdin.flush()

    def is_running(self) -> bool:
        """Check if server is running"""
        if self.server_process is None:
            return False
        return self.server_process.poll() is None

    def get_status(self) -> ServerStatus:
        """Get current server status"""
        status = ServerStatus(
            is_running=self.is_running(),
            max_players=self.config.max_players,
            version=self.config.minecraft_version
        )

        if self.is_running() and self.start_time:
            status.uptime = int(time.time() - self.start_time)

            # Get CPU and memory usage
            try:
                process = psutil.Process(self.server_process.pid)
                status.cpu_usage = process.cpu_percent()
                memory_info = process.memory_info()
                status.memory_usage = memory_info.rss / (1024 * 1024)  # MB
                status.memory_total = psutil.virtual_memory().total / (1024 * 1024)  # MB
            except:
                pass

        return status

    def get_config(self) -> ServerConfig:
        """Get server configuration"""
        return self.config

    def update_config(self, config: ServerConfig):
        """Update server configuration"""
        self.config = config
        self._save_config()

    async def create_backup(self) -> str:
        """Create a backup of the server"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = self.backups_dir / backup_name

        # Create backup
        shutil.copytree(
            self.minecraft_dir,
            backup_path,
            ignore=shutil.ignore_patterns('*.log', 'logs')
        )

        return backup_name

    async def restore_backup(self, backup_name: str):
        """Restore from a backup"""
        backup_path = self.backups_dir / backup_name

        if not backup_path.exists():
            raise Exception(f"Backup not found: {backup_name}")

        # Stop server if running
        was_running = self.is_running()
        if was_running:
            await self.stop_server()

        # Clear current server files (except logs)
        for item in self.minecraft_dir.iterdir():
            if item.name != 'logs':
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        # Restore backup
        shutil.copytree(backup_path, self.minecraft_dir, dirs_exist_ok=True)

        # Restart server if it was running
        if was_running:
            await self.start_server()

    def list_backups(self) -> List[BackupInfo]:
        """List all backups"""
        backups = []

        for backup_dir in self.backups_dir.iterdir():
            if backup_dir.is_dir():
                stat = backup_dir.stat()
                size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())

                backups.append(BackupInfo(
                    name=backup_dir.name,
                    created_at=datetime.fromtimestamp(stat.st_mtime),
                    size=size,
                    path=str(backup_dir)
                ))

        return sorted(backups, key=lambda x: x.created_at, reverse=True)

    async def _monitor_logs(self):
        """Monitor server logs"""
        if not self.server_process:
            return

        with open(self.log_file, 'a') as f:
            for line in iter(self.server_process.stdout.readline, ''):
                if not line:
                    break
                f.write(line)
                f.flush()

    async def stream_console_logs(self) -> AsyncIterator[str]:
        """Stream console logs in real-time"""
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                # Send existing logs
                lines = f.readlines()
                for line in lines[-100:]:  # Last 100 lines
                    yield line

                # Stream new logs
                while True:
                    line = f.readline()
                    if line:
                        # Feed to profiler for TPS/MSPT parsing
                        self.profiler.parse_tps_from_log(line)
                        self.profiler.parse_mspt_from_log(line)
                        yield line
                    else:
                        await asyncio.sleep(0.1)

    async def cleanup(self):
        """Cleanup resources"""
        if self.is_running():
            await self.stop_server()
        self.scheduler.shutdown()
        await self.profiler.cleanup()
        await self.modrinth_client.close()
        await self.curseforge_client.close()
        await self.spigot_client.close()

    # Player Management
    async def get_players(self) -> List[Player]:
        """Get list of all players"""
        players = []

        # Read from usercache.json
        usercache_file = self.minecraft_dir / "usercache.json"
        if usercache_file.exists():
            try:
                with open(usercache_file, 'r') as f:
                    cache_data = json.load(f)
                    for entry in cache_data:
                        players.append(Player(
                            uuid=entry.get('uuid', ''),
                            name=entry.get('name', ''),
                            online=False,
                            last_seen=datetime.fromisoformat(entry.get('expiresOn', datetime.now().isoformat()).replace('Z', '+00:00'))
                        ))
            except:
                pass

        # Check online players
        if self.is_running():
            # Parse from server logs or send list command
            # This is a simplified version
            pass

        return players

    async def get_online_players(self) -> List[Player]:
        """Get list of online players"""
        if not self.is_running():
            return []

        # Send list command and parse output
        # This would require parsing console output
        return [p for p in self.players_cache if p.online]

    async def player_action(self, player_name: str, action: PlayerAction, params: Optional[Dict[str, Any]] = None):
        """Perform action on player"""
        if not self.is_running():
            raise Exception("Server must be running")

        params = params or {}

        commands = {
            PlayerAction.KICK: f"kick {player_name} {params.get('reason', 'Kicked by admin')}",
            PlayerAction.BAN: f"ban {player_name} {params.get('reason', 'Banned by admin')}",
            PlayerAction.UNBAN: f"pardon {player_name}",
            PlayerAction.OP: f"op {player_name}",
            PlayerAction.DEOP: f"deop {player_name}",
            PlayerAction.WHITELIST_ADD: f"whitelist add {player_name}",
            PlayerAction.WHITELIST_REMOVE: f"whitelist remove {player_name}",
            PlayerAction.TELEPORT: f"tp {player_name} {params.get('x', 0)} {params.get('y', 64)} {params.get('z', 0)}",
            PlayerAction.GAMEMODE: f"gamemode {params.get('gamemode', 'survival')} {player_name}",
        }

        command = commands.get(action)
        if command:
            await self.send_command(command)

    async def get_player_inventory(self, player_name: str) -> Optional[PlayerInventory]:
        """Get player inventory (requires plugin/mod support)"""
        # This would require a plugin like Essentials or custom plugin
        # For demonstration, return mock data
        inventory_file = self.minecraft_dir / "world" / "playerdata" / f"{player_name}.dat"

        if not inventory_file.exists():
            return None

        # In production, you'd parse NBT data here
        # For now, return empty inventory
        return PlayerInventory(
            player_name=player_name,
            items=[]
        )

    async def give_item(self, player_name: str, item: str, amount: int = 1):
        """Give item to player"""
        if not self.is_running():
            raise Exception("Server must be running")

        await self.send_command(f"give {player_name} {item} {amount}")

    async def clear_inventory(self, player_name: str):
        """Clear player inventory"""
        if not self.is_running():
            raise Exception("Server must be running")

        await self.send_command(f"clear {player_name}")

    # World Management
    async def get_worlds(self) -> List[WorldInfo]:
        """Get list of worlds"""
        worlds = []

        world_dirs = ['world', 'world_nether', 'world_the_end']

        for world_name in world_dirs:
            world_path = self.minecraft_dir / world_name
            if world_path.exists():
                size = sum(f.stat().st_size for f in world_path.rglob('*') if f.is_file())
                stat = world_path.stat()

                # Read level.dat for seed
                seed = None
                level_dat = world_path / "level.dat"
                if level_dat.exists():
                    # Would need NBT parser for actual seed
                    seed = "Unknown"

                worlds.append(WorldInfo(
                    name=world_name,
                    size=size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                    seed=seed
                ))

        return worlds

    async def delete_world(self, world_name: str):
        """Delete a world"""
        if self.is_running():
            raise Exception("Server must be stopped to delete worlds")

        world_path = self.minecraft_dir / world_name
        if world_path.exists():
            shutil.rmtree(world_path)

    async def reset_world(self, world_name: str):
        """Reset a world (delete and regenerate on next start)"""
        await self.delete_world(world_name)

    # Scheduled Tasks
    def _load_scheduled_tasks(self):
        """Load scheduled tasks from file"""
        tasks_file = self.logs_dir / "scheduled_tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, 'r') as f:
                    tasks_data = json.load(f)
                    for task_data in tasks_data:
                        task = ScheduledTask(**task_data)
                        self.scheduled_tasks[task.id] = task
                        if task.enabled:
                            self._schedule_task(task)
            except Exception as e:
                print(f"Error loading scheduled tasks: {e}")

    def _save_scheduled_tasks(self):
        """Save scheduled tasks to file"""
        tasks_file = self.logs_dir / "scheduled_tasks.json"
        tasks_data = [task.dict() for task in self.scheduled_tasks.values()]
        with open(tasks_file, 'w') as f:
            json.dump(tasks_data, f, indent=2, default=str)

    def _schedule_task(self, task: ScheduledTask):
        """Schedule a task"""
        trigger = CronTrigger.from_crontab(task.schedule)

        async def task_wrapper():
            await self._execute_scheduled_task(task)

        self.scheduler.add_job(
            task_wrapper,
            trigger=trigger,
            id=task.id,
            name=task.name,
            replace_existing=True
        )

    async def _execute_scheduled_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        task.last_run = datetime.now()

        try:
            if task.task_type == "backup":
                await self.create_backup()
            elif task.task_type == "restart":
                await self.restart_server()
            elif task.task_type == "command":
                command = task.params.get('command', '')
                if command:
                    await self.send_command(command)
        except Exception as e:
            print(f"Error executing scheduled task {task.name}: {e}")

        self._save_scheduled_tasks()

    async def create_scheduled_task(self, task: ScheduledTask) -> ScheduledTask:
        """Create a new scheduled task"""
        if not task.id:
            task.id = str(uuid_module.uuid4())

        self.scheduled_tasks[task.id] = task

        if task.enabled:
            self._schedule_task(task)

        self._save_scheduled_tasks()
        return task

    async def update_scheduled_task(self, task_id: str, task: ScheduledTask):
        """Update a scheduled task"""
        if task_id not in self.scheduled_tasks:
            raise Exception("Task not found")

        # Remove old job
        try:
            self.scheduler.remove_job(task_id)
        except:
            pass

        # Update task
        task.id = task_id
        self.scheduled_tasks[task_id] = task

        # Reschedule if enabled
        if task.enabled:
            self._schedule_task(task)

        self._save_scheduled_tasks()

    async def delete_scheduled_task(self, task_id: str):
        """Delete a scheduled task"""
        if task_id not in self.scheduled_tasks:
            raise Exception("Task not found")

        # Remove job
        try:
            self.scheduler.remove_job(task_id)
        except:
            pass

        # Remove from dict
        del self.scheduled_tasks[task_id]
        self._save_scheduled_tasks()

    async def get_scheduled_tasks(self) -> List[ScheduledTask]:
        """Get all scheduled tasks"""
        return list(self.scheduled_tasks.values())

    # File Manager
    async def list_files(self, path: str = "") -> List[FileEntry]:
        """List files in a directory"""
        target_path = self.minecraft_dir / path

        if not target_path.exists() or not target_path.is_dir():
            raise Exception("Invalid directory")

        # Security check - don't allow going outside minecraft dir
        if not str(target_path.resolve()).startswith(str(self.minecraft_dir.resolve())):
            raise Exception("Access denied")

        entries = []
        for item in target_path.iterdir():
            stat = item.stat()
            entries.append(FileEntry(
                name=item.name,
                path=str(item.relative_to(self.minecraft_dir)),
                is_directory=item.is_dir(),
                size=stat.st_size if item.is_file() else 0,
                modified=datetime.fromtimestamp(stat.st_mtime)
            ))

        return sorted(entries, key=lambda x: (not x.is_directory, x.name))

    async def read_file(self, path: str) -> str:
        """Read file content"""
        target_path = self.minecraft_dir / path

        # Security check
        if not str(target_path.resolve()).startswith(str(self.minecraft_dir.resolve())):
            raise Exception("Access denied")

        if not target_path.exists() or not target_path.is_file():
            raise Exception("File not found")

        # Limit file size
        if target_path.stat().st_size > 1024 * 1024:  # 1MB
            raise Exception("File too large")

        with open(target_path, 'r') as f:
            return f.read()

    async def write_file(self, path: str, content: str):
        """Write file content"""
        target_path = self.minecraft_dir / path

        # Security check
        if not str(target_path.resolve()).startswith(str(self.minecraft_dir.resolve())):
            raise Exception("Access denied")

        with open(target_path, 'w') as f:
            f.write(content)

    async def delete_file(self, path: str):
        """Delete a file"""
        target_path = self.minecraft_dir / path

        # Security check
        if not str(target_path.resolve()).startswith(str(self.minecraft_dir.resolve())):
            raise Exception("Access denied")

        if target_path.is_file():
            target_path.unlink()
        elif target_path.is_dir():
            shutil.rmtree(target_path)

    # Multi-Source Integration
    async def search_projects(
        self,
        query: str,
        source: str = "modrinth",  # modrinth, curseforge, spigot, all
        project_type: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> List[ModrinthProject]:
        """Search for mods/plugins/datapacks from multiple sources"""
        results = []

        if source == "all":
            # Search all sources and combine results
            modrinth_results = await self.search_modrinth(query, project_type, categories)
            curseforge_results = await self.search_curseforge(query, project_type)
            if project_type in ["plugin", None]:
                spigot_results = await self.search_spigot(query)
                results = modrinth_results + curseforge_results + spigot_results
            else:
                results = modrinth_results + curseforge_results
        elif source == "modrinth":
            results = await self.search_modrinth(query, project_type, categories)
        elif source == "curseforge":
            results = await self.search_curseforge(query, project_type)
        elif source == "spigot":
            results = await self.search_spigot(query)

        return results

    async def search_modrinth(
        self,
        query: str,
        project_type: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> List[ModrinthProject]:
        """Search Modrinth for mods/plugins/datapacks"""
        facets = []

        if project_type:
            facets.append([f"project_type:{project_type}"])

        if categories:
            facets.append([f"categories:{cat}" for cat in categories])

        # Add game version filter
        facets.append([f"versions:{self.config.minecraft_version}"])

        result = await self.modrinth_client.search(query, facets=facets if facets else None)

        projects = []
        for hit in result.get("hits", []):
            projects.append(ModrinthProject(
                id=hit["project_id"],
                slug=hit["slug"],
                title=hit["title"],
                description=hit["description"],
                categories=hit.get("categories", []),
                project_type=hit["project_type"],
                downloads=hit["downloads"],
                icon_url=hit.get("icon_url"),
                author=hit.get("author", "Unknown"),
                versions=hit.get("versions", []),
                source="modrinth"
            ))

        return projects

    async def search_curseforge(
        self,
        query: str,
        project_type: Optional[str] = None
    ) -> List[ModrinthProject]:
        """Search CurseForge for mods/modpacks"""
        category_map = {
            "mod": self.curseforge_client.categories.get("mods"),
            "modpack": self.curseforge_client.categories.get("modpacks"),
            "plugin": self.curseforge_client.categories.get("bukkit_plugins")
        }

        category_id = category_map.get(project_type) if project_type else None

        result = await self.curseforge_client.search(
            query,
            category_id=category_id,
            game_version=self.config.minecraft_version
        )

        projects = []
        for item in result.get("data", []):
            # Map CurseForge data to our model
            authors = item.get("authors", [])
            author = authors[0].get("name", "Unknown") if authors else "Unknown"

            # Determine project type from categories
            categories = item.get("categories", [])
            cf_project_type = "mod"
            for cat in categories:
                cat_id = cat.get("classId")
                if cat_id == self.curseforge_client.categories.get("modpacks"):
                    cf_project_type = "modpack"
                elif cat_id == self.curseforge_client.categories.get("bukkit_plugins"):
                    cf_project_type = "plugin"

            projects.append(ModrinthProject(
                id=str(item["id"]),
                slug=item.get("slug", ""),
                title=item["name"],
                description=item.get("summary", ""),
                categories=[cat.get("name", "") for cat in categories],
                project_type=cf_project_type,
                downloads=item.get("downloadCount", 0),
                icon_url=item.get("logo", {}).get("thumbnailUrl"),
                author=author,
                versions=[],
                source="curseforge"
            ))

        return projects

    async def search_spigot(self, query: str) -> List[ModrinthProject]:
        """Search Spigot for plugins"""
        results = await self.spigot_client.search(query)

        projects = []
        for item in results:
            # Get author info
            author_info = item.get("author", {})
            author = author_info.get("name", "Unknown") if isinstance(author_info, dict) else "Unknown"

            # Get icon
            icon = item.get("icon", {})
            icon_url = icon.get("url") if isinstance(icon, dict) else None

            projects.append(ModrinthProject(
                id=str(item["id"]),
                slug=item.get("name", "").lower().replace(" ", "-"),
                title=item["name"],
                description=item.get("tag", ""),
                categories=item.get("category", {}).get("name", "").split() if item.get("category") else [],
                project_type="plugin",
                downloads=item.get("downloads", 0),
                icon_url=f"https://www.spigotmc.org/{icon_url}" if icon_url else None,
                author=author,
                versions=[],
                source="spigot"
            ))

        return projects

    async def get_project_versions(
        self,
        project_id: str,
        loader: Optional[str] = None
    ) -> List[ModrinthVersion]:
        """Get available versions for a project"""
        loaders = [loader] if loader else None
        game_versions = [self.config.minecraft_version]

        versions_data = await self.modrinth_client.get_project_versions(
            project_id,
            loaders=loaders,
            game_versions=game_versions
        )

        versions = []
        for v in versions_data:
            versions.append(ModrinthVersion(
                id=v["id"],
                project_id=v["project_id"],
                name=v["name"],
                version_number=v["version_number"],
                game_versions=v["game_versions"],
                loaders=v["loaders"],
                files=v["files"],
                downloads=v["downloads"],
                date_published=v["date_published"]
            ))

        return versions

    async def install_from_modrinth(
        self,
        version_id: str,
        install_type: str = "mods"  # mods, plugins, datapacks
    ) -> InstalledMod:
        """Install a mod/plugin/datapack from Modrinth"""
        # Get version details
        version = await self.modrinth_client.get_version(version_id)

        if not version.get("files"):
            raise Exception("No files found for this version")

        # Get primary file
        primary_file = None
        for f in version["files"]:
            if f.get("primary", False):
                primary_file = f
                break

        if not primary_file:
            primary_file = version["files"][0]

        # Determine installation directory
        install_dirs = {
            "mods": self.minecraft_dir / "mods",
            "plugins": self.minecraft_dir / "plugins",
            "datapacks": self.minecraft_dir / "world" / "datapacks"
        }

        install_dir = install_dirs.get(install_type, self.minecraft_dir / "mods")
        install_dir.mkdir(parents=True, exist_ok=True)

        # Download file
        filename = primary_file["filename"]
        dest_path = install_dir / filename

        success = await self.modrinth_client.download_file(
            primary_file["url"],
            dest_path
        )

        if not success:
            raise Exception("Failed to download file")

        # Create installed mod record
        installed = InstalledMod(
            filename=filename,
            project_id=version.get("project_id"),
            version_id=version["id"],
            name=version.get("name", filename),
            type=install_type,
            size=primary_file.get("size", 0),
            installed_date=datetime.now()
        )

        return installed

    async def list_installed_mods(self, mod_type: str = "mods") -> List[InstalledMod]:
        """List installed mods/plugins/datapacks"""
        install_dirs = {
            "mods": self.minecraft_dir / "mods",
            "plugins": self.minecraft_dir / "plugins",
            "datapacks": self.minecraft_dir / "world" / "datapacks"
        }

        install_dir = install_dirs.get(mod_type, self.minecraft_dir / "mods")

        if not install_dir.exists():
            return []

        installed = []
        for file_path in install_dir.glob("*.jar"):
            if file_path.is_file():
                stat = file_path.stat()
                installed.append(InstalledMod(
                    filename=file_path.name,
                    name=file_path.stem,
                    type=mod_type,
                    size=stat.st_size,
                    installed_date=datetime.fromtimestamp(stat.st_mtime)
                ))

        return installed

    async def uninstall_mod(self, filename: str, mod_type: str = "mods") -> bool:
        """Uninstall a mod/plugin/datapack"""
        install_dirs = {
            "mods": self.minecraft_dir / "mods",
            "plugins": self.minecraft_dir / "plugins",
            "datapacks": self.minecraft_dir / "world" / "datapacks"
        }

        install_dir = install_dirs.get(mod_type, self.minecraft_dir / "mods")
        file_path = install_dir / filename

        if file_path.exists():
            file_path.unlink()
            return True

        return False

    async def create_modpack_server(
        self,
        version_id: str,
        server_name: str,
        memory: str
    ) -> Dict[str, Any]:
        """Create a new server from a Modrinth modpack"""
        import zipfile
        import tempfile

        # Stop server if running
        if self.is_running():
            await self.stop_server()
            await asyncio.sleep(3)

        # Get modpack version details
        version = await self.modrinth_client.get_version(version_id)

        if not version.get("files"):
            raise Exception("No files found for this modpack version")

        # Get primary file (the modpack zip)
        primary_file = None
        for f in version["files"]:
            if f.get("primary", False) or f["filename"].endswith(".mrpack"):
                primary_file = f
                break

        if not primary_file:
            primary_file = version["files"][0]

        # Download modpack to temp location
        temp_dir = Path(tempfile.mkdtemp())
        modpack_path = temp_dir / primary_file["filename"]

        print(f"Downloading modpack: {primary_file['filename']}")
        success = await self.modrinth_client.download_file(
            primary_file["url"],
            modpack_path
        )

        if not success:
            shutil.rmtree(temp_dir)
            raise Exception("Failed to download modpack")

        # Backup current server
        if (self.minecraft_dir / "server.jar").exists():
            backup_name = f"pre-modpack-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            backup_path = self.backups_dir / backup_name
            print(f"Creating backup: {backup_name}")
            shutil.copytree(self.minecraft_dir, backup_path, ignore=shutil.ignore_patterns('*.log'))

        # Clear mods directory
        mods_dir = self.minecraft_dir / "mods"
        if mods_dir.exists():
            shutil.rmtree(mods_dir)
        mods_dir.mkdir(parents=True)

        # Extract modpack
        print("Extracting modpack...")
        with zipfile.ZipFile(modpack_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir / "modpack")

        modpack_extracted = temp_dir / "modpack"

        # Read modpack manifest (modrinth.index.json for mrpack format)
        manifest_path = modpack_extracted / "modrinth.index.json"
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            # Install mods from manifest
            print("Installing mods from modpack...")
            if "files" in manifest:
                for file_info in manifest["files"]:
                    file_url = file_info.get("downloads", [None])[0]
                    file_path = file_info.get("path", "")

                    if file_url and file_path:
                        dest_path = self.minecraft_dir / file_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)

                        print(f"Downloading: {file_path}")
                        await self.modrinth_client.download_file(file_url, dest_path)

            # Copy overrides (configs, scripts, etc.)
            overrides_dir = modpack_extracted / "overrides"
            if overrides_dir.exists():
                print("Copying overrides...")
                for item in overrides_dir.rglob("*"):
                    if item.is_file():
                        rel_path = item.relative_to(overrides_dir)
                        dest_path = self.minecraft_dir / rel_path
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_path)

            # Update server config based on modpack
            game_version = manifest.get("dependencies", {}).get("minecraft", "1.20.1")
            loader = "forge"
            if "fabric-loader" in manifest.get("dependencies", {}):
                loader = "fabric"
            elif "quilt-loader" in manifest.get("dependencies", {}):
                loader = "quilt"

            self.config.minecraft_version = game_version
            self.config.server_name = server_name
            self.config.memory = memory
            self._save_config()

            # Download appropriate server jar
            # For now, we'll just note this - in production you'd download the correct loader
            print(f"Modpack requires: {loader} for Minecraft {game_version}")
            print("Note: You may need to manually install the correct server jar for this modpack")

        # Cleanup
        shutil.rmtree(temp_dir)

        print("Modpack server created successfully!")
        return {
            "modpack": version.get("name", "Unknown"),
            "version": version.get("version_number", "Unknown"),
            "game_version": self.config.minecraft_version,
            "mods_installed": len(list(mods_dir.glob("*.jar")))
        }

    # Performance Profiler Methods
    def get_profiler_metrics(self) -> Dict[str, Any]:
        """Get current profiler metrics"""
        return self.profiler.get_current_metrics()

    def get_profiler_history(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Get profiler history metrics"""
        return self.profiler.get_history_metrics(duration_seconds)

    def get_profiler_statistics(self) -> Dict[str, Any]:
        """Get profiler statistics"""
        return self.profiler.get_statistics()

    def get_profiler_alerts(self) -> List[Dict[str, Any]]:
        """Get performance alerts"""
        return self.profiler.get_alerts()

    async def stream_profiler_metrics(self) -> AsyncIterator[Dict[str, Any]]:
        """Stream profiler metrics in real-time"""
        while True:
            metrics = self.get_profiler_metrics()
            yield metrics
            await asyncio.sleep(1)  # Send metrics every second
