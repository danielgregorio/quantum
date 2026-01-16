/**
 * WebSocket Client for Real-time Notifications
 * Connects to backend WebSocket server for live updates
 */

class QuantumWebSocket {
    constructor(url = 'ws://localhost:8000/ws') {
        this.url = url;
        this.ws = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.reconnectAttempts = 0;
        this.handlers = new Map();
        this.isConnected = false;
    }

    // Connect to WebSocket
    connect() {
        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                console.log('🔌 WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000;

                // Show connection notification
                if (window.Quantum?.notify) {
                    Quantum.notify.success('🔌 Real-time updates connected');
                }

                // Trigger connected event
                this.trigger('connected');
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.trigger('error', error);
            };

            this.ws.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                this.isConnected = false;
                this.trigger('disconnected');

                // Attempt to reconnect
                this.scheduleReconnect();
            };

        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
            this.scheduleReconnect();
        }
    }

    // Handle incoming message
    handleMessage(data) {
        const { type, payload } = data;

        console.log('📨 WebSocket message:', type, payload);

        // Trigger type-specific handlers
        this.trigger(type, payload);

        // Handle common message types
        switch (type) {
            case 'notification':
                this.handleNotification(payload);
                break;

            case 'datasource.status':
                this.handleDatasourceStatus(payload);
                break;

            case 'container.updated':
                this.handleContainerUpdate(payload);
                break;

            case 'log.entry':
                this.handleLogEntry(payload);
                break;

            case 'metrics.update':
                this.handleMetricsUpdate(payload);
                break;

            default:
                this.trigger('message', data);
        }
    }

    // Handle notification
    handleNotification(payload) {
        const { level, message } = payload;

        if (window.Quantum?.notify) {
            switch (level) {
                case 'success':
                    Quantum.notify.success(message);
                    break;
                case 'error':
                    Quantum.notify.error(message);
                    break;
                case 'warning':
                    Quantum.notify.warning(message);
                    break;
                default:
                    Quantum.notify.info(message);
            }
        }
    }

    // Handle datasource status update
    handleDatasourceStatus(payload) {
        const { datasource_id, status } = payload;

        // Update datasource status in UI if on datasources page
        const statusElement = document.querySelector(`[data-datasource-id="${datasource_id}"] .status`);
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `badge ${status === 'running' ? 'success' : 'error'}`;
        }
    }

    // Handle container update
    handleContainerUpdate(payload) {
        const { container_id, action, status } = payload;

        if (window.Quantum?.notify) {
            Quantum.notify.info(`Container ${container_id}: ${action}`);
        }

        // Refresh containers page if active
        if (window.location.pathname.includes('containers.html')) {
            if (typeof loadContainers === 'function') {
                loadContainers();
            }
        }
    }

    // Handle log entry
    handleLogEntry(payload) {
        const { level, message, source } = payload;

        // Append to logs page if active
        if (window.location.pathname.includes('logs.html')) {
            // Implementation depends on logs page structure
            console.log(`[${level}] ${source}: ${message}`);
        }
    }

    // Handle metrics update
    handleMetricsUpdate(payload) {
        const { cpu, memory, disk, connections } = payload;

        // Update monitoring page if active
        if (window.location.pathname.includes('monitoring.html')) {
            if (document.getElementById('cpu-usage')) {
                document.getElementById('cpu-usage').textContent = `${cpu}%`;
            }
            if (document.getElementById('memory-usage')) {
                document.getElementById('memory-usage').textContent = `${memory} MB`;
            }
            if (document.getElementById('disk-usage')) {
                document.getElementById('disk-usage').textContent = `${disk} GB`;
            }
            if (document.getElementById('active-connections')) {
                document.getElementById('active-connections').textContent = connections;
            }

            // Update charts if available
            if (window.ChartIntegration?.charts) {
                Object.values(window.ChartIntegration.charts).forEach(chart => {
                    if (chart) {
                        window.ChartIntegration.updateChartData(chart, Math.random() * 100);
                    }
                });
            }
        }
    }

    // Send message to server
    send(type, payload = {}) {
        if (!this.isConnected) {
            console.warn('WebSocket not connected');
            return false;
        }

        try {
            this.ws.send(JSON.stringify({ type, payload }));
            return true;
        } catch (error) {
            console.error('Error sending WebSocket message:', error);
            return false;
        }
    }

    // Subscribe to datasource updates
    subscribeDatasource(datasourceId) {
        this.send('subscribe', { type: 'datasource', id: datasourceId });
    }

    // Subscribe to container updates
    subscribeContainer(containerId) {
        this.send('subscribe', { type: 'container', id: containerId });
    }

    // Subscribe to logs
    subscribeLogs(source = 'all') {
        this.send('subscribe', { type: 'logs', source });
    }

    // Subscribe to metrics
    subscribeMetrics() {
        this.send('subscribe', { type: 'metrics' });
    }

    // Event handling
    on(event, handler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, []);
        }
        this.handlers.get(event).push(handler);
    }

    off(event, handler) {
        if (!this.handlers.has(event)) return;

        const handlers = this.handlers.get(event);
        const index = handlers.indexOf(handler);
        if (index > -1) {
            handlers.splice(index, 1);
        }
    }

    trigger(event, data) {
        if (!this.handlers.has(event)) return;

        this.handlers.get(event).forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                console.error(`Error in ${event} handler:`, error);
            }
        });
    }

    // Schedule reconnect
    scheduleReconnect() {
        this.reconnectAttempts++;

        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay
        );

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            console.log('Attempting to reconnect...');
            this.connect();
        }, delay);
    }

    // Disconnect
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
            this.isConnected = false;
        }
    }

    // Get connection status
    getStatus() {
        return {
            connected: this.isConnected,
            reconnectAttempts: this.reconnectAttempts,
            url: this.url
        };
    }
}

// Global instance
const quantumWS = new QuantumWebSocket();

// Auto-connect on load
document.addEventListener('DOMContentLoaded', function() {
    // Connect to WebSocket
    quantumWS.connect();

    // Subscribe based on current page
    const path = window.location.pathname;

    if (path.includes('monitoring.html')) {
        quantumWS.subscribeMetrics();
    } else if (path.includes('datasources.html') || path.includes('containers.html')) {
        quantumWS.subscribeDatasource('all');
        quantumWS.subscribeContainer('all');
    } else if (path.includes('logs.html')) {
        quantumWS.subscribeLogs();
    }

    console.log('🔌 WebSocket client initialized');
});

// Export
window.QuantumWebSocket = QuantumWebSocket;
window.quantumWS = quantumWS;
