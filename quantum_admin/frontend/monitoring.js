// API Base URL
const API_URL = 'http://localhost:8000';

// Refresh interval (5 seconds)
const REFRESH_INTERVAL = 5000;

// Load initial data
window.addEventListener('DOMContentLoaded', function() {
    loadSystemMetrics();
    loadSystemInfo();
    initCharts();

    // Auto-refresh
    setInterval(loadSystemMetrics, REFRESH_INTERVAL);
});

// =====================
// METRICS LOADING
// =====================

async function loadSystemMetrics() {
    try {
        // Simulate metrics (replace with real API when available)
        const metrics = {
            cpu_usage: Math.random() * 30 + 10, // 10-40%
            memory_used: Math.floor(Math.random() * 500 + 200), // 200-700 MB
            disk_used: Math.floor(Math.random() * 50 + 20), // 20-70 GB
            active_connections: Math.floor(Math.random() * 20 + 5), // 5-25
        };

        // Update stats cards
        document.getElementById('cpu-usage').textContent = metrics.cpu_usage.toFixed(1) + '%';
        document.getElementById('memory-usage').textContent = metrics.memory_used + ' MB';
        document.getElementById('disk-usage').textContent = metrics.disk_used + ' GB';
        document.getElementById('active-connections').textContent = metrics.active_connections;

        // Update process stats
        document.getElementById('quantum-cpu').textContent = (Math.random() * 2 + 0.5).toFixed(1) + '%';
        document.getElementById('quantum-mem').textContent = Math.floor(Math.random() * 20 + 40) + ' MB';
        document.getElementById('admin-cpu').textContent = (Math.random() * 1 + 0.3).toFixed(1) + '%';
        document.getElementById('admin-mem').textContent = Math.floor(Math.random() * 10 + 30) + ' MB';

        // Check for alerts
        checkAlerts(metrics);
    } catch (error) {
        console.error('Error loading metrics:', error);
    }
}

async function loadSystemInfo() {
    try {
        // Try to get real system info from backend
        const response = await fetch(`${API_URL}/health`);

        if (response.ok) {
            const data = await response.json();

            if (data.python_version) {
                document.getElementById('python-version').textContent = data.python_version;
            }
            if (data.platform) {
                document.getElementById('os-info').textContent = data.platform;
            }
        }

        // Update uptime
        updateUptime();
        setInterval(updateUptime, 60000); // Update every minute
    } catch (error) {
        console.error('Error loading system info:', error);
    }
}

function updateUptime() {
    // Simulate uptime (replace with real data)
    const uptimeMinutes = Math.floor(Math.random() * 500 + 100);
    const hours = Math.floor(uptimeMinutes / 60);
    const minutes = uptimeMinutes % 60;
    document.getElementById('uptime').textContent = `${hours}h ${minutes}m`;
}

// =====================
// ALERTS
// =====================

function checkAlerts(metrics) {
    const alertsContainer = document.getElementById('alerts-container');
    const alerts = [];

    // CPU Alert
    if (metrics.cpu_usage > 80) {
        alerts.push({
            type: 'error',
            icon: '🔥',
            message: `High CPU usage detected: ${metrics.cpu_usage.toFixed(1)}%`
        });
    } else if (metrics.cpu_usage > 60) {
        alerts.push({
            type: 'warning',
            icon: '⚠️',
            message: `Elevated CPU usage: ${metrics.cpu_usage.toFixed(1)}%`
        });
    }

    // Memory Alert
    if (metrics.memory_used > 600) {
        alerts.push({
            type: 'warning',
            icon: '💭',
            message: `Memory usage is high: ${metrics.memory_used} MB`
        });
    }

    // Disk Alert
    if (metrics.disk_used > 60) {
        alerts.push({
            type: 'warning',
            icon: '💾',
            message: `Disk usage is high: ${metrics.disk_used} GB`
        });
    }

    // Render alerts
    if (alerts.length === 0) {
        alertsContainer.innerHTML = '<p style="text-align: center; color: #7f8c8d; padding: 20px;">✅ No alerts - All systems operating normally</p>';
    } else {
        alertsContainer.innerHTML = alerts.map(alert => `
            <div class="alert alert-${alert.type}" style="padding: 15px; margin-bottom: 10px; border-radius: 8px; background: ${alert.type === 'error' ? '#fee' : '#fff3cd'}; border-left: 4px solid ${alert.type === 'error' ? '#dc3545' : '#ffc107'};">
                ${alert.icon} ${alert.message}
            </div>
        `).join('');
    }
}

// =====================
// CHARTS (Placeholder)
// =====================

function initCharts() {
    // Placeholder for chart initialization
    // In production, use Chart.js or similar library
    const chartElements = document.querySelectorAll('.chart canvas');

    chartElements.forEach(canvas => {
        const ctx = canvas.getContext('2d');

        // Draw simple placeholder chart
        ctx.fillStyle = '#f8f9fa';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw sample line
        ctx.strokeStyle = '#667eea';
        ctx.lineWidth = 2;
        ctx.beginPath();

        for (let i = 0; i < 50; i++) {
            const x = (canvas.width / 50) * i;
            const y = canvas.height / 2 + Math.sin(i / 5) * 50 + (Math.random() - 0.5) * 20;

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        }

        ctx.stroke();

        // Add text
        ctx.fillStyle = '#7f8c8d';
        ctx.font = '14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Real-time data visualization (Chart.js integration planned)', canvas.width / 2, canvas.height / 2);
    });
}

function updateCharts() {
    // Update charts based on time range
    const timeRange = document.getElementById('timeRange').value;
    console.log('Update charts for time range:', timeRange);

    // Re-initialize with new data
    initCharts();
}

// =====================
// ACTIONS
// =====================

function refreshMetrics() {
    loadSystemMetrics();
    loadSystemInfo();
    showSuccess('Metrics refreshed successfully');
}

function exportMetrics() {
    const data = {
        timestamp: new Date().toISOString(),
        cpu: document.getElementById('cpu-usage').textContent,
        memory: document.getElementById('memory-usage').textContent,
        disk: document.getElementById('disk-usage').textContent,
        connections: document.getElementById('active-connections').textContent,
        uptime: document.getElementById('uptime').textContent
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `quantum-metrics-${new Date().toISOString().split('T')[0]}.json`;
    a.click();

    URL.revokeObjectURL(url);
    showSuccess('Metrics exported successfully');
}

async function restartProcess(processName) {
    if (!confirm(`Are you sure you want to restart ${processName}?\n\nThis may cause temporary service interruption.`)) {
        return;
    }

    try {
        // Call restart endpoint (implement on backend)
        const response = await fetch(`${API_URL}/system/restart/${processName}`, {
            method: 'POST'
        });

        if (response.ok) {
            showSuccess(`${processName} restart initiated`);
        } else {
            showError('Restart failed. Check logs for details.');
        }
    } catch (error) {
        console.error('Error restarting process:', error);
        showWarning('Restart endpoint not yet implemented on backend');
    }
}

// =====================
// NOTIFICATIONS
// =====================

function showSuccess(message) {
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ ' + message);
}

function showWarning(message) {
    alert('⚠️ ' + message);
}
