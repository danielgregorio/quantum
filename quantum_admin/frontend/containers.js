// API Base URL
const API_URL = 'http://localhost:8000';

// Global state
let currentContainerId = null;
let containers = [];
let images = [];

// Load initial data
window.addEventListener('DOMContentLoaded', function() {
    loadContainers();
    loadImages();
    loadVolumes();
    loadNetworks();
});

// =====================
// CONTAINERS
// =====================

async function loadContainers() {
    const tbody = document.querySelector('#containers-table tbody');
    const showAll = document.getElementById('show-all').checked;

    try {
        // Get all datasources (which are Docker containers)
        const projectsResponse = await fetch(`${API_URL}/projects`);
        const projects = await projectsResponse.json();

        containers = [];

        // Get datasources for each project
        for (const project of projects) {
            const dsResponse = await fetch(`${API_URL}/projects/${project.id}/datasources`);
            const projectDatasources = await dsResponse.json();

            for (const ds of projectDatasources) {
                if (ds.connection_type === 'docker') {
                    // Get container status
                    try {
                        const statusResponse = await fetch(`${API_URL}/datasources/${ds.id}/status`);
                        const statusData = await statusResponse.json();

                        containers.push({
                            id: ds.id,
                            name: ds.name,
                            image: ds.image || `${ds.type}:latest`,
                            status: statusData.status || 'unknown',
                            port: ds.port,
                            created: ds.created_at,
                            datasource: ds
                        });
                    } catch (e) {
                        console.error(`Error getting status for ${ds.name}:`, e);
                    }
                }
            }
        }

        // Filter by show all
        let displayContainers = containers;
        if (!showAll) {
            displayContainers = containers.filter(c => c.status === 'running');
        }

        // Update stats
        document.getElementById('total-containers').textContent = containers.length;
        document.getElementById('running-containers').textContent = containers.filter(c => c.status === 'running').length;
        document.getElementById('stopped-containers').textContent = containers.filter(c => c.status !== 'running').length;

        // Render table
        if (displayContainers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center">No containers found</td></tr>';
            return;
        }

        tbody.innerHTML = '';

        displayContainers.forEach(container => {
            const statusClass = container.status === 'running' ? 'success' :
                               container.status === 'exited' ? 'error' : 'warning';

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <strong>${container.name}</strong>
                    <br><small style="color: #666;">ID: ${container.id}</small>
                </td>
                <td>${container.image}</td>
                <td><span class="badge ${statusClass}">${container.status.toUpperCase()}</span></td>
                <td>${container.port || '-'}</td>
                <td>${formatDate(container.created)}</td>
                <td>
                    <div class="btn-group">
                        ${container.status === 'running' ?
                            `<button class="btn btn-sm" onclick="stopContainer(${container.id})" title="Stop">⏸️</button>` :
                            `<button class="btn btn-sm btn-success" onclick="startContainer(${container.id})" title="Start">▶️</button>`
                        }
                        <button class="btn btn-sm" onclick="restartContainer(${container.id})" title="Restart">🔄</button>
                        <button class="btn btn-sm" onclick="viewContainerLogs(${container.id}, '${container.name}')" title="Logs">📋</button>
                        <button class="btn btn-sm btn-danger" onclick="deleteContainer(${container.id}, '${container.name}')" title="Delete">🗑️</button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading containers:', error);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">⚠️ Error loading containers</td></tr>';
    }
}

async function startContainer(id) {
    try {
        const response = await fetch(`${API_URL}/datasources/${id}/start`, { method: 'POST' });
        if (response.ok) {
            showSuccess('Container started successfully');
            setTimeout(loadContainers, 2000);
        }
    } catch (error) {
        showError('Failed to start container');
    }
}

async function stopContainer(id) {
    try {
        const response = await fetch(`${API_URL}/datasources/${id}/stop`, { method: 'POST' });
        if (response.ok) {
            showSuccess('Container stopped successfully');
            setTimeout(loadContainers, 1000);
        }
    } catch (error) {
        showError('Failed to stop container');
    }
}

async function restartContainer(id) {
    try {
        const response = await fetch(`${API_URL}/datasources/${id}/restart`, { method: 'POST' });
        if (response.ok) {
            showSuccess('Container restarting...');
            setTimeout(loadContainers, 3000);
        }
    } catch (error) {
        showError('Failed to restart container');
    }
}

async function deleteContainer(id, name) {
    if (!confirm(`Delete container "${name}"?\n\nThis will stop and remove the container permanently.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/datasources/${id}`, { method: 'DELETE' });
        if (response.ok) {
            showSuccess(`Container "${name}" deleted`);
            loadContainers();
        }
    } catch (error) {
        showError('Failed to delete container');
    }
}

// =====================
// LOGS
// =====================

async function viewContainerLogs(id, name) {
    currentContainerId = id;
    document.querySelector('#logsModal h2').textContent = `📋 Logs: ${name}`;
    document.getElementById('logsModal').style.display = 'block';
    refreshLogs();
}

async function refreshLogs() {
    if (!currentContainerId) return;

    const logsContent = document.getElementById('logs-content');
    const lines = document.getElementById('log-lines').value;

    logsContent.textContent = 'Loading logs...';

    try {
        const response = await fetch(`${API_URL}/datasources/${currentContainerId}/logs?lines=${lines}`);
        const data = await response.json();
        logsContent.textContent = data.logs || 'No logs available';
    } catch (error) {
        logsContent.textContent = `Error fetching logs: ${error.message}`;
    }
}

function downloadLogs() {
    const logs = document.getElementById('logs-content').textContent;
    const blob = new Blob([logs], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `container-${currentContainerId}-logs.txt`;
    a.click();

    URL.revokeObjectURL(url);
}

function closeLogsModal() {
    document.getElementById('logsModal').style.display = 'none';
    currentContainerId = null;
}

// =====================
// IMAGES
// =====================

async function loadImages() {
    const tbody = document.querySelector('#images-table tbody');

    // Simulate images (in production, call Docker API)
    const mockImages = [
        { repository: 'postgres', tag: '16-alpine', id: 'abc123', size: '245 MB', created: '2 weeks ago' },
        { repository: 'mysql', tag: '8', id: 'def456', size: '521 MB', created: '1 month ago' },
        { repository: 'mongodb', tag: 'latest', id: 'ghi789', size: '698 MB', created: '3 weeks ago' },
        { repository: 'redis', tag: 'alpine', id: 'jkl012', size: '42 MB', created: '1 week ago' }
    ];

    images = mockImages;
    document.getElementById('total-images').textContent = images.length;

    tbody.innerHTML = '';

    images.forEach(image => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${image.repository}:${image.tag}</strong></td>
            <td><code style="font-size: 12px;">${image.id}</code></td>
            <td>${image.size}</td>
            <td>${image.created}</td>
            <td>
                <div class="btn-group">
                    <button class="btn btn-sm" onclick="inspectImage('${image.repository}:${image.tag}')">🔍 Inspect</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteImage('${image.repository}:${image.tag}')">🗑️ Delete</button>
                </div>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function pullImage() {
    const imageName = prompt('Enter Docker image name (e.g., postgres:16-alpine):');
    if (!imageName) return;

    showSuccess(`Pulling image: ${imageName}`);
    // Implement pull logic with backend
    setTimeout(() => {
        showSuccess(`Image ${imageName} pulled successfully`);
        loadImages();
    }, 2000);
}

function inspectImage(imageName) {
    alert(`Image: ${imageName}\n\nInspection details would be shown here.\n(Implement with Docker API)`);
}

function deleteImage(imageName) {
    if (!confirm(`Delete image ${imageName}?\n\nThis action cannot be undone.`)) return;

    showSuccess(`Deleting image: ${imageName}`);
    setTimeout(() => {
        loadImages();
    }, 1000);
}

// =====================
// VOLUMES
// =====================

async function loadVolumes() {
    const tbody = document.querySelector('#volumes-table tbody');

    // Mock volumes
    const mockVolumes = [
        { name: 'quantum_postgres_data', driver: 'local', mountpoint: '/var/lib/docker/volumes/quantum_postgres_data' },
        { name: 'quantum_mysql_data', driver: 'local', mountpoint: '/var/lib/docker/volumes/quantum_mysql_data' }
    ];

    if (mockVolumes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No volumes found</td></tr>';
        return;
    }

    tbody.innerHTML = '';

    mockVolumes.forEach(volume => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${volume.name}</strong></td>
            <td>${volume.driver}</td>
            <td><code style="font-size: 11px;">${volume.mountpoint}</code></td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="deleteVolume('${volume.name}')">🗑️ Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function createVolume() {
    const volumeName = prompt('Enter volume name:');
    if (!volumeName) return;

    showSuccess(`Creating volume: ${volumeName}`);
    setTimeout(() => {
        loadVolumes();
    }, 1000);
}

function deleteVolume(name) {
    if (!confirm(`Delete volume "${name}"?\n\nAll data will be lost!`)) return;

    showSuccess(`Deleting volume: ${name}`);
    setTimeout(() => {
        loadVolumes();
    }, 1000);
}

// =====================
// NETWORKS
// =====================

async function loadNetworks() {
    const tbody = document.querySelector('#networks-table tbody');

    // Mock networks
    const mockNetworks = [
        { name: 'bridge', driver: 'bridge', scope: 'local', containers: 3 },
        { name: 'host', driver: 'host', scope: 'local', containers: 0 },
        { name: 'quantum_network', driver: 'bridge', scope: 'local', containers: 5 }
    ];

    tbody.innerHTML = '';

    mockNetworks.forEach(network => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${network.name}</strong></td>
            <td>${network.driver}</td>
            <td>${network.scope}</td>
            <td>${network.containers}</td>
            <td>
                ${network.name !== 'bridge' && network.name !== 'host' ?
                    `<button class="btn btn-sm btn-danger" onclick="deleteNetwork('${network.name}')">🗑️ Delete</button>` :
                    '<span style="color: #999;">System network</span>'
                }
            </td>
        `;
        tbody.appendChild(row);
    });
}

function createNetwork() {
    const networkName = prompt('Enter network name:');
    if (!networkName) return;

    showSuccess(`Creating network: ${networkName}`);
    setTimeout(() => {
        loadNetworks();
    }, 1000);
}

function deleteNetwork(name) {
    if (!confirm(`Delete network "${name}"?`)) return;

    showSuccess(`Deleting network: ${name}`);
    setTimeout(() => {
        loadNetworks();
    }, 1000);
}

// =====================
// UTILITIES
// =====================

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
}

function showSuccess(message) {
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ ' + message);
}

// Auto-refresh containers every 10 seconds
setInterval(() => {
    loadContainers();
}, 10000);
