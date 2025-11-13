import aiohttp
import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path
import json


class ModrinthClient:
    """Client for Modrinth API"""

    def __init__(self):
        self.base_url = "https://api.modrinth.com/v2"
        self.user_agent = "CraftServer/1.0.0"

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the Modrinth API"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "User-Agent": self.user_agent,
            **kwargs.pop("headers", {})
        }

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Modrinth API error: {response.status}")

    async def search(
        self,
        query: str,
        facets: Optional[List[List[str]]] = None,
        index: str = "relevance",
        offset: int = 0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for projects on Modrinth"""
        params = {
            "query": query,
            "index": index,
            "offset": offset,
            "limit": limit
        }

        if facets:
            params["facets"] = json.dumps(facets)

        return await self._request("GET", "/search", params=params)

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details"""
        return await self._request("GET", f"/project/{project_id}")

    async def get_project_versions(
        self,
        project_id: str,
        loaders: Optional[List[str]] = None,
        game_versions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get project versions"""
        params = {}
        if loaders:
            params["loaders"] = json.dumps(loaders)
        if game_versions:
            params["game_versions"] = json.dumps(game_versions)

        return await self._request("GET", f"/project/{project_id}/version", params=params)

    async def get_version(self, version_id: str) -> Dict[str, Any]:
        """Get version details"""
        return await self._request("GET", f"/version/{version_id}")

    async def download_file(self, url: str, dest_path: Path) -> bool:
        """Download a file from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={"User-Agent": self.user_agent}) as response:
                    if response.status == 200:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(dest_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                        return True
                    return False
        except Exception as e:
            print(f"Download error: {e}")
            return False
