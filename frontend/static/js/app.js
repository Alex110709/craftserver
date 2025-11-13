// CraftServer Manager - Frontend Application

class CraftServerApp {
    constructor() {
        this.apiBase = '';
        this.ws = null;
        this.updateInterval = null;
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupEventListeners();
        this.connectWebSocket();
        this.startStatusUpdates();
        this.loadInitialData();
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
