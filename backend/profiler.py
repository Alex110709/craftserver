"""Performance profiler for Minecraft server - similar to Spark"""
import asyncio
import time
import re
from typing import Dict, Any, List, Optional, Deque
from collections import deque
from datetime import datetime
import psutil
import docker
from pathlib import Path


class PerformanceProfiler:
    """Real-time performance profiler for Minecraft server"""

    def __init__(self, container_name: str = "minecraft-server", history_size: int = 300):
        self.container_name = container_name
        self.history_size = history_size  # Keep 5 minutes of data at 1 sample/second

        # Performance metrics history
        self.tps_history: Deque[float] = deque(maxlen=history_size)
        self.cpu_history: Deque[float] = deque(maxlen=history_size)
        self.memory_history: Deque[float] = deque(maxlen=history_size)
        self.tick_time_history: Deque[float] = deque(maxlen=history_size)
        self.timestamp_history: Deque[float] = deque(maxlen=history_size)

        # Current metrics
        self.current_tps: float = 20.0
        self.current_cpu: float = 0.0
        self.current_memory: float = 0.0
        self.current_memory_used: int = 0
        self.current_memory_max: int = 0
        self.current_tick_time: float = 0.0

        # Docker client
        self.docker_client: Optional[docker.DockerClient] = None
        self.container = None

        # Monitoring state
        self.is_running = False
        self.monitor_task = None

        # Plugin/Mod profiling
        self.plugin_cpu_usage: Dict[str, float] = {}
        self.entity_counts: Dict[str, int] = {}

    async def initialize(self):
        """Initialize the profiler"""
        try:
            self.docker_client = docker.from_env()
            await self._find_container()
        except Exception as e:
            print(f"Failed to initialize profiler: {e}")

    async def _find_container(self):
        """Find the Minecraft server container"""
        try:
            if self.docker_client:
                self.container = self.docker_client.containers.get(self.container_name)
        except docker.errors.NotFound:
            print(f"Container {self.container_name} not found")
            self.container = None
        except Exception as e:
            print(f"Error finding container: {e}")
            self.container = None

    async def start_monitoring(self):
        """Start real-time monitoring"""
        if self.is_running:
            return

        self.is_running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Update container reference if needed
                if not self.container:
                    await self._find_container()

                if self.container:
                    # Collect metrics
                    await self._collect_docker_stats()
                    await self._collect_tps_data()

                    # Add timestamp
                    self.timestamp_history.append(time.time())

                # Wait before next collection
                await asyncio.sleep(1)  # Collect every second

            except Exception as e:
                print(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def _collect_docker_stats(self):
        """Collect CPU and memory stats from Docker"""
        try:
            if not self.container:
                return

            # Reload container to get fresh stats
            self.container.reload()

            # Get container stats (this is a blocking call, so run in executor)
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None,
                lambda: self.container.stats(stream=False)
            )

            # Calculate CPU percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_count = stats['cpu_stats']['online_cpus']

            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0
                self.current_cpu = round(cpu_percent, 2)
                self.cpu_history.append(self.current_cpu)

            # Calculate memory usage
            memory_usage = stats['memory_stats'].get('usage', 0)
            memory_limit = stats['memory_stats'].get('limit', 1)
            memory_percent = (memory_usage / memory_limit) * 100.0

            self.current_memory = round(memory_percent, 2)
            self.current_memory_used = memory_usage
            self.current_memory_max = memory_limit
            self.memory_history.append(self.current_memory)

        except Exception as e:
            print(f"Error collecting Docker stats: {e}")

    async def _collect_tps_data(self):
        """Collect TPS data from server logs"""
        # This would parse the server console output for TPS information
        # For now, we'll simulate it. In reality, you'd need to:
        # 1. Send /tps command periodically
        # 2. Parse the response
        # 3. Extract TPS values

        # Placeholder - in real implementation, parse from console
        # For Paper/Spigot servers: /tps shows TPS
        # Output format: "TPS from last 1m, 5m, 15m: 20.0, 19.8, 19.5"
        pass

    def parse_tps_from_log(self, log_line: str):
        """Parse TPS from server log line"""
        # Example: "TPS from last 1m, 5m, 15m: 20.0, 19.8, 19.5"
        tps_pattern = r'TPS.*?(\d+\.?\d*)'
        match = re.search(tps_pattern, log_line)
        if match:
            tps = float(match.group(1))
            self.current_tps = tps
            self.tps_history.append(tps)

            # Calculate approximate tick time (should be 50ms for 20 TPS)
            if tps > 0:
                tick_time = 50.0 / (tps / 20.0)
                self.current_tick_time = round(tick_time, 2)
                self.tick_time_history.append(self.current_tick_time)

    def parse_mspt_from_log(self, log_line: str):
        """Parse MSPT (milliseconds per tick) from server log"""
        # Example: "Time: Mean tick: 45.2ms"
        mspt_pattern = r'tick.*?(\d+\.?\d*)\s*ms'
        match = re.search(mspt_pattern, log_line, re.IGNORECASE)
        if match:
            mspt = float(match.group(1))
            self.current_tick_time = mspt
            self.tick_time_history.append(mspt)

            # Calculate TPS from MSPT (ideal is 50ms = 20 TPS)
            if mspt > 0:
                tps = min(20.0, 1000.0 / mspt)
                self.current_tps = round(tps, 2)
                self.tps_history.append(self.current_tps)

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            "timestamp": time.time(),
            "tps": self.current_tps,
            "cpu_percent": self.current_cpu,
            "memory_percent": self.current_memory,
            "memory_used_mb": self.current_memory_used / (1024 * 1024),
            "memory_max_mb": self.current_memory_max / (1024 * 1024),
            "tick_time_ms": self.current_tick_time,
            "status": self._get_performance_status()
        }

    def get_history_metrics(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Get historical performance metrics"""
        # Calculate how many samples to return
        samples = min(duration_seconds, len(self.timestamp_history))

        if samples == 0:
            return {
                "timestamps": [],
                "tps": [],
                "cpu": [],
                "memory": [],
                "tick_time": []
            }

        return {
            "timestamps": list(self.timestamp_history)[-samples:],
            "tps": list(self.tps_history)[-samples:],
            "cpu": list(self.cpu_history)[-samples:],
            "memory": list(self.memory_history)[-samples:],
            "tick_time": list(self.tick_time_history)[-samples:]
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistical analysis of performance"""
        if len(self.tps_history) == 0:
            return {}

        return {
            "tps": {
                "current": self.current_tps,
                "avg": round(sum(self.tps_history) / len(self.tps_history), 2),
                "min": round(min(self.tps_history), 2),
                "max": round(max(self.tps_history), 2)
            },
            "cpu": {
                "current": self.current_cpu,
                "avg": round(sum(self.cpu_history) / len(self.cpu_history), 2) if self.cpu_history else 0,
                "min": round(min(self.cpu_history), 2) if self.cpu_history else 0,
                "max": round(max(self.cpu_history), 2) if self.cpu_history else 0
            },
            "memory": {
                "current": self.current_memory,
                "avg": round(sum(self.memory_history) / len(self.memory_history), 2) if self.memory_history else 0,
                "min": round(min(self.memory_history), 2) if self.memory_history else 0,
                "max": round(max(self.memory_history), 2) if self.memory_history else 0
            },
            "tick_time": {
                "current": self.current_tick_time,
                "avg": round(sum(self.tick_time_history) / len(self.tick_time_history), 2) if self.tick_time_history else 0,
                "min": round(min(self.tick_time_history), 2) if self.tick_time_history else 0,
                "max": round(max(self.tick_time_history), 2) if self.tick_time_history else 0
            }
        }

    def _get_performance_status(self) -> str:
        """Determine overall performance status"""
        if self.current_tps >= 19.5:
            return "excellent"
        elif self.current_tps >= 18.0:
            return "good"
        elif self.current_tps >= 15.0:
            return "fair"
        else:
            return "poor"

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get performance alerts"""
        alerts = []

        # TPS alerts
        if self.current_tps < 15.0:
            alerts.append({
                "level": "critical",
                "type": "tps",
                "message": f"Critical TPS lag detected: {self.current_tps} TPS",
                "value": self.current_tps
            })
        elif self.current_tps < 18.0:
            alerts.append({
                "level": "warning",
                "type": "tps",
                "message": f"TPS below optimal: {self.current_tps} TPS",
                "value": self.current_tps
            })

        # CPU alerts
        if self.current_cpu > 90:
            alerts.append({
                "level": "critical",
                "type": "cpu",
                "message": f"High CPU usage: {self.current_cpu}%",
                "value": self.current_cpu
            })
        elif self.current_cpu > 75:
            alerts.append({
                "level": "warning",
                "type": "cpu",
                "message": f"Elevated CPU usage: {self.current_cpu}%",
                "value": self.current_cpu
            })

        # Memory alerts
        if self.current_memory > 90:
            alerts.append({
                "level": "critical",
                "type": "memory",
                "message": f"High memory usage: {self.current_memory}%",
                "value": self.current_memory
            })
        elif self.current_memory > 80:
            alerts.append({
                "level": "warning",
                "type": "memory",
                "message": f"Elevated memory usage: {self.current_memory}%",
                "value": self.current_memory
            })

        # Tick time alerts (ideal is 50ms)
        if self.current_tick_time > 100:
            alerts.append({
                "level": "critical",
                "type": "tick_time",
                "message": f"Very high tick time: {self.current_tick_time}ms",
                "value": self.current_tick_time
            })
        elif self.current_tick_time > 70:
            alerts.append({
                "level": "warning",
                "type": "tick_time",
                "message": f"High tick time: {self.current_tick_time}ms",
                "value": self.current_tick_time
            })

        return alerts

    async def cleanup(self):
        """Cleanup resources"""
        await self.stop_monitoring()
        if self.docker_client:
            self.docker_client.close()
