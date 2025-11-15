"""Multi-server manager for managing multiple Minecraft server instances"""
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .minecraft_manager import MinecraftManager
from .models import ServerConfig


class ServerInfo:
    """Information about a Minecraft server instance"""

    def __init__(self, server_id: str, name: str, port: int, created_at: str):
        self.id = server_id
        self.name = name
        self.port = port
        self.created_at = created_at
        self.last_accessed = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "port": self.port,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerInfo':
        server = cls(
            server_id=data["id"],
            name=data["name"],
            port=data["port"],
            created_at=data["created_at"]
        )
        server.last_accessed = data.get("last_accessed", datetime.now().isoformat())
        return server


class ServerManager:
    """Manages multiple Minecraft server instances"""

    def __init__(self, base_dir: Path = Path("/app/servers")):
        self.base_dir = base_dir
        self.config_file = base_dir / "servers.json"
        self.servers: Dict[str, ServerInfo] = {}
        self.managers: Dict[str, MinecraftManager] = {}
        self.current_server_id: Optional[str] = None

        # Create base directory
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Load existing servers
        self._load_servers()

    def _load_servers(self):
        """Load server configurations from disk"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for server_data in data.get("servers", []):
                        server = ServerInfo.from_dict(server_data)
                        self.servers[server.id] = server
                    self.current_server_id = data.get("current_server_id")
            except Exception as e:
                print(f"Error loading servers config: {e}")

        # If no servers exist, create a default one
        if not self.servers:
            self._create_default_server()

    def _save_servers(self):
        """Save server configurations to disk"""
        try:
            data = {
                "servers": [server.to_dict() for server in self.servers.values()],
                "current_server_id": self.current_server_id
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving servers config: {e}")

    def _create_default_server(self):
        """Create a default server"""
        server_id = str(uuid.uuid4())
        server = ServerInfo(
            server_id=server_id,
            name="Default Server",
            port=25565,
            created_at=datetime.now().isoformat()
        )
        self.servers[server_id] = server
        self.current_server_id = server_id
        self._save_servers()

    def _get_server_dir(self, server_id: str) -> Path:
        """Get the directory for a specific server"""
        return self.base_dir / server_id

    async def _create_manager(self, server_id: str) -> MinecraftManager:
        """Create a MinecraftManager instance for a server"""
        server_dir = self._get_server_dir(server_id)
        manager = MinecraftManager(
            minecraft_dir=server_dir / "minecraft",
            backups_dir=server_dir / "backups",
            logs_dir=server_dir / "logs"
        )
        await manager.initialize()
        return manager

    async def get_manager(self, server_id: Optional[str] = None) -> Optional[MinecraftManager]:
        """Get or create a MinecraftManager for a server"""
        # Use current server if none specified
        if server_id is None:
            server_id = self.current_server_id

        if server_id is None or server_id not in self.servers:
            return None

        # Update last accessed time
        self.servers[server_id].last_accessed = datetime.now().isoformat()
        self._save_servers()

        # Return existing manager or create new one
        if server_id not in self.managers:
            self.managers[server_id] = await self._create_manager(server_id)

        return self.managers[server_id]

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all servers"""
        return [server.to_dict() for server in self.servers.values()]

    def get_server_info(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific server"""
        if server_id in self.servers:
            return self.servers[server_id].to_dict()
        return None

    async def create_server(
        self,
        name: str,
        port: Optional[int] = None,
        minecraft_version: str = "1.20.1",
        server_type: str = "vanilla"
    ) -> Dict[str, Any]:
        """Create a new server"""
        # Generate unique server ID
        server_id = str(uuid.uuid4())

        # Find available port if not specified
        if port is None:
            port = self._find_available_port()

        # Create server info
        server = ServerInfo(
            server_id=server_id,
            name=name,
            port=port,
            created_at=datetime.now().isoformat()
        )

        # Create server directory structure
        server_dir = self._get_server_dir(server_id)
        server_dir.mkdir(parents=True, exist_ok=True)
        (server_dir / "minecraft").mkdir(exist_ok=True)
        (server_dir / "backups").mkdir(exist_ok=True)
        (server_dir / "logs").mkdir(exist_ok=True)

        # Add to servers list
        self.servers[server_id] = server
        self._save_servers()

        # Create and initialize manager
        manager = await self._create_manager(server_id)
        self.managers[server_id] = manager

        # Configure server
        manager.config.minecraft_version = minecraft_version
        manager.config.server_port = port
        manager.config.server_name = name
        manager._save_config()

        return server.to_dict()

    async def delete_server(self, server_id: str) -> bool:
        """Delete a server"""
        if server_id not in self.servers:
            return False

        # Stop and cleanup manager if exists
        if server_id in self.managers:
            await self.managers[server_id].cleanup()
            del self.managers[server_id]

        # Remove from servers list
        del self.servers[server_id]

        # Update current server if needed
        if self.current_server_id == server_id:
            if len(self.servers) > 0:
                # Set to first available server
                self.current_server_id = next(iter(self.servers.keys()))
            else:
                # No servers left, create a default one
                self._create_default_server()

        self._save_servers()

        # Optionally delete server directory
        # import shutil
        # server_dir = self._get_server_dir(server_id)
        # if server_dir.exists():
        #     shutil.rmtree(server_dir)

        return True

    def set_current_server(self, server_id: str) -> bool:
        """Set the current active server"""
        if server_id not in self.servers:
            return False

        self.current_server_id = server_id
        self.servers[server_id].last_accessed = datetime.now().isoformat()
        self._save_servers()
        return True

    def get_current_server_id(self) -> Optional[str]:
        """Get the current active server ID"""
        return self.current_server_id

    def _find_available_port(self, start_port: int = 25565) -> int:
        """Find an available port for a new server"""
        used_ports = {server.port for server in self.servers.values()}
        port = start_port
        while port in used_ports:
            port += 1
        return port

    async def cleanup(self):
        """Cleanup all managers"""
        for manager in self.managers.values():
            await manager.cleanup()
        self.managers.clear()

    async def update_server_info(
        self,
        server_id: str,
        name: Optional[str] = None,
        port: Optional[int] = None
    ) -> bool:
        """Update server information"""
        if server_id not in self.servers:
            return False

        server = self.servers[server_id]

        if name is not None:
            server.name = name
            # Update manager config if exists
            if server_id in self.managers:
                self.managers[server_id].config.server_name = name
                self.managers[server_id]._save_config()

        if port is not None:
            # Check if port is already in use by another server
            for sid, s in self.servers.items():
                if sid != server_id and s.port == port:
                    raise Exception(f"Port {port} is already in use")

            server.port = port
            # Update manager config if exists
            if server_id in self.managers:
                self.managers[server_id].config.server_port = port
                self.managers[server_id]._save_config()

        self._save_servers()
        return True
