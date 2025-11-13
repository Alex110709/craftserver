// CraftServer Manager - Frontend Application

class CraftServerApp {
    constructor() {
        this.apiBase = '';
        this.ws = null;
        this.updateInterval = null;
        this.init();
    }

    init() {
        this.initTheme();
        this.setupNavigation();
        this.setupEventListeners();
        this.setupTabs();
        this.connectWebSocket();
        this.startStatusUpdates();
        this.loadInitialData();
    }

    // Theme Management
    initTheme() {
        // Load theme from localStorage or default to dark
        const savedTheme = localStorage.getItem('theme') || 'dark';
        this.setTheme(savedTheme);

        // Add theme toggle event listener
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.currentTheme = theme;
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }

    // Navigation
    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        const sections = document.querySelectorAll('.section');

        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);

                // Update active nav link
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');

                // Update active section
                sections.forEach(s => s.classList.remove('active'));
                document.getElementById(targetId).classList.add('active');

                // Load section data
                if (targetId === 'backups') {
                    this.loadBackups();
                } else if (targetId === 'players') {
                    this.loadPlayers();
                } else if (targetId === 'worlds') {
                    this.loadWorlds();
                } else if (targetId === 'tasks') {
                    this.loadTasks();
                } else if (targetId === 'files') {
                    this.loadFiles();
                } else if (targetId === 'modrinth') {
                    // Modrinth section loaded
                }
            });
        });
    }

    // Event Listeners
    setupEventListeners() {
        // Control buttons
        document.getElementById('startBtn').addEventListener('click', () => this.startServer());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopServer());
        document.getElementById('restartBtn').addEventListener('click', () => this.restartServer());

        // Console command
        document.getElementById('sendCommand').addEventListener('click', () => this.sendCommand());
        document.getElementById('commandInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendCommand();
        });

        // Settings form
        document.getElementById('settingsForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveSettings();
        });

        // Backup button
        document.getElementById('createBackupBtn').addEventListener('click', () => this.createBackup());

        // Players buttons
        document.getElementById('refreshPlayersBtn').addEventListener('click', () => this.loadPlayers());

        // Worlds button
        document.getElementById('refreshWorldsBtn').addEventListener('click', () => this.loadWorlds());

        // Tasks buttons
        document.getElementById('createTaskBtn').addEventListener('click', () => this.openTaskModal());
        const taskType = document.getElementById('taskType');
        if (taskType) {
            taskType.addEventListener('change', (e) => {
                const commandGroup = document.getElementById('taskCommandGroup');
                commandGroup.style.display = e.target.value === 'command' ? 'block' : 'none';
            });
        }
    }

    // Setup Tabs
    setupTabs() {
        const tabs = document.querySelectorAll('.tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.getAttribute('data-tab');

                // Update active tab
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Update active content
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                document.getElementById(`${tabName}-tab`).classList.add('active');

                // Load data for tab
                if (tabName === 'installed-mods') {
                    this.loadInstalledMods('mods');
                } else if (tabName === 'installed-plugins') {
                    this.loadInstalledMods('plugins');
                } else if (tabName === 'installed-datapacks') {
                    this.loadInstalledMods('datapacks');
                }
            });
        });
    }

    // WebSocket Connection
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/console`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
        };

        this.ws.onmessage = (event) => {
            this.appendConsoleLog(event.data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            // Reconnect after 5 seconds
            setTimeout(() => this.connectWebSocket(), 5000);
        };
    }

    // API Calls
    async apiCall(endpoint, method = 'GET', data = null) {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(`${this.apiBase}/api${endpoint}`, options);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            this.showNotification(`오류: ${error.message}`, 'error');
            throw error;
        }
    }

    // Load Initial Data
    async loadInitialData() {
        await this.updateStatus();
        await this.loadConfig();
    }

    // Server Control
    async startServer() {
        try {
            await this.apiCall('/server/start', 'POST');
            this.showNotification('서버를 시작하는 중...', 'success');
            setTimeout(() => this.updateStatus(), 2000);
        } catch (error) {
            console.error('Failed to start server:', error);
        }
    }

    async stopServer() {
        try {
            await this.apiCall('/server/stop', 'POST');
            this.showNotification('서버를 중지하는 중...', 'warning');
            setTimeout(() => this.updateStatus(), 2000);
        } catch (error) {
            console.error('Failed to stop server:', error);
        }
    }

    async restartServer() {
        try {
            await this.apiCall('/server/restart', 'POST');
            this.showNotification('서버를 재시작하는 중...', 'info');
            setTimeout(() => this.updateStatus(), 2000);
        } catch (error) {
            console.error('Failed to restart server:', error);
        }
    }

    // Status Updates
    startStatusUpdates() {
        this.updateInterval = setInterval(() => this.updateStatus(), 5000);
    }

    async updateStatus() {
        try {
            const status = await this.apiCall('/status');
            this.updateUI(status);
        } catch (error) {
            console.error('Failed to update status:', error);
        }
    }

    updateUI(status) {
        // Update status indicator
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');

        if (status.is_running) {
            statusDot.className = 'status-dot online';
            statusText.textContent = '서버 온라인';
        } else {
            statusDot.className = 'status-dot offline';
            statusText.textContent = '서버 오프라인';
        }

        // Update control buttons
        document.getElementById('startBtn').disabled = status.is_running;
        document.getElementById('stopBtn').disabled = !status.is_running;
        document.getElementById('restartBtn').disabled = !status.is_running;
        document.getElementById('commandInput').disabled = !status.is_running;
        document.getElementById('sendCommand').disabled = !status.is_running;

        // Update stats
        document.getElementById('playerCount').textContent = status.player_count;
        document.getElementById('maxPlayers').textContent = status.max_players;
        document.getElementById('uptime').textContent = this.formatUptime(status.uptime);
        document.getElementById('memory').textContent =
            `${status.memory_usage.toFixed(0)} MB / ${status.memory_total.toFixed(0)} MB`;
        document.getElementById('cpu').textContent = `${status.cpu_usage.toFixed(1)}%`;

        // Update server info
        if (status.version) {
            document.getElementById('version').textContent = status.version;
        }
    }

    formatUptime(seconds) {
        if (!seconds || seconds === 0) return '0분';

        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);

        if (hours > 0) {
            return `${hours}시간 ${minutes}분`;
        } else {
            return `${minutes}분`;
        }
    }

    // Console
    appendConsoleLog(message) {
        const consoleOutput = document.getElementById('consoleOutput');
        const line = document.createElement('div');
        line.className = 'console-line';

        // Colorize log levels
        if (message.includes('[ERROR]') || message.includes('ERROR')) {
            line.classList.add('error');
        } else if (message.includes('[WARN]') || message.includes('WARN')) {
            line.classList.add('warning');
        } else if (message.includes('[INFO]')) {
            line.classList.add('info');
        }

        line.textContent = message;
        consoleOutput.appendChild(line);

        // Auto-scroll to bottom
        consoleOutput.scrollTop = consoleOutput.scrollHeight;

        // Keep only last 1000 lines
        while (consoleOutput.children.length > 1000) {
            consoleOutput.removeChild(consoleOutput.firstChild);
        }
    }

    async sendCommand() {
        const input = document.getElementById('commandInput');
        const command = input.value.trim();

        if (!command) return;

        try {
            await this.apiCall('/server/command', 'POST', { command });
            this.appendConsoleLog(`> ${command}`);
            input.value = '';
        } catch (error) {
            console.error('Failed to send command:', error);
        }
    }

    // Settings
    async loadConfig() {
        try {
            const config = await this.apiCall('/config');
            this.populateSettings(config);
        } catch (error) {
            console.error('Failed to load config:', error);
        }
    }

    populateSettings(config) {
        document.getElementById('serverName').value = config.server_name;
        document.getElementById('maxPlayersInput').value = config.max_players;
        document.getElementById('gamemodeInput').value = config.gamemode;
        document.getElementById('difficultyInput').value = config.difficulty;
        document.getElementById('motd').value = config.motd;
        document.getElementById('viewDistance').value = config.view_distance;
        document.getElementById('memory').value = config.memory;
        document.getElementById('pvp').checked = config.pvp;
        document.getElementById('onlineMode').checked = config.online_mode;

        // Update dashboard info
        document.getElementById('gamemode').textContent =
            config.gamemode.charAt(0).toUpperCase() + config.gamemode.slice(1);
        document.getElementById('difficulty').textContent =
            config.difficulty.charAt(0).toUpperCase() + config.difficulty.slice(1);
    }

    async saveSettings() {
        const config = {
            server_name: document.getElementById('serverName').value,
            max_players: parseInt(document.getElementById('maxPlayersInput').value),
            gamemode: document.getElementById('gamemodeInput').value,
            difficulty: document.getElementById('difficultyInput').value,
            motd: document.getElementById('motd').value,
            view_distance: parseInt(document.getElementById('viewDistance').value),
            memory: document.getElementById('memory').value,
            pvp: document.getElementById('pvp').checked,
            online_mode: document.getElementById('onlineMode').checked,
            minecraft_version: "1.20.1"
        };

        try {
            await this.apiCall('/config', 'POST', config);
            this.showNotification('설정이 저장되었습니다', 'success');
            await this.loadConfig();
        } catch (error) {
            console.error('Failed to save config:', error);
        }
    }

    // Backups
    async loadBackups() {
        try {
            const backups = await this.apiCall('/backups');
            this.displayBackups(backups);
        } catch (error) {
            console.error('Failed to load backups:', error);
        }
    }

    displayBackups(backups) {
        const backupsList = document.getElementById('backupsList');

        if (backups.length === 0) {
            backupsList.innerHTML = `
                <div class="empty-state">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    <p>백업이 없습니다</p>
                </div>
            `;
            return;
        }

        backupsList.innerHTML = backups.map(backup => `
            <div class="backup-item">
                <div class="backup-info">
                    <div class="backup-name">${backup.name}</div>
                    <div class="backup-meta">
                        ${new Date(backup.created_at).toLocaleString('ko-KR')} •
                        ${this.formatBytes(backup.size)}
                    </div>
                </div>
                <div class="backup-actions">
                    <button class="btn btn-primary" onclick="app.restoreBackup('${backup.name}')">
                        복원
                    </button>
                </div>
            </div>
        `).join('');
    }

    async createBackup() {
        try {
            const result = await this.apiCall('/backup', 'POST');
            this.showNotification(`백업이 생성되었습니다: ${result.backup}`, 'success');
            await this.loadBackups();
        } catch (error) {
            console.error('Failed to create backup:', error);
        }
    }

    async restoreBackup(backupName) {
        if (!confirm(`백업 "${backupName}"을(를) 복원하시겠습니까? 현재 데이터가 덮어씌워집니다.`)) {
            return;
        }

        try {
            await this.apiCall('/backup/restore', 'POST', { name: backupName });
            this.showNotification('백업이 복원되었습니다', 'success');
        } catch (error) {
            console.error('Failed to restore backup:', error);
        }
    }

    // Utilities
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    showNotification(message, type = 'info') {
        // Simple console notification for now
        // Can be enhanced with a toast notification system
        console.log(`[${type.toUpperCase()}] ${message}`);

        // Create a simple toast
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            padding: 1rem 1.5rem;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            box-shadow: var(--shadow-lg);
            z-index: 9999;
            animation: slideIn 0.3s ease-out;
        `;
        toast.textContent = message;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // Players Management
    async loadPlayers() {
        try {
            const [allPlayers, onlinePlayers] = await Promise.all([
                this.apiCall('/players'),
                this.apiCall('/players/online')
            ]);
            this.displayPlayers(allPlayers, onlinePlayers);
        } catch (error) {
            console.error('Failed to load players:', error);
        }
    }

    displayPlayers(allPlayers, onlinePlayers) {
        const onlineList = document.getElementById('onlinePlayersList');
        const allList = document.getElementById('allPlayersList');

        // Online players
        if (onlinePlayers.length === 0) {
            onlineList.innerHTML = '<div class="empty-state"><p>온라인 플레이어가 없습니다</p></div>';
        } else {
            onlineList.innerHTML = onlinePlayers.map(player => this.playerItemHTML(player, true)).join('');
        }

        // All players
        if (allPlayers.length === 0) {
            allList.innerHTML = '<div class="empty-state"><p>플레이어 정보가 없습니다</p></div>';
        } else {
            allList.innerHTML = allPlayers.map(player => this.playerItemHTML(player, false)).join('');
        }
    }

    playerItemHTML(player, isOnline) {
        return `
            <div class="player-item" onclick="app.openPlayerModal('${player.name}')">
                <div class="player-info">
                    <div class="player-avatar"></div>
                    <div class="player-details">
                        <div class="player-name">${player.name}</div>
                        <div class="player-meta">
                            UUID: ${player.uuid.substring(0, 8)}...
                            ${!isOnline && player.last_seen ? ` • 마지막 접속: ${new Date(player.last_seen).toLocaleString('ko-KR')}` : ''}
                        </div>
                    </div>
                </div>
                <span class="player-status ${isOnline ? 'online' : 'offline'}">
                    ${isOnline ? '온라인' : '오프라인'}
                </span>
            </div>
        `;
    }

    openPlayerModal(playerName) {
        this.currentPlayer = playerName;
        document.getElementById('modalPlayerName').textContent = playerName;
        document.getElementById('playerModal').style.display = 'flex';
    }

    closePlayerModal() {
        document.getElementById('playerModal').style.display = 'none';
    }

    async kickPlayer() {
        try {
            await this.apiCall(`/players/${this.currentPlayer}/action`, 'POST', {
                action: 'kick',
                params: { reason: '관리자에 의해 킥됨' }
            });
            this.showNotification(`${this.currentPlayer}를 킥했습니다`, 'success');
            this.closePlayerModal();
        } catch (error) {
            console.error('Failed to kick player:', error);
        }
    }

    async banPlayer() {
        try {
            await this.apiCall(`/players/${this.currentPlayer}/action`, 'POST', {
                action: 'ban',
                params: { reason: '관리자에 의해 밴됨' }
            });
            this.showNotification(`${this.currentPlayer}를 밴했습니다`, 'success');
            this.closePlayerModal();
        } catch (error) {
            console.error('Failed to ban player:', error);
        }
    }

    async opPlayer() {
        try {
            await this.apiCall(`/players/${this.currentPlayer}/action`, 'POST', {
                action: 'op'
            });
            this.showNotification(`${this.currentPlayer}에게 OP를 부여했습니다`, 'success');
            this.closePlayerModal();
        } catch (error) {
            console.error('Failed to op player:', error);
        }
    }

    async whitelistPlayer() {
        try {
            await this.apiCall(`/players/${this.currentPlayer}/action`, 'POST', {
                action: 'whitelist_add'
            });
            this.showNotification(`${this.currentPlayer}를 화이트리스트에 추가했습니다`, 'success');
            this.closePlayerModal();
        } catch (error) {
            console.error('Failed to whitelist player:', error);
        }
    }

    async giveItem() {
        const itemName = document.getElementById('itemName').value;
        const itemAmount = parseInt(document.getElementById('itemAmount').value);

        if (!itemName) return;

        try {
            await this.apiCall(`/players/${this.currentPlayer}/give`, 'POST', {
                item: itemName,
                amount: itemAmount
            });
            this.showNotification(`${this.currentPlayer}에게 ${itemName} x${itemAmount}을 지급했습니다`, 'success');
            document.getElementById('itemName').value = '';
            document.getElementById('itemAmount').value = '1';
        } catch (error) {
            console.error('Failed to give item:', error);
        }
    }

    // Worlds Management
    async loadWorlds() {
        try {
            const worlds = await this.apiCall('/worlds');
            this.displayWorlds(worlds);
        } catch (error) {
            console.error('Failed to load worlds:', error);
        }
    }

    displayWorlds(worlds) {
        const worldsList = document.getElementById('worldsList');

        if (worlds.length === 0) {
            worldsList.innerHTML = '<div class="empty-state"><p>월드가 없습니다</p></div>';
            return;
        }

        worldsList.innerHTML = worlds.map(world => `
            <div class="world-card">
                <div class="world-header">
                    <div class="world-name">${world.name}</div>
                </div>
                <div class="world-info">
                    <div class="world-info-item">
                        <span class="world-info-label">크기</span>
                        <span class="world-info-value">${this.formatBytes(world.size)}</span>
                    </div>
                    <div class="world-info-item">
                        <span class="world-info-label">마지막 수정</span>
                        <span class="world-info-value">${new Date(world.last_modified).toLocaleString('ko-KR')}</span>
                    </div>
                    ${world.seed ? `
                    <div class="world-info-item">
                        <span class="world-info-label">시드</span>
                        <span class="world-info-value">${world.seed}</span>
                    </div>
                    ` : ''}
                </div>
                <div class="world-actions">
                    <button class="btn btn-danger btn-sm" onclick="app.deleteWorld('${world.name}')">삭제</button>
                    <button class="btn btn-warning btn-sm" onclick="app.resetWorld('${world.name}')">리셋</button>
                </div>
            </div>
        `).join('');
    }

    async deleteWorld(worldName) {
        if (!confirm(`"${worldName}" 월드를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
            return;
        }

        try {
            await this.apiCall(`/worlds/${worldName}`, 'DELETE');
            this.showNotification(`${worldName} 월드를 삭제했습니다`, 'success');
            await this.loadWorlds();
        } catch (error) {
            console.error('Failed to delete world:', error);
        }
    }

    async resetWorld(worldName) {
        if (!confirm(`"${worldName}" 월드를 리셋하시겠습니까? 모든 데이터가 삭제됩니다.`)) {
            return;
        }

        try {
            await this.apiCall(`/worlds/${worldName}/reset`, 'POST');
            this.showNotification(`${worldName} 월드를 리셋했습니다`, 'success');
            await this.loadWorlds();
        } catch (error) {
            console.error('Failed to reset world:', error);
        }
    }

    // Scheduled Tasks
    async loadTasks() {
        try {
            const tasks = await this.apiCall('/tasks');
            this.displayTasks(tasks);
        } catch (error) {
            console.error('Failed to load tasks:', error);
        }
    }

    displayTasks(tasks) {
        const tasksList = document.getElementById('tasksList');

        if (tasks.length === 0) {
            tasksList.innerHTML = '<div class="empty-state"><p>스케줄 작업이 없습니다</p></div>';
            return;
        }

        tasksList.innerHTML = tasks.map(task => `
            <div class="task-item">
                <div class="task-info">
                    <div class="task-name">
                        ${task.name}
                        <span class="task-badge ${task.enabled ? 'enabled' : 'disabled'}">
                            ${task.enabled ? '활성' : '비활성'}
                        </span>
                    </div>
                    <div class="task-meta">
                        유형: ${task.task_type} • 스케줄: ${task.schedule}
                        ${task.last_run ? ` • 마지막 실행: ${new Date(task.last_run).toLocaleString('ko-KR')}` : ''}
                    </div>
                </div>
                <div class="task-actions">
                    <button class="btn btn-danger btn-sm" onclick="app.deleteTask('${task.id}')">삭제</button>
                </div>
            </div>
        `).join('');
    }

    openTaskModal() {
        document.getElementById('taskModal').style.display = 'flex';
    }

    closeTaskModal() {
        document.getElementById('taskModal').style.display = 'none';
        document.getElementById('taskName').value = '';
        document.getElementById('taskSchedule').value = '';
        document.getElementById('taskCommand').value = '';
    }

    async saveTask() {
        const name = document.getElementById('taskName').value;
        const taskType = document.getElementById('taskType').value;
        const schedule = document.getElementById('taskSchedule').value;
        const command = document.getElementById('taskCommand').value;

        if (!name || !schedule) {
            this.showNotification('작업 이름과 스케줄을 입력하세요', 'error');
            return;
        }

        const task = {
            id: '',
            name: name,
            task_type: taskType,
            schedule: schedule,
            enabled: true,
            params: taskType === 'command' ? { command: command } : {}
        };

        try {
            await this.apiCall('/tasks', 'POST', task);
            this.showNotification('스케줄 작업이 생성되었습니다', 'success');
            this.closeTaskModal();
            await this.loadTasks();
        } catch (error) {
            console.error('Failed to create task:', error);
        }
    }

    async deleteTask(taskId) {
        if (!confirm('이 스케줄 작업을 삭제하시겠습니까?')) {
            return;
        }

        try {
            await this.apiCall(`/tasks/${taskId}`, 'DELETE');
            this.showNotification('스케줄 작업이 삭제되었습니다', 'success');
            await this.loadTasks();
        } catch (error) {
            console.error('Failed to delete task:', error);
        }
    }

    // File Manager
    async loadFiles(path = '') {
        try {
            const files = await this.apiCall(`/files?path=${encodeURIComponent(path)}`);
            this.currentPath = path;
            this.displayFiles(files);
        } catch (error) {
            console.error('Failed to load files:', error);
        }
    }

    displayFiles(files) {
        const filesList = document.getElementById('filesList');
        const currentPath = document.getElementById('currentPath');

        // Update breadcrumb
        const pathParts = this.currentPath ? this.currentPath.split('/') : [];
        currentPath.innerHTML = `
            <span class="breadcrumb-item" onclick="app.loadFiles('')">📁 Home</span>
            ${pathParts.map((part, i) => `
                <span> / </span>
                <span class="breadcrumb-item" onclick="app.loadFiles('${pathParts.slice(0, i + 1).join('/')}')">${part}</span>
            `).join('')}
        `;

        if (files.length === 0) {
            filesList.innerHTML = '<div class="empty-state"><p>파일이 없습니다</p></div>';
            return;
        }

        filesList.innerHTML = files.map(file => `
            <div class="file-item" onclick="app.${file.is_directory ? `loadFiles('${file.path}')` : `openFile('${file.path}')`}">
                <div class="file-icon">
                    <span>${file.is_directory ? '📁' : '📄'}</span>
                    <span class="file-name ${file.is_directory ? 'directory' : ''}">${file.name}</span>
                </div>
                <div class="file-meta">
                    ${!file.is_directory ? `<span>${this.formatBytes(file.size)}</span>` : ''}
                    <span>${new Date(file.modified).toLocaleString('ko-KR')}</span>
                </div>
            </div>
        `).join('');
    }

    async openFile(path) {
        try {
            const content = await this.apiCall(`/files/read?path=${encodeURIComponent(path)}`);
            this.currentFilePath = path;
            document.getElementById('editorFileName').textContent = path;
            document.getElementById('fileContent').value = content;
            document.getElementById('fileEditorModal').style.display = 'flex';
        } catch (error) {
            console.error('Failed to open file:', error);
            this.showNotification('파일을 열 수 없습니다', 'error');
        }
    }

    closeFileEditor() {
        document.getElementById('fileEditorModal').style.display = 'none';
    }

    async saveFile() {
        const content = document.getElementById('fileContent').value;

        try {
            await this.apiCall('/files/write', 'POST', {
                path: this.currentFilePath,
                content: content
            });
            this.showNotification('파일이 저장되었습니다', 'success');
            this.closeFileEditor();
        } catch (error) {
            console.error('Failed to save file:', error);
        }
    }

    // Multi-Source Integration
    async searchModrinth() {
        const query = document.getElementById('modrinthSearch').value;
        const source = document.getElementById('searchSource').value || 'modrinth';
        const projectType = document.getElementById('projectType').value;

        if (!query) {
            this.showNotification('검색어를 입력하세요', 'error');
            return;
        }

        try {
            const projects = await this.apiCall(
                `/projects/search?query=${encodeURIComponent(query)}&source=${source}${projectType ? `&project_type=${projectType}` : ''}`
            );
            this.displaySearchResults(projects);
        } catch (error) {
            console.error('Failed to search:', error);
        }
    }

    displaySearchResults(projects) {
        const searchResults = document.getElementById('searchResults');

        if (projects.length === 0) {
            searchResults.innerHTML = '<div class="empty-state"><p>검색 결과가 없습니다</p></div>';
            return;
        }

        const sourceLabels = {
            'modrinth': 'Modrinth',
            'curseforge': 'CurseForge',
            'spigot': 'Spigot'
        };

        const sourceColors = {
            'modrinth': '#1BD96A',
            'curseforge': '#F16436',
            'spigot': '#FFB61C'
        };

        searchResults.innerHTML = projects.map(project => `
            <div class="mod-card">
                <div class="mod-header">
                    <div class="mod-icon">
                        ${project.icon_url ? `<img src="${project.icon_url}" alt="${project.title}">` : ''}
                    </div>
                    <div class="mod-title-section">
                        <div class="mod-title">${project.title}</div>
                        <div class="mod-author">by ${project.author}</div>
                    </div>
                </div>
                <p class="mod-description">${project.description}</p>
                <div class="mod-meta">
                    <span class="mod-badge">${project.project_type}</span>
                    <span class="mod-badge" style="background-color: ${sourceColors[project.source] || '#666'}33; color: ${sourceColors[project.source] || '#999'};">${sourceLabels[project.source] || project.source}</span>
                    <span>📥 ${this.formatDownloads(project.downloads)}</span>
                </div>
                <div class="mod-actions">
                    <button class="btn btn-success" onclick="app.showInstallModal('${project.id}', '${project.title}', '${project.project_type}', '${project.source}')">
                        설치
                    </button>
                </div>
            </div>
        `).join('');
    }

    async showInstallModal(projectId, projectName, projectType, source) {
        this.currentInstallProject = { id: projectId, name: projectName, type: projectType, source: source || 'modrinth' };
        document.getElementById('installProjectName').textContent = projectName;
        document.getElementById('installModal').style.display = 'flex';

        // Load versions
        try {
            const versions = await this.apiCall(`/modrinth/project/${projectId}/versions`);
            this.displayVersions(versions);
        } catch (error) {
            console.error('Failed to load versions:', error);
        }
    }

    displayVersions(versions) {
        const versionsList = document.getElementById('versionsList');

        if (versions.length === 0) {
            versionsList.innerHTML = '<p>사용 가능한 버전이 없습니다</p>';
            return;
        }

        versionsList.innerHTML = versions.map(version => `
            <div class="version-item">
                <div class="version-info">
                    <div class="version-name">${version.name}</div>
                    <div class="version-meta">
                        버전: ${version.version_number} •
                        로더: ${version.loaders.join(', ')} •
                        게임 버전: ${version.game_versions.join(', ')}
                    </div>
                </div>
                <button class="btn btn-primary btn-sm" onclick="app.installVersion('${version.id}')">
                    설치
                </button>
            </div>
        `).join('');
    }

    async installVersion(versionId) {
        try {
            const installType = this.currentInstallProject.type === 'mod' ? 'mods' :
                              this.currentInstallProject.type === 'plugin' ? 'plugins' :
                              'datapacks';

            await this.apiCall('/modrinth/install', 'POST', {
                version_id: versionId,
                type: installType
            });

            this.showNotification(`${this.currentInstallProject.name}이(가) 설치되었습니다`, 'success');
            this.closeInstallModal();
        } catch (error) {
            console.error('Failed to install:', error);
        }
    }

    closeInstallModal() {
        document.getElementById('installModal').style.display = 'none';
    }

    async loadInstalledMods(modType) {
        try {
            const mods = await this.apiCall(`/modrinth/installed/${modType}`);
            this.displayInstalledMods(mods, modType);
        } catch (error) {
            console.error('Failed to load installed mods:', error);
        }
    }

    displayInstalledMods(mods, modType) {
        const listId = modType === 'mods' ? 'installedModsList' :
                      modType === 'plugins' ? 'installedPluginsList' :
                      'installedDatapacksList';

        const list = document.getElementById(listId);

        if (mods.length === 0) {
            const typeName = modType === 'mods' ? '모드' :
                           modType === 'plugins' ? '플러그인' :
                           '데이터팩';
            list.innerHTML = `<div class="empty-state"><p>설치된 ${typeName}가 없습니다</p></div>`;
            return;
        }

        list.innerHTML = mods.map(mod => `
            <div class="installed-mod-item">
                <div class="installed-mod-info">
                    <div class="installed-mod-name">${mod.name}</div>
                    <div class="installed-mod-meta">
                        ${this.formatBytes(mod.size)} •
                        설치: ${new Date(mod.installed_date).toLocaleString('ko-KR')}
                    </div>
                </div>
                <button class="btn btn-danger btn-sm" onclick="app.uninstallMod('${mod.filename}', '${modType}')">
                    제거
                </button>
            </div>
        `).join('');
    }

    async uninstallMod(filename, modType) {
        if (!confirm(`${filename}을(를) 제거하시겠습니까?`)) {
            return;
        }

        try {
            await this.apiCall(`/modrinth/installed/${modType}/${filename}`, 'DELETE');
            this.showNotification(`${filename}이(가) 제거되었습니다`, 'success');
            await this.loadInstalledMods(modType);
        } catch (error) {
            console.error('Failed to uninstall mod:', error);
        }
    }

    formatDownloads(downloads) {
        if (downloads >= 1000000) {
            return (downloads / 1000000).toFixed(1) + 'M';
        } else if (downloads >= 1000) {
            return (downloads / 1000).toFixed(1) + 'K';
        }
        return downloads.toString();
    }

    // Modpack Management
    async searchModpacks() {
        const query = document.getElementById('modpackSearch').value;
        const source = document.getElementById('modpackSource').value || 'modrinth';
        const loader = document.getElementById('modpackLoader').value;

        if (!query) {
            this.showNotification('검색어를 입력하세요', 'error');
            return;
        }

        try {
            let url = `/projects/search?query=${encodeURIComponent(query)}&source=${source}&project_type=modpack`;
            if (loader) {
                url += `&loader=${loader}`;
            }

            const modpacks = await this.apiCall(url);
            this.displayModpackResults(modpacks);
        } catch (error) {
            console.error('Failed to search modpacks:', error);
        }
    }

    displayModpackResults(modpacks) {
        const modpackResults = document.getElementById('modpackResults');

        if (modpacks.length === 0) {
            modpackResults.innerHTML = '<div class="empty-state"><p>검색 결과가 없습니다</p></div>';
            return;
        }

        const sourceLabels = {
            'modrinth': 'Modrinth',
            'curseforge': 'CurseForge'
        };

        const sourceColors = {
            'modrinth': '#1BD96A',
            'curseforge': '#F16436'
        };

        modpackResults.innerHTML = modpacks.map(modpack => `
            <div class="mod-card">
                <div class="mod-header">
                    <div class="mod-icon">
                        ${modpack.icon_url ? `<img src="${modpack.icon_url}" alt="${modpack.title}">` : ''}
                    </div>
                    <div class="mod-title-section">
                        <div class="mod-title">${modpack.title}</div>
                        <div class="mod-author">by ${modpack.author}</div>
                    </div>
                </div>
                <p class="mod-description">${modpack.description}</p>
                <div class="mod-meta">
                    <span class="mod-badge">모드팩</span>
                    <span class="mod-badge" style="background-color: ${sourceColors[modpack.source] || '#666'}33; color: ${sourceColors[modpack.source] || '#999'};">${sourceLabels[modpack.source] || modpack.source}</span>
                    <span>📥 ${this.formatDownloads(modpack.downloads)}</span>
                </div>
                <div class="mod-actions">
                    <button class="btn btn-success" onclick="app.showModpackModal('${modpack.id}', '${modpack.title.replace(/'/g, "\\'")}', '${modpack.source}')">
                        서버 생성
                    </button>
                </div>
            </div>
        `).join('');
    }

    async showModpackModal(modpackId, modpackName, source) {
        this.currentModpack = { id: modpackId, name: modpackName, source: source || 'modrinth' };
        document.getElementById('modpackName').textContent = modpackName;
        document.getElementById('modpackServerName').value = modpackName + ' Server';
        document.getElementById('modpackModal').style.display = 'flex';

        // Load modpack versions
        try {
            const versions = await this.apiCall(`/modrinth/project/${modpackId}/versions`);
            const versionSelect = document.getElementById('modpackVersion');

            if (versions.length === 0) {
                versionSelect.innerHTML = '<option value="">사용 가능한 버전이 없습니다</option>';
                return;
            }

            versionSelect.innerHTML = versions.map(version => `
                <option value="${version.id}">
                    ${version.name} - ${version.game_versions.join(', ')} (${version.loaders.join(', ')})
                </option>
            `).join('');
        } catch (error) {
            console.error('Failed to load modpack versions:', error);
        }
    }

    closeModpackModal() {
        document.getElementById('modpackModal').style.display = 'none';
    }

    async createModpackServer() {
        const versionId = document.getElementById('modpackVersion').value;
        const serverName = document.getElementById('modpackServerName').value;
        const memory = document.getElementById('modpackMemory').value;

        if (!versionId) {
            this.showNotification('버전을 선택하세요', 'error');
            return;
        }

        if (!serverName) {
            this.showNotification('서버 이름을 입력하세요', 'error');
            return;
        }

        if (!confirm('현재 서버가 중지되고 새 모드팩 서버가 생성됩니다. 계속하시겠습니까?')) {
            return;
        }

        try {
            this.showNotification('모드팩 서버를 생성하는 중... 시간이 걸릴 수 있습니다.', 'info');
            this.closeModpackModal();

            const result = await this.apiCall('/modrinth/create-modpack-server', 'POST', {
                version_id: versionId,
                server_name: serverName,
                memory: memory
            });

            this.showNotification('모드팩 서버가 성공적으로 생성되었습니다!', 'success');
            await this.updateStatus();
            await this.loadConfig();
        } catch (error) {
            console.error('Failed to create modpack server:', error);
            this.showNotification('모드팩 서버 생성에 실패했습니다', 'error');
        }
    }
}

// Initialize app
const app = new CraftServerApp();

// Add toast animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
