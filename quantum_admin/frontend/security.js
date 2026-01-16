// Mock data
let users = [];
let roles = [];
let apiKeys = [];
let sessions = [];
let auditLog = [];

// Load initial data
window.addEventListener('DOMContentLoaded', function() {
    loadSecurityData();
});

// =====================
// DATA LOADING
// =====================

function loadSecurityData() {
    loadUsers();
    loadRoles();
    loadApiKeys();
    loadSessions();
    loadAuditLog();
    updateStats();
}

function loadUsers() {
    // Mock users
    users = [
        { id: 1, username: 'admin', email: 'admin@quantum.dev', role: 'Administrator', status: 'active', lastLogin: '2 hours ago' },
        { id: 2, username: 'developer', email: 'dev@quantum.dev', role: 'Developer', status: 'active', lastLogin: '5 hours ago' },
        { id: 3, username: 'viewer', email: 'viewer@quantum.dev', role: 'Viewer', status: 'active', lastLogin: '1 day ago' },
        { id: 4, username: 'john.doe', email: 'john@example.com', role: 'Developer', status: 'inactive', lastLogin: '7 days ago' }
    ];

    const tbody = document.querySelector('#users-table tbody');
    tbody.innerHTML = '';

    users.forEach(user => {
        const statusClass = user.status === 'active' ? 'success' : 'default';

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${user.username}</strong></td>
            <td>${user.email}</td>
            <td><span class="badge info">${user.role}</span></td>
            <td><span class="badge ${statusClass}">${user.status.toUpperCase()}</span></td>
            <td>${user.lastLogin}</td>
            <td>
                <div class="btn-group">
                    <button class="btn btn-sm" onclick="editUser(${user.id})">✏️ Edit</button>
                    <button class="btn btn-sm" onclick="resetPassword(${user.id})">🔑 Reset Password</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteUser(${user.id}, '${user.username}')">🗑️ Delete</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function loadRoles() {
    // Mock roles
    roles = [
        {
            name: 'Administrator',
            permissions: ['all'],
            users: 1,
            description: 'Full system access'
        },
        {
            name: 'Developer',
            permissions: ['read', 'write', 'deploy'],
            users: 2,
            description: 'Development and deployment access'
        },
        {
            name: 'Viewer',
            permissions: ['read'],
            users: 1,
            description: 'Read-only access'
        }
    ];

    const container = document.getElementById('roles-container');
    container.innerHTML = '';

    roles.forEach(role => {
        const card = document.createElement('div');
        card.style.cssText = 'background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;';
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                <div>
                    <h3 style="margin: 0; color: #2c3e50;">${role.name}</h3>
                    <p style="margin: 5px 0 0 0; color: #7f8c8d; font-size: 14px;">${role.description}</p>
                </div>
                <span class="badge default">${role.users} users</span>
            </div>

            <div style="margin-bottom: 15px;">
                <strong style="font-size: 13px; color: #2c3e50;">Permissions:</strong><br>
                ${role.permissions.map(p => `<span class="badge info" style="margin-top: 5px; margin-right: 5px;">${p}</span>`).join('')}
            </div>

            <div class="btn-group">
                <button class="btn btn-sm" onclick="editRole('${role.name}')">✏️ Edit</button>
                ${role.name !== 'Administrator' ?
                    `<button class="btn btn-sm btn-danger" onclick="deleteRole('${role.name}')">🗑️ Delete</button>` :
                    ''
                }
            </div>
        `;
        container.appendChild(card);
    });
}

function loadApiKeys() {
    // Mock API keys
    apiKeys = [
        { id: 1, name: 'Production API', key: 'qk_prod_***************', created: '2 weeks ago', lastUsed: '5 minutes ago', status: 'active' },
        { id: 2, name: 'Development API', key: 'qk_dev_***************', created: '1 month ago', lastUsed: '2 hours ago', status: 'active' },
        { id: 3, name: 'Test API', key: 'qk_test_***************', created: '3 months ago', lastUsed: 'Never', status: 'inactive' }
    ];

    const tbody = document.querySelector('#api-keys-table tbody');
    tbody.innerHTML = '';

    if (apiKeys.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No API keys yet. Generate one to get started.</td></tr>';
        return;
    }

    apiKeys.forEach(key => {
        const statusClass = key.status === 'active' ? 'success' : 'default';

        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${key.name}</strong></td>
            <td><code>${key.key}</code></td>
            <td>${key.created}</td>
            <td>${key.lastUsed}</td>
            <td><span class="badge ${statusClass}">${key.status.toUpperCase()}</span></td>
            <td>
                <div class="btn-group">
                    <button class="btn btn-sm" onclick="copyApiKey(${key.id})">📋 Copy</button>
                    <button class="btn btn-sm btn-danger" onclick="revokeApiKey(${key.id}, '${key.name}')">🔒 Revoke</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function loadSessions() {
    // Mock sessions
    sessions = [
        { id: 1, user: 'admin', ip: '192.168.1.100', location: 'São Paulo, Brazil', started: '2 hours ago', lastActivity: '5 minutes ago' },
        { id: 2, user: 'developer', ip: '192.168.1.101', location: 'Rio de Janeiro, Brazil', started: '5 hours ago', lastActivity: '30 minutes ago' }
    ];

    const tbody = document.querySelector('#sessions-table tbody');
    tbody.innerHTML = '';

    if (sessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No active sessions</td></tr>';
        return;
    }

    sessions.forEach(session => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${session.user}</strong></td>
            <td>${session.ip}</td>
            <td>${session.location}</td>
            <td>${session.started}</td>
            <td>${session.lastActivity}</td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="terminateSession(${session.id}, '${session.user}')">🚫 Terminate</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function loadAuditLog() {
    const filter = document.getElementById('audit-filter')?.value || 'all';

    // Mock audit log
    const allAuditLog = [
        { timestamp: '2024-01-15 14:30:22', event: 'User Login', category: 'auth', user: 'admin', ip: '192.168.1.100', details: 'Successful login' },
        { timestamp: '2024-01-15 14:25:15', event: 'Datasource Created', category: 'datasource', user: 'developer', ip: '192.168.1.101', details: 'Created postgres_db datasource' },
        { timestamp: '2024-01-15 14:20:00', event: 'Settings Changed', category: 'settings', user: 'admin', ip: '192.168.1.100', details: 'Updated SMTP configuration' },
        { timestamp: '2024-01-15 14:15:45', event: 'User Created', category: 'user', user: 'admin', ip: '192.168.1.100', details: 'Created user: john.doe' },
        { timestamp: '2024-01-15 14:10:30', event: 'Failed Login', category: 'auth', user: 'unknown', ip: '203.0.113.42', details: 'Invalid credentials' },
        { timestamp: '2024-01-15 14:05:12', event: 'Container Started', category: 'datasource', user: 'developer', ip: '192.168.1.101', details: 'Started container: postgres-16-alpine' }
    ];

    auditLog = filter === 'all' ?
        allAuditLog :
        allAuditLog.filter(log => log.category === filter);

    const tbody = document.getElementById('audit-tbody');
    tbody.innerHTML = '';

    auditLog.forEach(log => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${log.timestamp}</td>
            <td><strong>${log.event}</strong></td>
            <td>${log.user}</td>
            <td>${log.ip}</td>
            <td>${log.details}</td>
        `;
        tbody.appendChild(row);
    });
}

function updateStats() {
    document.getElementById('total-users').textContent = users.length;
    document.getElementById('active-sessions').textContent = sessions.length;
    document.getElementById('failed-logins').textContent = auditLog.filter(l => l.event === 'Failed Login').length;
    document.getElementById('api-keys').textContent = apiKeys.filter(k => k.status === 'active').length;

    // Check for security alerts
    checkSecurityAlerts();
}

function checkSecurityAlerts() {
    const alertsContainer = document.getElementById('security-alerts');
    const failedLogins = auditLog.filter(l => l.event === 'Failed Login');
    const alerts = [];

    // Multiple failed logins from same IP
    const ipCounts = {};
    failedLogins.forEach(log => {
        ipCounts[log.ip] = (ipCounts[log.ip] || 0) + 1;
    });

    Object.keys(ipCounts).forEach(ip => {
        if (ipCounts[ip] >= 3) {
            alerts.push({
                type: 'warning',
                message: `Multiple failed login attempts from IP ${ip} (${ipCounts[ip]} attempts)`
            });
        }
    });

    // Inactive API keys
    const inactiveKeys = apiKeys.filter(k => k.lastUsed === 'Never');
    if (inactiveKeys.length > 0) {
        alerts.push({
            type: 'info',
            message: `${inactiveKeys.length} API key(s) have never been used and can be revoked`
        });
    }

    // Render alerts
    if (alerts.length === 0) {
        alertsContainer.innerHTML = '<p style="text-align: center; color: #7f8c8d; padding: 20px;">✅ No security alerts</p>';
    } else {
        alertsContainer.innerHTML = alerts.map(alert => `
            <div style="padding: 15px; margin-bottom: 10px; background: ${alert.type === 'warning' ? '#fff3cd' : '#d1ecf1'}; border-left: 4px solid ${alert.type === 'warning' ? '#ffc107' : '#17a2b8'}; border-radius: 4px;">
                ${alert.type === 'warning' ? '⚠️' : 'ℹ️'} ${alert.message}
            </div>
        `).join('');
    }
}

// =====================
// USER ACTIONS
// =====================

function createUser() {
    const username = prompt('Enter username:');
    if (!username) return;

    const email = prompt('Enter email:');
    if (!email) return;

    showSuccess(`User "${username}" created successfully`);
    setTimeout(loadUsers, 500);
}

function editUser(id) {
    const user = users.find(u => u.id === id);
    alert(`Edit user: ${user.username}\n\n(Implement edit form)`);
}

function resetPassword(id) {
    const user = users.find(u => u.id === id);
    if (confirm(`Reset password for ${user.username}?`)) {
        showSuccess(`Password reset email sent to ${user.email}`);
    }
}

function deleteUser(id, username) {
    if (!confirm(`Delete user "${username}"?\n\nThis action cannot be undone.`)) return;

    showSuccess(`User "${username}" deleted`);
    setTimeout(loadUsers, 500);
}

// =====================
// ROLE ACTIONS
// =====================

function createRole() {
    const name = prompt('Enter role name:');
    if (!name) return;

    showSuccess(`Role "${name}" created`);
    setTimeout(loadRoles, 500);
}

function editRole(name) {
    alert(`Edit role: ${name}\n\n(Implement role editor)`);
}

function deleteRole(name) {
    if (!confirm(`Delete role "${name}"?\n\nUsers with this role will be assigned to Viewer.`)) return;

    showSuccess(`Role "${name}" deleted`);
    setTimeout(loadRoles, 500);
}

// =====================
// API KEY ACTIONS
// =====================

function generateApiKey() {
    const name = prompt('Enter API key name:');
    if (!name) return;

    const key = 'qk_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);

    alert(`API Key generated!\n\n${key}\n\n⚠️ Save this key now - you won't see it again!`);

    showSuccess('API key generated');
    setTimeout(loadApiKeys, 500);
}

function copyApiKey(id) {
    showSuccess('API key copied to clipboard');
}

function revokeApiKey(id, name) {
    if (!confirm(`Revoke API key "${name}"?\n\nApplications using this key will lose access.`)) return;

    showSuccess(`API key "${name}" revoked`);
    setTimeout(loadApiKeys, 500);
}

// =====================
// SESSION ACTIONS
// =====================

function terminateSession(id, user) {
    if (!confirm(`Terminate session for ${user}?\n\nThe user will be logged out immediately.`)) return;

    showSuccess(`Session terminated for ${user}`);
    setTimeout(loadSessions, 500);
}

// =====================
// EXPORT
// =====================

function exportAuditLog() {
    const csv = 'Timestamp,Event,User,IP Address,Details\n' +
        auditLog.map(log => `"${log.timestamp}","${log.event}","${log.user}","${log.ip}","${log.details}"`).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-log-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();

    URL.revokeObjectURL(url);
    showSuccess('Audit log exported');
}

// =====================
// UTILITIES
// =====================

function showSuccess(message) {
    alert('✅ ' + message);
}
