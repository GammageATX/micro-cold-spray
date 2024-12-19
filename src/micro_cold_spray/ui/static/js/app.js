// MCS Control UI JavaScript

class MCSControlUI {
    constructor() {
        this.apiUrls = JSON.parse(document.getElementById('apiUrls').dataset.urls);
        this.connectionStatus = document.getElementById('connectionStatus');
        this.systemInfo = document.getElementById('systemInfo');
        this.uptimeDisplay = document.getElementById('uptimeDisplay');
        this.tagUpdateInterval = 1000; // 1 second
        this.stateUpdateInterval = 2000; // 2 seconds
        this.startTime = Date.now();
        
        // WebSocket connections
        this.tagSocket = null;
        this.stateSocket = null;
        
        // Initialize
        this.init();
    }
    
    init() {
        // Initialize WebSocket connections
        this.initializeWebSockets();
        
        // Start update loops
        this.startUpdateLoops();
        
        // Initialize event listeners
        this.initializeEventListeners();
        
        // Update system info
        this.updateSystemInfo();
    }
    
    initializeWebSockets() {
        // Tag WebSocket
        if (window.location.pathname === '/tags') {
            this.tagSocket = new WebSocket(this.apiUrls.communication.replace('http', 'ws') + '/ws/tags');
            this.tagSocket.onmessage = (event) => this.handleTagUpdate(JSON.parse(event.data));
            this.tagSocket.onclose = () => this.handleConnectionLoss('tags');
        }
        
        // State WebSocket
        if (window.location.pathname === '/system/state') {
            this.stateSocket = new WebSocket(this.apiUrls.state.replace('http', 'ws') + '/ws/state');
            this.stateSocket.onmessage = (event) => this.handleStateUpdate(JSON.parse(event.data));
            this.stateSocket.onclose = () => this.handleConnectionLoss('state');
        }
    }
    
    startUpdateLoops() {
        // Update uptime display
        setInterval(() => this.updateUptime(), 1000);
        
        // Update system info periodically
        setInterval(() => this.updateSystemInfo(), 30000);
    }
    
    initializeEventListeners() {
        // Tag write form submission
        document.querySelectorAll('.tag-write-form').forEach(form => {
            form.addEventListener('submit', (e) => this.handleTagWrite(e));
        });
        
        // Config editor save
        document.querySelectorAll('.config-save-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleConfigSave(e));
        });
        
        // Service control buttons
        document.querySelectorAll('.service-control-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleServiceControl(e));
        });
    }
    
    async updateSystemInfo() {
        try {
            const response = await fetch(this.apiUrls.state + '/info');
            const data = await response.json();
            
            if (this.systemInfo) {
                this.systemInfo.innerHTML = `
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <tbody>
                                <tr>
                                    <th>System Version</th>
                                    <td>${data.version}</td>
                                </tr>
                                <tr>
                                    <th>Services Status</th>
                                    <td>${this.formatServiceStatus(data.services)}</td>
                                </tr>
                                <tr>
                                    <th>Active Tags</th>
                                    <td>${data.active_tags}</td>
                                </tr>
                                <tr>
                                    <th>Memory Usage</th>
                                    <td>${this.formatBytes(data.memory_usage)}</td>
                                </tr>
                                <tr>
                                    <th>CPU Usage</th>
                                    <td>${data.cpu_usage}%</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                `;
            }
            
            this.updateConnectionStatus('connected');
        } catch (error) {
            console.error('Failed to update system info:', error);
            this.updateConnectionStatus('disconnected');
        }
    }
    
    updateUptime() {
        const uptime = Math.floor((Date.now() - this.startTime) / 1000);
        const hours = Math.floor(uptime / 3600);
        const minutes = Math.floor((uptime % 3600) / 60);
        const seconds = uptime % 60;
        
        if (this.uptimeDisplay) {
            this.uptimeDisplay.textContent = `Uptime: ${hours}h ${minutes}m ${seconds}s`;
        }
    }
    
    updateConnectionStatus(status) {
        if (this.connectionStatus) {
            this.connectionStatus.className = `status-badge ${status}`;
            this.connectionStatus.innerHTML = `
                <i class="fas fa-circle"></i>
                ${status.charAt(0).toUpperCase() + status.slice(1)}
            `;
        }
    }
    
    async handleTagWrite(event) {
        event.preventDefault();
        const form = event.target;
        const tagPath = form.dataset.tagPath;
        const value = form.querySelector('input[name="value"]').value;
        
        try {
            const response = await fetch(this.apiUrls.communication + '/tags/write', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tag_path: tagPath,
                    value: value
                })
            });
            
            if (!response.ok) throw new Error('Failed to write tag value');
            
            this.showAlert('success', `Successfully wrote value to ${tagPath}`);
        } catch (error) {
            console.error('Tag write error:', error);
            this.showAlert('danger', `Failed to write value to ${tagPath}: ${error.message}`);
        }
    }
    
    async handleConfigSave(event) {
        const configType = event.target.dataset.configType;
        const editor = document.querySelector('.config-editor');
        const content = editor.value;
        
        try {
            const response = await fetch(this.apiUrls.config + '/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    type: configType,
                    content: content
                })
            });
            
            if (!response.ok) throw new Error('Failed to save configuration');
            
            this.showAlert('success', 'Configuration saved successfully');
        } catch (error) {
            console.error('Config save error:', error);
            this.showAlert('danger', `Failed to save configuration: ${error.message}`);
        }
    }
    
    async handleServiceControl(event) {
        const action = event.target.dataset.action;
        const service = event.target.dataset.service;
        
        try {
            const response = await fetch(this.apiUrls[service] + '/control', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ action })
            });
            
            if (!response.ok) throw new Error(`Failed to ${action} service`);
            
            this.showAlert('success', `Successfully ${action}ed ${service} service`);
        } catch (error) {
            console.error('Service control error:', error);
            this.showAlert('danger', `Failed to ${action} ${service} service: ${error.message}`);
        }
    }
    
    handleTagUpdate(data) {
        const tagElement = document.querySelector(`[data-tag-path="${data.tag_path}"]`);
        if (tagElement) {
            const valueElement = tagElement.querySelector('.tag-value');
            const timestampElement = tagElement.querySelector('.tag-timestamp');
            
            valueElement.textContent = this.formatTagValue(data.value, data.type);
            timestampElement.textContent = new Date(data.timestamp).toLocaleString();
            
            // Flash animation
            valueElement.classList.add('updating');
            setTimeout(() => valueElement.classList.remove('updating'), 1000);
        }
    }
    
    handleStateUpdate(data) {
        Object.entries(data).forEach(([key, value]) => {
            const stateElement = document.querySelector(`[data-state-key="${key}"]`);
            if (stateElement) {
                const valueElement = stateElement.querySelector('.state-value');
                valueElement.textContent = this.formatStateValue(value);
                
                // Flash animation
                valueElement.classList.add('updating');
                setTimeout(() => valueElement.classList.remove('updating'), 1000);
            }
        });
    }
    
    handleConnectionLoss(type) {
        this.updateConnectionStatus('disconnected');
        this.showAlert('warning', `Lost connection to ${type} service. Attempting to reconnect...`);
        
        // Attempt to reconnect after 5 seconds
        setTimeout(() => this.initializeWebSockets(), 5000);
    }
    
    showAlert(type, message) {
        const alertsContainer = document.getElementById('statusMessages');
        if (!alertsContainer) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertsContainer.appendChild(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(() => alert.remove(), 5000);
    }
    
    formatTagValue(value, type) {
        switch (type) {
            case 'float':
                return Number(value).toFixed(2);
            case 'boolean':
                return value ? 'True' : 'False';
            default:
                return value;
        }
    }
    
    formatStateValue(value) {
        if (typeof value === 'boolean') {
            return value ? 'Active' : 'Inactive';
        } else if (typeof value === 'number') {
            return value.toFixed(2);
        }
        return value;
    }
    
    formatBytes(bytes) {
        const units = ['B', 'KB', 'MB', 'GB'];
        let value = bytes;
        let unit = 0;
        
        while (value > 1024 && unit < units.length - 1) {
            value /= 1024;
            unit++;
        }
        
        return `${value.toFixed(2)} ${units[unit]}`;
    }
    
    formatServiceStatus(services) {
        return Object.entries(services)
            .map(([name, status]) => `${name}: ${status}`)
            .join('<br>');
    }
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.mcsControl = new MCSControlUI();
}); 