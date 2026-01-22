// Mock log entries
let allLogs = [];
let filteredLogs = [];
let currentFontSize = 13;

// Load initial data
window.addEventListener('DOMContentLoaded', function() {
    generateMockLogs();
    loadLogs();

    // Auto-refresh every 5 seconds
    setInterval(() => {
        if (document.getElementById('log-source').value !== 'all' ||
            document.getElementById('log-level').value !== 'all') {
            // Don't auto-refresh when filters are active
            return;
        }
        loadLogs(true);
    }, 5000);
});

// =====================
// LOG GENERATION
// =====================

function generateMockLogs() {
    const sources = ['quantum', 'admin', 'database', 'system'];
    const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
    const messages = [
        'Server started successfully',
        'Database connection established',
        'Request processed: GET /api/projects',
        'User authentication successful',
        'Cache updated',
        'File uploaded: document.pdf',
        'Email sent to user@example.com',
        'Connection timeout on datasource postgres_db',
        'Invalid request parameter: missing required field "name"',
        'Memory usage: 85% - approaching limit',
        'Failed to connect to database: connection refused',
        'Unhandled exception in request handler',
        'Container started: postgres-16-alpine',
        'Hot reload triggered: home.q modified',
        'API rate limit exceeded for IP 192.168.1.100'
    ];

    allLogs = [];

    for (let i = 0; i < 200; i++) {
        const timestamp = new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000);
        const source = sources[Math.floor(Math.random() * sources.length)];
        const level = levels[Math.floor(Math.random() * levels.length)];
        const message = messages[Math.floor(Math.random() * messages.length)];

        allLogs.push({
            timestamp,
            source,
            level,
            message: `[${source.toUpperCase()}] ${message}`
        });
    }

    // Sort by timestamp (newest first)
    allLogs.sort((a, b) => b.timestamp - a.timestamp);
}

// =====================
// LOG LOADING
// =====================

function loadLogs(silent = false) {
    const source = document.getElementById('log-source').value;
    const level = document.getElementById('log-level').value;
    const timeRange = document.getElementById('time-range').value;
    const showTimestamps = document.getElementById('show-timestamps').checked;

    // Filter logs
    filteredLogs = allLogs.filter(log => {
        // Source filter
        if (source !== 'all' && log.source !== source) {
            return false;
        }

        // Level filter
        if (level !== 'all' && log.level !== level) {
            return false;
        }

        // Time range filter
        const now = Date.now();
        const logAge = now - log.timestamp.getTime();

        const ranges = {
            '1h': 60 * 60 * 1000,
            '6h': 6 * 60 * 60 * 1000,
            '24h': 24 * 60 * 60 * 1000,
            '7d': 7 * 24 * 60 * 60 * 1000,
            '30d': 30 * 24 * 60 * 60 * 1000
        };

        if (logAge > ranges[timeRange]) {
            return false;
        }

        return true;
    });

    // Update stats
    updateStats();

    // Render logs
    const viewer = document.getElementById('log-viewer');
    const logLines = filteredLogs.map(log => formatLogEntry(log, showTimestamps));

    viewer.textContent = logLines.join('\n');

    // Auto-scroll
    if (document.getElementById('auto-scroll').checked) {
        viewer.scrollTop = viewer.scrollHeight;
    }

    if (!silent) {
        console.log(`Loaded ${filteredLogs.length} logs`);
    }

    // Update recent errors
    updateRecentErrors();
}

function formatLogEntry(log, showTimestamps) {
    const timestamp = showTimestamps ? `[${formatTimestamp(log.timestamp)}] ` : '';
    const levelColor = getLevelColor(log.level);
    const level = `[${log.level}]`.padEnd(11);

    return `${timestamp}${level} ${log.message}`;
}

function formatTimestamp(date) {
    return date.toISOString().replace('T', ' ').substring(0, 19);
}

function getLevelColor(level) {
    const colors = {
        'DEBUG': '#6c757d',
        'INFO': '#17a2b8',
        'WARNING': '#ffc107',
        'ERROR': '#dc3545',
        'CRITICAL': '#6f42c1'
    };
    return colors[level] || '#6c757d';
}

function updateStats() {
    document.getElementById('total-logs').textContent = filteredLogs.length;

    const info = filteredLogs.filter(l => l.level === 'INFO').length;
    const warnings = filteredLogs.filter(l => l.level === 'WARNING').length;
    const errors = filteredLogs.filter(l => l.level === 'ERROR' || l.level === 'CRITICAL').length;

    document.getElementById('info-count').textContent = info;
    document.getElementById('warning-count').textContent = warnings;
    document.getElementById('error-count').textContent = errors;
}

function updateRecentErrors() {
    const recentErrors = filteredLogs.filter(l => l.level === 'ERROR' || l.level === 'CRITICAL').slice(0, 5);

    const container = document.getElementById('recent-errors');

    if (recentErrors.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #7f8c8d; padding: 20px;">✅ No errors in the selected time range</p>';
        return;
    }

    container.innerHTML = recentErrors.map(error => `
        <div style="padding: 15px; margin-bottom: 10px; background: #fee; border-left: 4px solid #dc3545; border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <strong style="color: #dc3545;">${error.level}</strong>
                <span style="color: #7f8c8d; font-size: 13px;">${formatTimestamp(error.timestamp)}</span>
            </div>
            <p style="margin: 0; color: #2c3e50;">${error.message}</p>
        </div>
    `).join('');
}

// =====================
// FILTERING
// =====================

function filterLogs() {
    const searchTerm = document.getElementById('search-logs').value.toLowerCase();

    if (!searchTerm) {
        loadLogs();
        return;
    }

    filteredLogs = filteredLogs.filter(log =>
        log.message.toLowerCase().includes(searchTerm) ||
        log.level.toLowerCase().includes(searchTerm) ||
        log.source.toLowerCase().includes(searchTerm)
    );

    const viewer = document.getElementById('log-viewer');
    const showTimestamps = document.getElementById('show-timestamps').checked;
    const logLines = filteredLogs.map(log => formatLogEntry(log, showTimestamps));

    viewer.textContent = logLines.join('\n');
    updateStats();
}

// =====================
// ACTIONS
// =====================

function clearLogs() {
    if (!confirm('Clear all logs?\n\nThis action cannot be undone.')) {
        return;
    }

    allLogs = [];
    filteredLogs = [];

    loadLogs();
    showSuccess('Logs cleared');
}

function downloadLogs() {
    const showTimestamps = document.getElementById('show-timestamps').checked;
    const logText = filteredLogs.map(log => formatLogEntry(log, showTimestamps)).join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `quantum-logs-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();

    URL.revokeObjectURL(url);
    showSuccess('Logs downloaded');
}

function toggleWordWrap() {
    const viewer = document.getElementById('log-viewer');
    const wordWrap = document.getElementById('word-wrap').checked;

    viewer.style.whiteSpace = wordWrap ? 'pre-wrap' : 'pre';
}

function fontSize(action) {
    const viewer = document.getElementById('log-viewer');

    if (action === 'increase' && currentFontSize < 20) {
        currentFontSize += 1;
    } else if (action === 'decrease' && currentFontSize > 10) {
        currentFontSize -= 1;
    }

    viewer.style.fontSize = currentFontSize + 'px';
}

// =====================
// UTILITIES
// =====================

function showSuccess(message) {
    alert('✅ ' + message);
}
