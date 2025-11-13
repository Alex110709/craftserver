"""Spigot/Spiget API Client for fetching Bukkit/Spigot plugins"""
import aiohttp
from typing import Dict, Any, List, Optional
from pathlib import Path


class SpigotClient:
    """Client for interacting with Spiget API (Spigot resources)"""

    def __init__(self):
        self.base_url = "https://api.spiget.org/v2"
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers={
                "User-Agent": "CraftServer/1.0"
            })
        return self.session

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def search(
        self,
        query: str,
        size: int = 20,
        sort: str = "-downloads"  # Sort by downloads descending
    ) -> List[Dict[str, Any]]:
        """Search for plugins on Spigot"""
        session = await self._get_session()

        params = {
            "size": size,
            "sort": sort
        }

        try:
            # Spiget search endpoint
            async with session.get(
                f"{self.base_url}/search/resources/{query}",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Spiget API error: {response.status}")
                    return []
        except Exception as e:
            print(f"Error searching Spigot: {e}")
            return []

    async def get_resource(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """Get details for a specific resource/plugin"""
        session = await self._get_session()

        try:
            async with session.get(f"{self.base_url}/resources/{resource_id}") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f"Error getting resource from Spigot: {e}")
            return None

    async def get_resource_versions(self, resource_id: int) -> List[Dict[str, Any]]:
        """Get available versions for a resource"""
        session = await self._get_session()

        try:
            async with session.get(f"{self.base_url}/resources/{resource_id}/versions") as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            print(f"Error getting resource versions from Spigot: {e}")
            return []

    async def get_latest_version(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """Get the latest version of a resource"""
        session = await self._get_session()

        try:
            async with session.get(f"{self.base_url}/resources/{resource_id}/versions/latest") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f"Error getting latest version from Spigot: {e}")
            return None

    async def get_download_url(self, resource_id: int, version_id: Optional[int] = None) -> Optional[str]:
        """Get download URL for a resource"""
        if version_id:
            return f"https://api.spiget.org/v2/resources/{resource_id}/versions/{version_id}/download"
        else:
            return f"https://api.spiget.org/v2/resources/{resource_id}/download"

    async def download_file(self, resource_id: int, dest_path: Path, version_id: Optional[int] = None) -> bool:
        """Download a plugin from Spigot"""
        session = await self._get_session()

        download_url = await self.get_download_url(resource_id, version_id)
        if not download_url:
            return False

        try:
            async with session.get(download_url, allow_redirects=True) as response:
                if response.status == 200:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(dest_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    return True
                else:
                    print(f"Failed to download plugin: {response.status}")
                    return False
        except Exception as e:
            print(f"Error downloading plugin from Spigot: {e}")
            return False

    async def get_resource_author(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """Get author information for a resource"""
        session = await self._get_session()

        try:
            async with session.get(f"{self.base_url}/resources/{resource_id}/author") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            print(f"Error getting author from Spigot: {e}")
            return None
