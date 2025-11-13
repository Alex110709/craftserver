import asyncio
import os
import shutil
import psutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, AsyncIterator
import subprocess
import time
import json

from .models import ServerStatus, ServerConfig, BackupInfo


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

    async def initialize(self):
        """Initialize the manager"""
        # Create directories
        self.minecraft_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Download server jar if not exists
        server_jar = self.minecraft_dir / "server.jar"
        if not server_jar.exists():
            await self._download_server_jar()

        # Create/load server properties
        self._load_config()

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
                        yield line
                    else:
                        await asyncio.sleep(0.1)

    async def cleanup(self):
        """Cleanup resources"""
        if self.is_running():
            await self.stop_server()
