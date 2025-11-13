"""CurseForge API Client for fetching mods, modpacks, and plugins"""
import aiohttp
from typing import Dict, Any, List, Optional
from pathlib import Path


class CurseForgeClient:
    """Client for interacting with CurseForge API"""

    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://api.curseforge.com/v1"
        self.api_key = api_key or ""  # API key can be set via environment variable
        self.session: Optional[aiohttp.ClientSession] = None

        # CurseForge game ID for Minecraft
        self.minecraft_game_id = 432

        # Category IDs
        self.categories = {
            "modpacks": 4471,
            "mods": 6,
            "bukkit_plugins": 5,
            "resource_packs": 12,
            "worlds": 17
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def search(
        self,
        query: str,
        category_id: Optional[int] = None,
        game_version: Optional[str] = None,
        mod_loader_type: Optional[int] = None,  # 1=Forge, 4=Fabric, 5=Quilt
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Search for mods/modpacks on CurseForge"""
        session = await self._get_session()

        params = {
            "gameId": self.minecraft_game_id,
            "searchFilter": query,
            "pageSize": page_size,
            "index": 0
        }

        if category_id:
            params["classId"] = category_id

        if game_version:
            params["gameVersion"] = game_version

        if mod_loader_type:
            params["modLoaderType"] = mod_loader_type

        try:
            async with session.get(f"{self.base_url}/mods/search", params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"CurseForge API error: {response.status}")
                    return {"data": []}
        except Exception as e:
            print(f"Error searching CurseForge: {e}")
            return {"data": []}

    async def get_mod(self, mod_id: int) -> Optional[Dict[str, Any]]:
        """Get details for a specific mod"""
        session = await self._get_session()

        try:
            async with session.get(f"{self.base_url}/mods/{mod_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("data")
                return None
        except Exception as e:
            print(f"Error getting mod from CurseForge: {e}")
            return None

    async def get_mod_files(
        self,
        mod_id: int,
        game_version: Optional[str] = None,
        mod_loader_type: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get available files/versions for a mod"""
        session = await self._get_session()

        params = {}
        if game_version:
            params["gameVersion"] = game_version
        if mod_loader_type:
            params["modLoaderType"] = mod_loader_type

        try:
            async with session.get(f"{self.base_url}/mods/{mod_id}/files", params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("data", [])
                return []
        except Exception as e:
            print(f"Error getting mod files from CurseForge: {e}")
            return []

    async def get_file(self, mod_id: int, file_id: int) -> Optional[Dict[str, Any]]:
        """Get details for a specific file"""
        session = await self._get_session()

        try:
            async with session.get(f"{self.base_url}/mods/{mod_id}/files/{file_id}") as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("data")
                return None
        except Exception as e:
            print(f"Error getting file from CurseForge: {e}")
            return None

    async def download_file(self, download_url: str, dest_path: Path) -> bool:
        """Download a file from CurseForge"""
        session = await self._get_session()

        try:
            async with session.get(download_url) as response:
                if response.status == 200:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    return True
                else:
                    print(f"Failed to download file: {response.status}")
                    return False
        except Exception as e:
            print(f"Error downloading file from CurseForge: {e}")
            return False
