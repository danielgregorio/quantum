// API Base URL
const API_URL = 'http://localhost:8000';

// Global state
let projects = [];
let datasources = [];
let currentLogsId = null;

// Default ports by database type
const DEFAULT_PORTS = {
    'postgres': 5432,
    'mysql': 3306,
    'mongodb': 27017,
    'redis': 6379,
    'mariadb': 3306
};

// Load initial data
window.addEventListener('DOMContentLoaded', function() {
    loadProjects();
    loadDatasources();
});

// =====================
// PROJECT FUNCTIONS
// =====================

async function loadProjects() {
    try {
        const response = await fetch(`${API_URL}/projects`);
        projects = await response.json();

        // Populate project dropdown
        const select = document.getElementById('project_id');
        select.innerHTML = '<option value="">Select a project...</option>';

        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.id;
            option.textContent = `${project.name} - ${project.description || 'No description'}`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading projects:', error);
        showError('Failed to load projects. Make sure Admin API is running.');
    }
}

// =====================
// DATASOURCE FUNCTIONS
// =====================

async function loadDatasources() {
    const tbody = document.querySelector('#datasources-table tbody');

    try {
        // Get all projects
        const projectsResponse = await fetch(`${API_URL}/projects`);
        const projects = await projectsResponse.json();

        if (projects.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No projects yet. Create a project first!</td></tr>';
            return;
        }

        datasources = [];

        // Get datasources for each project
        for (const project of projects) {
            const dsResponse = await fetch(`${API_URL}/projects/${project.id}/datasources`);
            const projectDatasources = await dsResponse.json();

            // Add project info to each datasource
            projectDatasources.forEach(ds => {
                ds.project = project;
                datasources.push(ds);
            });
        }

        if (datasources.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No datasources yet. Create one to get started!</td></tr>';
            return;
        }

        // Render table
        tbody.innerHTML = '';

        for (const ds of datasources) {
            // Get real-time status if it's a Docker container
            let status = 'N/A';
            let statusClass = 'default';

            if (ds.connection_type === 'docker') {
                try {
                    const statusResponse = await fetch(`${API_URL}/datasources/${ds.id}/status`);
                    const statusData = await statusResponse.json();
                    status = statusData.status || 'unknown';

                    if (status === 'running') statusClass = 'success';
                    else if (status === 'exited') statusClass = 'error';
                    else if (status === 'created') statusClass = 'warning';
                } catch (e) {
                    status = 'error';
                    statusClass = 'error';
                }
            } else {
                status = 'external';
                statusClass = 'info';
            }

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <strong>${ds.name}</strong>
                    <br><small style="color: #666;">Project: ${ds.project.name}</small>
                </td>
                <td><span class="badge info">${ds.type.toUpperCase()}</span></td>
                <td><span class="badge ${ds.connection_type === 'docker' ? 'default' : 'warning'}">${ds.connection_type.toUpperCase()}</span></td>
                <td><span class="badge ${statusClass}">${status.toUpperCase()}</span></td>
                <td>${ds.host || 'localhost'}:${ds.port}</td>
                <td>
                    <div class="btn-group">
                        ${ds.connection_type === 'docker' ? `
                            ${status === 'running' ?
                                `<button class="btn btn-sm" onclick="stopDatasource(${ds.id})" title="Stop">⏸️</button>` :
                                `<button class="btn btn-sm btn-success" onclick="startDatasource(${ds.id})" title="Start">▶️</button>`
                            }
                            <button class="btn btn-sm" onclick="restartDatasource(${ds.id})" title="Restart">🔄</button>
                            <button class="btn btn-sm" onclick="viewLogs(${ds.id})" title="View Logs">📋</button>
                        ` : ''}
                        <button class="btn btn-sm" onclick="testConnection(${ds.id})" title="Test Connection">🔌</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteDatasource(${ds.id}, '${ds.name}')" title="Delete">🗑️</button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        }
    } catch (error) {
        console.error('Error loading datasources:', error);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">⚠️ Error loading datasources. Make sure Admin API is running.</td></tr>';
    }
}

async function createDatasource(event) {
    event.preventDefault();

    const projectId = document.getElementById('project_id').value;
    const connectionType = document.getElementById('connection_type').value;

    // Build datasource object
    const datasource = {
        name: document.getElementById('ds_name').value,
        type: document.getElementById('ds_type').value,
        connection_type: connectionType,
        port: parseInt(document.getElementById('port').value),
        database_name: document.getElementById('database_name').value,
        username: document.getElementById('username').value,
        password: document.getElementById('password').value,
        auto_start: document.getElementById('auto_start').checked
    };

    // Docker-specific fields
    if (connectionType === 'docker') {
        const image = document.getElementById('image').value;
        if (image) datasource.image = image;
    } else {
        // External connection
        datasource.host = document.getElementById('host').value;
    }

    // Advanced settings
    const envText = document.getElementById('environment').value.trim();
    if (envText) {
        try {
            datasource.environment = JSON.parse(envText);
        } catch (e) {
            showError('Invalid JSON in environment variables');
            return;
        }
    }

    const volumesText = document.getElementById('volumes').value.trim();
    if (volumesText) {
        try {
            datasource.volumes = JSON.parse(volumesText);
        } catch (e) {
            showError('Invalid JSON in volumes');
            return;
        }
    }

    try {
        const response = await fetch(`${API_URL}/projects/${projectId}/datasources`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(datasource)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create datasource');
        }

        const result = await response.json();
        console.log('Datasource created:', result);

        showSuccess(`Datasource "${datasource.name}" created successfully!`);
        closeCreateModal();
        loadDatasources();
    } catch (error) {
        console.error('Error creating datasource:', error);
        showError('Failed to create datasource: ' + error.message);
    }
}

async function startDatasource(id) {
    try {
        const response = await fetch(`${API_URL}/datasources/${id}/start`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to start datasource');
        }

        showSuccess('Datasource started successfully!');

        // Reload after a delay to allow container to start
        setTimeout(() => loadDatasources(), 2000);
    } catch (error) {
        console.error('Error starting datasource:', error);
        showError('Failed to start datasource: ' + error.message);
    }
}

async function stopDatasource(id) {
    try {
        const response = await fetch(`${API_URL}/datasources/${id}/stop`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to stop datasource');
        }

        showSuccess('Datasource stopped successfully!');

        // Reload after a delay
        setTimeout(() => loadDatasources(), 1000);
    } catch (error) {
        console.error('Error stopping datasource:', error);
        showError('Failed to stop datasource: ' + error.message);
    }
}

async function restartDatasource(id) {
    try {
        const response = await fetch(`${API_URL}/datasources/${id}/restart`, {
            method: 'POST'
        });

        if (!response.ok) {
            throw new Error('Failed to restart datasource');
        }

        showSuccess('Datasource restarting...');

        // Reload after a delay
        setTimeout(() => loadDatasources(), 3000);
    } catch (error) {
        console.error('Error restarting datasource:', error);
        showError('Failed to restart datasource: ' + error.message);
    }
}

async function deleteDatasource(id, name) {
    if (!confirm(`Are you sure you want to delete datasource "${name}"?\n\nThis will stop and remove the container if it's running.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/datasources/${id}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete datasource');
        }

        showSuccess(`Datasource "${name}" deleted successfully!`);
        loadDatasources();
    } catch (error) {
        console.error('Error deleting datasource:', error);
        showError('Failed to delete datasource: ' + error.message);
    }
}

async function testConnection(id) {
    try {
        const response = await fetch(`${API_URL}/datasources/${id}/test`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            showSuccess('✅ Connection successful!');
        } else {
            showError('❌ Connection failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error testing connection:', error);
        showError('Failed to test connection: ' + error.message);
    }
}

// =====================
// LOGS FUNCTIONS
// =====================

async function viewLogs(id) {
    currentLogsId = id;
    document.getElementById('logsModal').style.display = 'block';
    refreshLogs();
}

async function refreshLogs() {
    if (!currentLogsId) return;

    const logsContent = document.getElementById('logs-content');
    const lines = document.getElementById('log-lines').value;

    logsContent.textContent = 'Loading logs...';

    try {
        const response = await fetch(`${API_URL}/datasources/${currentLogsId}/logs?lines=${lines}`);

        if (!response.ok) {
            throw new Error('Failed to fetch logs');
        }

        const data = await response.json();
        logsContent.textContent = data.logs || 'No logs available';
    } catch (error) {
        console.error('Error fetching logs:', error);
        logsContent.textContent = `Error fetching logs: ${error.message}`;
    }
}

function closeLogsModal() {
    document.getElementById('logsModal').style.display = 'none';
    currentLogsId = null;
}

// =====================
// MODAL FUNCTIONS
// =====================

function showCreateModal() {
    document.getElementById('createModal').style.display = 'block';

    // Reset form
    document.getElementById('createForm').reset();

    // Set defaults
    document.getElementById('connection_type').value = 'docker';
    document.getElementById('auto_start').checked = true;
    toggleConnectionFields();
}

function closeCreateModal() {
    document.getElementById('createModal').style.display = 'none';
}

function toggleConnectionFields() {
    const connectionType = document.getElementById('connection_type').value;
    const dockerSettings = document.getElementById('docker-settings');
    const externalSettings = document.getElementById('external-settings');

    if (connectionType === 'docker') {
        dockerSettings.style.display = 'block';
        externalSettings.style.display = 'none';
        document.getElementById('host').removeAttribute('required');
    } else {
        dockerSettings.style.display = 'none';
        externalSettings.style.display = 'block';
        document.getElementById('host').setAttribute('required', 'required');
    }
}

function updateDefaultPort() {
    const type = document.getElementById('ds_type').value;
    const portInput = document.getElementById('port');

    if (type && DEFAULT_PORTS[type]) {
        portInput.value = DEFAULT_PORTS[type];
    }
}

// Close modals when clicking outside
window.onclick = function(event) {
    const createModal = document.getElementById('createModal');
    const logsModal = document.getElementById('logsModal');

    if (event.target === createModal) {
        closeCreateModal();
    }
    if (event.target === logsModal) {
        closeLogsModal();
    }
};

// =====================
// NOTIFICATION FUNCTIONS
// =====================

function showSuccess(message) {
    // Simple alert for now - could be improved with toast notifications
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ ' + message);
}

// Auto-refresh datasources every 30 seconds
setInterval(() => {
    loadDatasources();
}, 30000);
