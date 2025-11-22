# CLAUDE.md - CraftServer AI Assistant Guide

This document provides comprehensive guidance for AI assistants working with the CraftServer codebase.

## Project Overview

**CraftServer** is a Docker-based Minecraft server management application with a modern web interface inspired by Modrinth. It provides real-time server monitoring, console access, backup management, and configuration controls.

### Key Information
- **Language:** Python 3.11 (Backend), Vanilla JavaScript (Frontend)
- **Framework:** FastAPI with WebSocket support
- **Architecture:** RESTful API + Real-time WebSocket streaming
- **Deployment:** Docker + Docker Compose
- **Primary Use Case:** Managing Minecraft Java Edition servers

## Architecture

### Tech Stack

**Backend:**
- **FastAPI 0.104.1** - Modern async Python web framework
- **Uvicorn 0.24.0** - ASGI server with WebSocket support
- **Pydantic 2.5.0** - Data validation and settings management
- **psutil 5.9.6** - System and process monitoring
- **aiofiles 23.2.1** - Async file I/O operations

**Frontend:**
- **Vanilla JavaScript (ES6+)** - No framework dependencies
- **Modern CSS** - CSS Grid, Flexbox, CSS Variables
- **WebSocket API** - Real-time console streaming

**Infrastructure:**
- **Docker** - Python 3.11-slim base + OpenJDK 17 JRE
- **Docker Compose** - Service orchestration
- **Minecraft Server** - Java Edition (configurable version)

### Design Patterns

1. **Singleton Manager Pattern**
   - `MinecraftManager` is instantiated once per application
   - Manages all server lifecycle operations
   - Location: `backend/minecraft_manager.py`

2. **Async/Await Throughout**
   - All I/O operations are async
   - WebSocket streaming uses async generators
   - Server start/stop operations are non-blocking

3. **Service Layer Pattern**
   - FastAPI routes delegate to `MinecraftManager`
   - Business logic separated from HTTP concerns
   - Routes: `backend/main.py:33-143`
   - Logic: `backend/minecraft_manager.py`

4. **Data Model Validation**
   - Pydantic models for all API inputs/outputs
   - Type safety and runtime validation
   - Models: `backend/models.py`

## Codebase Structure

```
craftserver/
├── backend/                      # Python FastAPI application
│   ├── __init__.py              # Package marker
│   ├── main.py                  # FastAPI app, routes, WebSocket
│   ├── minecraft_manager.py     # Core business logic
│   └── models.py                # Pydantic data models
├── frontend/                     # Web interface
│   ├── index.html               # Single-page application
│   └── static/
│       ├── css/style.css        # Modrinth-inspired dark theme
│       └── js/app.js            # Frontend application logic
├── minecraft/                    # Minecraft server files (volume mount)
├── backups/                      # Backup storage (volume mount)
├── logs/                         # Application logs (volume mount)
├── Dockerfile                    # Container image definition
├── docker-compose.yml            # Service orchestration
├── requirements.txt              # Python dependencies
└── README.md                     # User documentation (Korean)
```

### Key Files and Their Roles

| File | Purpose | Lines | Key Functions |
|------|---------|-------|---------------|
| `backend/main.py` | API routes and WebSocket | 156 | 11 endpoints, 1 WebSocket handler |
| `backend/minecraft_manager.py` | Server management | 306 | Server lifecycle, backups, monitoring |
| `backend/models.py` | Data models | 47 | 4 Pydantic models |
| `frontend/static/js/app.js` | Frontend logic | ~500 | SPA navigation, API calls, WebSocket |
| `frontend/static/css/style.css` | UI styling | ~800 | Dark theme, responsive design |
| `Dockerfile` | Container setup | 30 | Python + Java installation |
| `docker-compose.yml` | Service config | 21 | Ports, volumes, environment |

## API Reference

### REST Endpoints

**Server Control:**
- `GET /api/status` → `ServerStatus` - Current server state and metrics
- `POST /api/server/start` → `{status, message}` - Start Minecraft server
- `POST /api/server/stop` → `{status, message}` - Graceful shutdown
- `POST /api/server/restart` → `{status, message}` - Stop then start
- `POST /api/server/command` - Send console command (body: `{command: str}`)

**Configuration:**
- `GET /api/config` → `ServerConfig` - Get server.properties values
- `POST /api/config` - Update config (body: `ServerConfig`)

**Backup Management:**
- `GET /api/backups` → `List[BackupInfo]` - List all backups
- `POST /api/backup` → `{status, message, backup}` - Create new backup
- `POST /api/backup/restore` - Restore backup (body: `{name: str}`)

**WebSocket:**
- `WS /ws/console` - Real-time console log streaming

### Data Models

**ServerStatus** (runtime state):
```python
is_running: bool           # Server process running
uptime: Optional[int]      # Seconds since start
player_count: int          # Current players (default: 0)
max_players: int           # Player limit
cpu_usage: float           # Process CPU % (when running)
memory_usage: float        # Process memory MB (when running)
memory_total: float        # Total system memory MB
version: Optional[str]     # Minecraft version
```

**ServerConfig** (persistent configuration):
```python
server_name: str           # Display name
max_players: int           # 1-100
gamemode: str              # survival|creative|adventure|spectator
difficulty: str            # peaceful|easy|normal|hard
pvp: bool                  # PvP enabled
online_mode: bool          # Mojang auth required
motd: str                  # Message of the day
view_distance: int         # 3-32 chunks
spawn_protection: int      # Spawn radius in blocks
memory: str                # JVM heap (1G|2G|4G|8G|16G)
minecraft_version: str     # Server version
```

**BackupInfo**:
```python
name: str                  # Directory name (backup_YYYYMMDD_HHMMSS)
created_at: datetime       # Backup timestamp
size: int                  # Total bytes
path: str                  # Absolute path
```

## Development Workflows

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Development

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Rebuild after changes
docker-compose up -d --build

# Stop services
docker-compose down
```

### Making Changes

**Backend Changes:**
1. Edit files in `backend/`
2. Test with `uvicorn backend.main:app --reload`
3. Verify API responses with browser or curl
4. Check logs for errors

**Frontend Changes:**
1. Edit `frontend/index.html` or `frontend/static/`
2. Hard refresh browser (Ctrl+Shift+R)
3. Check browser console for JavaScript errors
4. Test WebSocket connection in Network tab

**Configuration Changes:**
1. Update `docker-compose.yml` for environment variables
2. Update `Dockerfile` for system dependencies
3. Update `requirements.txt` for Python packages
4. Rebuild container: `docker-compose up -d --build`

## Coding Conventions

### Python (Backend)

**Style:**
- Follow PEP 8
- Use snake_case for functions and variables
- Use type hints on all function signatures
- Async/await for all I/O operations

**File Organization:**
- Routes in `main.py` (thin controllers)
- Business logic in `minecraft_manager.py` (service layer)
- Data models in `models.py` (Pydantic only)

**Error Handling:**
```python
# API routes
try:
    result = await mc_manager.some_operation()
    return {"status": "success", "message": "Done"}
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**Async Patterns:**
```python
# Non-blocking operations
async def start_server(self):
    # Use async subprocess handling
    self.server_process = subprocess.Popen(...)
    asyncio.create_task(self._monitor_logs())

# Streaming data
async def stream_console_logs(self) -> AsyncIterator[str]:
    while True:
        line = f.readline()
        if line:
            yield line
        else:
            await asyncio.sleep(0.1)
```

### JavaScript (Frontend)

**Style:**
- ES6+ syntax (classes, arrow functions, async/await)
- CamelCase for classes, camelCase for functions/variables
- Event delegation where possible
- No jQuery or external frameworks

**Application Structure:**
```javascript
class CraftServerApp {
    constructor() {
        // Initialize state
        this.ws = null;
        this.currentSection = 'dashboard';
    }

    async init() {
        // Setup event listeners
        // Connect WebSocket
        // Start status polling
    }
}
```

**API Calls:**
```javascript
// Fetch pattern
async someAction() {
    try {
        const response = await fetch('/api/endpoint', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        const result = await response.json();
        this.showToast(result.message, 'success');
    } catch (error) {
        this.showToast('Error: ' + error.message, 'error');
    }
}
```

### CSS

**Conventions:**
- kebab-case for class names
- CSS variables for theme colors
- Mobile-first responsive design
- Grid for layout, Flexbox for components

**Theme Variables (from style.css):**
```css
--primary-color: #1bd96a;  /* Modrinth green */
--bg-dark: #1a1a1a;
--bg-card: #2a2a2a;
--text-primary: #ffffff;
--text-secondary: #a0a0a0;
```

## Common Tasks

### Adding a New API Endpoint

1. Define Pydantic model in `backend/models.py` (if needed)
2. Add route to `backend/main.py`:
   ```python
   @app.post("/api/new-endpoint")
   async def new_endpoint(data: YourModel):
       try:
           result = await mc_manager.your_method(data)
           return {"status": "success", "data": result}
       except Exception as e:
           raise HTTPException(status_code=500, detail=str(e))
   ```
3. Implement logic in `backend/minecraft_manager.py`:
   ```python
   async def your_method(self, data: YourModel):
       # Implementation
       return result
   ```
4. Update frontend to call new endpoint

### Adding Server Configuration Option

1. Add field to `ServerConfig` in `backend/models.py`:
   ```python
   class ServerConfig(BaseModel):
       new_option: str = "default_value"
   ```
2. Update `_load_config()` in `minecraft_manager.py` to parse from server.properties
3. Update `_save_config()` to write to server.properties
4. Add UI control in `frontend/index.html` settings section
5. Update `app.js` to handle new field

### Implementing Real-time Feature

1. Modify `stream_console_logs()` or create new async generator
2. Add WebSocket endpoint in `main.py`:
   ```python
   @app.websocket("/ws/new-stream")
   async def new_stream(websocket: WebSocket):
       await websocket.accept()
       try:
           async for data in mc_manager.stream_data():
               await websocket.send_json(data)
       except WebSocketDisconnect:
           pass
   ```
3. Connect from frontend:
   ```javascript
   this.customWs = new WebSocket(`ws://${window.location.host}/ws/new-stream`);
   this.customWs.onmessage = (event) => {
       // Handle data
   };
   ```

## Important Considerations

### Server Process Management

**Process Lifecycle:**
1. `start_server()` creates subprocess with `Popen`
2. Process runs in background with stdio pipes
3. `_monitor_logs()` reads stdout to log file
4. `stop_server()` sends "stop" command, waits 30s, then kills
5. Process state tracked via `server_process.poll()`

**Critical Points:**
- Always check `is_running()` before operations
- Use `send_command()` for console input
- Handle subprocess cleanup in `cleanup()`
- Log monitoring runs as background task

### File Paths

**Container Paths (hardcoded in MinecraftManager):**
- Minecraft files: `/app/minecraft`
- Backups: `/app/backups`
- Logs: `/app/logs`

**Host Paths (docker-compose.yml volumes):**
- `./minecraft:/app/minecraft`
- `./backups:/app/backups`
- `./logs:/app/logs`

**Important:** When testing locally without Docker, these paths won't exist. Create them or adjust `minecraft_dir`, `backups_dir`, `logs_dir` in MinecraftManager.__init__()

### Environment Variables

Set in `docker-compose.yml`:
- `MINECRAFT_VERSION` - Minecraft version (default: 1.20.1)
- `SERVER_MEMORY` - JVM heap size (default: 2G)
- `SERVER_PORT` - Minecraft port (default: 25565)

Access in Python:
```python
version = os.getenv("MINECRAFT_VERSION", "1.20.1")
```

### Security Considerations

**Current Limitations:**
- No authentication/authorization
- CORS allows all origins (`allow_origins=["*"]`)
- Console commands have no validation
- Container runs as root

**For Production:**
- Add authentication middleware (JWT, OAuth2)
- Restrict CORS to specific domains
- Validate/sanitize console commands
- Run container as non-root user
- Enable HTTPS (reverse proxy)

### Known Limitations

1. **Server JAR Download** - `_download_server_jar()` creates placeholder file, doesn't actually download
   - Production: Implement Mojang version manifest API
   - URL pattern: `https://piston-data.mojang.com/v1/objects/{hash}/server.jar`

2. **Player Tracking** - Player model defined but not implemented
   - Would require parsing log files for join/leave events
   - Or using RCON/Query protocol

3. **Console History** - Logs stored on disk but in-memory limit in frontend (1000 lines)
   - Large log files may cause memory issues
   - Consider pagination or log rotation

4. **Backup Size** - No compression, backups can be large
   - Consider adding tar.gz compression
   - Implement backup retention policy

## Testing Guidelines

### Manual Testing Checklist

**Server Operations:**
- [ ] Start server (verify process starts)
- [ ] View real-time console logs
- [ ] Send console command (e.g., "list")
- [ ] Check CPU/memory metrics appear
- [ ] Stop server (verify graceful shutdown)
- [ ] Restart server

**Configuration:**
- [ ] Load config (verify values match server.properties)
- [ ] Update config (verify saves to file)
- [ ] Restart and verify changes applied

**Backups:**
- [ ] Create backup (verify directory created)
- [ ] List backups (verify metadata correct)
- [ ] Restore backup (verify files restored)

**WebSocket:**
- [ ] Connect to /ws/console
- [ ] Verify receives existing logs
- [ ] Verify receives new logs in real-time
- [ ] Test reconnection after disconnect

### API Testing with curl

```bash
# Get status
curl http://localhost:8000/api/status

# Start server
curl -X POST http://localhost:8000/api/server/start

# Send command
curl -X POST http://localhost:8000/api/server/command \
  -H "Content-Type: application/json" \
  -d '{"command": "list"}'

# Get config
curl http://localhost:8000/api/config

# Create backup
curl -X POST http://localhost:8000/api/backup
```

## Troubleshooting

### Server Won't Start

**Check:**
1. Java installed: `docker exec craftserver java -version`
2. server.jar exists: `ls minecraft/server.jar`
3. Memory allocation valid: Check `SERVER_MEMORY` env var
4. Port 25565 not in use: `lsof -i :25565`
5. Logs: `tail -f logs/server.log`

**Common Causes:**
- Insufficient memory
- EULA not accepted (auto-handled in code)
- Corrupted server.jar
- Port conflict

### WebSocket Not Connecting

**Check:**
1. Server running: `docker-compose ps`
2. Browser console errors
3. Network tab shows WebSocket connection attempt
4. CORS policy blocking connection

**Debug:**
```javascript
this.ws.onerror = (error) => {
    console.error('WebSocket Error:', error);
};
```

### Docker Issues

**Container won't start:**
```bash
# Check logs
docker-compose logs craftserver

# Rebuild
docker-compose down
docker-compose up -d --build

# Check volumes
docker volume ls
```

**Permission errors:**
- Container runs as root, shouldn't have permission issues
- If using local dev, check file ownership: `chown -R $USER minecraft/ backups/ logs/`

## Git Workflow

**Branch Naming:**
- Feature: `claude/feature-name-{session-id}`
- Current: `claude/claude-md-mi9ytj80yqj8e3k8-01KTifkvDi1yoqqzosLxyUBx`

**Commit Messages:**
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Be descriptive: "Add player tracking endpoint" not "Update code"
- Reference issues: "Fix #123: Server memory leak"

**Before Committing:**
1. Test changes locally
2. Check for console errors
3. Verify Docker build: `docker-compose up -d --build`
4. Review git diff for unintended changes

## Additional Resources

**FastAPI Documentation:**
- https://fastapi.tiangolo.com/
- WebSockets: https://fastapi.tiangolo.com/advanced/websockets/

**Minecraft Server:**
- Version Manifest: https://launchermeta.mojang.com/mc/game/version_manifest.json
- Server Properties: https://minecraft.fandom.com/wiki/Server.properties

**Pydantic:**
- https://docs.pydantic.dev/latest/

**Docker:**
- Compose: https://docs.docker.com/compose/

## Quick Reference Commands

```bash
# Development
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Docker
docker-compose up -d              # Start services
docker-compose down               # Stop services
docker-compose logs -f            # View logs
docker-compose restart            # Restart services
docker-compose up -d --build      # Rebuild and start

# Testing
curl http://localhost:8000/api/status
docker exec craftserver java -version
docker exec -it craftserver bash

# Debugging
tail -f logs/server.log           # Server logs
tail -f minecraft/logs/latest.log # Minecraft logs
docker-compose ps                 # Service status
```

---

**Last Updated:** 2025-11-22
**Version:** 1.0.0
**Maintainer:** CraftServer Development Team
