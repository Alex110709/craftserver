"""Java installation and management for Minecraft servers"""
import asyncio
import os
import platform
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import aiohttp
import re


class JavaManager:
    """Manages Java installation and version detection"""

    def __init__(self, java_base_dir: Path = Path("/app/java")):
        self.java_base_dir = java_base_dir
        self.java_base_dir.mkdir(parents=True, exist_ok=True)

        # Adoptium API for downloading Java
        self.adoptium_api = "https://api.adoptium.net/v3"

        # Minecraft version to Java version mapping
        self.version_mapping = {
            "1.20.5": 21,  # 1.20.5+ requires Java 21
            "1.20.4": 17,  # 1.18-1.20.4 requires Java 17
            "1.20.3": 17,
            "1.20.2": 17,
            "1.20.1": 17,
            "1.20": 17,
            "1.19.4": 17,
            "1.19.3": 17,
            "1.19.2": 17,
            "1.19.1": 17,
            "1.19": 17,
            "1.18.2": 17,
            "1.18.1": 17,
            "1.18": 17,
            "1.17.1": 16,  # 1.17 requires Java 16
            "1.17": 16,
            "1.16.5": 8,   # 1.16 and below can use Java 8
            "1.16.4": 8,
            "1.16.3": 8,
            "1.16.2": 8,
            "1.16.1": 8,
            "1.16": 8,
        }

    def get_required_java_version(self, minecraft_version: str) -> int:
        """Get the required Java version for a Minecraft version"""
        # Try exact match first
        if minecraft_version in self.version_mapping:
            return self.version_mapping[minecraft_version]

        # Parse version and determine based on major.minor
        try:
            parts = minecraft_version.split('.')
            if len(parts) >= 2:
                major = int(parts[1])
                minor = int(parts[2]) if len(parts) > 2 else 0

                # 1.20.5+ needs Java 21
                if major == 20 and minor >= 5:
                    return 21
                # 1.18-1.20.4 needs Java 17
                elif major >= 18:
                    return 17
                # 1.17 needs Java 16
                elif major == 17:
                    return 16
                # 1.16 and below can use Java 8
                else:
                    return 8
        except (ValueError, IndexError):
            pass

        # Default to Java 17 for unknown versions
        return 17

    async def get_installed_java_version(self, java_path: Optional[str] = None) -> Optional[int]:
        """Get the version of installed Java"""
        try:
            java_cmd = java_path if java_path else "java"

            process = await asyncio.create_subprocess_exec(
                java_cmd, "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            # Java prints version to stderr
            output = stderr.decode() if stderr else stdout.decode()

            # Parse version from output
            # Example: 'openjdk version "17.0.8"' or 'java version "1.8.0_381"'
            version_match = re.search(r'version "(\d+)\.(\d+)', output)
            if version_match:
                major = int(version_match.group(1))
                # Java 8 is reported as 1.8
                if major == 1:
                    return int(version_match.group(2))
                return major

            # Try alternative parsing for newer Java versions
            version_match = re.search(r'version "(\d+)', output)
            if version_match:
                return int(version_match.group(1))

        except (FileNotFoundError, subprocess.SubprocessError):
            pass

        return None

    def get_java_path(self, version: int) -> Optional[Path]:
        """Get the path to a specific Java installation"""
        java_dir = self.java_base_dir / f"jdk-{version}"

        if not java_dir.exists():
            return None

        # Find java executable
        bin_dir = java_dir / "bin"
        if not bin_dir.exists():
            # Check for nested structure (macOS)
            contents_dir = java_dir / "Contents" / "Home" / "bin"
            if contents_dir.exists():
                bin_dir = contents_dir

        java_exec = bin_dir / "java"
        if java_exec.exists():
            return java_exec

        return None

    async def is_java_installed(self, version: int) -> bool:
        """Check if a specific Java version is installed"""
        java_path = self.get_java_path(version)
        if not java_path:
            return False

        installed_version = await self.get_installed_java_version(str(java_path))
        return installed_version == version

    async def get_download_url(self, version: int) -> Optional[Dict[str, str]]:
        """Get download URL for Java from Adoptium"""
        try:
            # Determine OS and architecture
            system = platform.system().lower()
            machine = platform.machine().lower()

            # Map to Adoptium API parameters
            os_map = {
                "linux": "linux",
                "darwin": "mac",
                "windows": "windows"
            }

            arch_map = {
                "x86_64": "x64",
                "amd64": "x64",
                "aarch64": "aarch64",
                "arm64": "aarch64"
            }

            os_param = os_map.get(system, "linux")
            arch_param = arch_map.get(machine, "x64")

            # Build API URL
            url = f"{self.adoptium_api}/binary/latest/{version}/ga/{os_param}/{arch_param}/jdk/hotspot/normal/eclipse"

            async with aiohttp.ClientSession() as session:
                # Get redirect URL (actual download link)
                async with session.head(url, allow_redirects=True) as response:
                    if response.status == 200:
                        download_url = str(response.url)

                        # Determine file extension
                        if system == "linux":
                            ext = "tar.gz"
                        elif system == "darwin":
                            ext = "tar.gz"
                        else:  # windows
                            ext = "zip"

                        return {
                            "url": download_url,
                            "extension": ext,
                            "version": version
                        }

        except Exception as e:
            print(f"Failed to get download URL: {e}")

        return None

    async def download_java(
        self,
        version: int,
        progress_callback=None
    ) -> bool:
        """Download Java JDK"""
        try:
            download_info = await self.get_download_url(version)
            if not download_info:
                return False

            url = download_info["url"]
            ext = download_info["extension"]

            # Download to temporary file
            download_path = self.java_base_dir / f"jdk-{version}.{ext}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False

                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0

                    with open(download_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                            downloaded += len(chunk)

                            if progress_callback and total_size > 0:
                                progress = (downloaded / total_size) * 100
                                await progress_callback(progress, "downloading")

            if progress_callback:
                await progress_callback(100, "extracting")

            # Extract archive
            java_dir = self.java_base_dir / f"jdk-{version}"
            if java_dir.exists():
                shutil.rmtree(java_dir)

            java_dir.mkdir(parents=True, exist_ok=True)

            if ext == "tar.gz":
                with tarfile.open(download_path, 'r:gz') as tar:
                    # Extract to temp directory first
                    temp_extract = self.java_base_dir / "temp_extract"
                    temp_extract.mkdir(exist_ok=True)
                    tar.extractall(temp_extract)

                    # Find the root directory (usually jdk-<version>+<build>)
                    extracted_dirs = list(temp_extract.iterdir())
                    if extracted_dirs:
                        # Move contents to final location
                        shutil.move(str(extracted_dirs[0]), str(java_dir))
                        shutil.rmtree(temp_extract)
            elif ext == "zip":
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    temp_extract = self.java_base_dir / "temp_extract"
                    temp_extract.mkdir(exist_ok=True)
                    zip_ref.extractall(temp_extract)

                    extracted_dirs = list(temp_extract.iterdir())
                    if extracted_dirs:
                        shutil.move(str(extracted_dirs[0]), str(java_dir))
                        shutil.rmtree(temp_extract)

            # Make java executable (Unix-like systems)
            java_exec = self.get_java_path(version)
            if java_exec and os.name != 'nt':
                os.chmod(java_exec, 0o755)

            # Clean up download file
            download_path.unlink()

            if progress_callback:
                await progress_callback(100, "completed")

            return True

        except Exception as e:
            print(f"Failed to download Java: {e}")
            return False

    async def install_java(
        self,
        version: int,
        progress_callback=None
    ) -> Tuple[bool, str]:
        """Install Java if not already installed"""
        # Check if already installed
        if await self.is_java_installed(version):
            return True, f"Java {version} is already installed"

        # Download and install
        success = await self.download_java(version, progress_callback)

        if success:
            return True, f"Java {version} installed successfully"
        else:
            return False, f"Failed to install Java {version}"

    async def auto_install_for_minecraft(
        self,
        minecraft_version: str,
        progress_callback=None
    ) -> Tuple[bool, str, int]:
        """Automatically install the required Java version for Minecraft"""
        required_version = self.get_required_java_version(minecraft_version)

        success, message = await self.install_java(required_version, progress_callback)

        return success, message, required_version

    def get_java_info(self) -> Dict[str, Any]:
        """Get information about installed Java versions"""
        installed = []

        for java_dir in self.java_base_dir.iterdir():
            if java_dir.is_dir() and java_dir.name.startswith("jdk-"):
                try:
                    version = int(java_dir.name.split("-")[1])
                    java_path = self.get_java_path(version)

                    installed.append({
                        "version": version,
                        "path": str(java_path) if java_path else None,
                        "exists": java_path is not None
                    })
                except (ValueError, IndexError):
                    continue

        return {
            "installed_versions": sorted(installed, key=lambda x: x["version"]),
            "java_base_dir": str(self.java_base_dir)
        }

    async def cleanup_unused_versions(self, keep_versions: list[int]):
        """Remove Java versions that are not in the keep list"""
        for java_dir in self.java_base_dir.iterdir():
            if java_dir.is_dir() and java_dir.name.startswith("jdk-"):
                try:
                    version = int(java_dir.name.split("-")[1])
                    if version not in keep_versions:
                        shutil.rmtree(java_dir)
                        print(f"Removed Java {version}")
                except (ValueError, IndexError):
                    continue
