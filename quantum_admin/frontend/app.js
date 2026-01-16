// API Base URL
const API_URL = 'http://localhost:8000';

// Load initial data
window.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('stat-components')) {
        refreshStats();
        loadDatasources();
    }
});

async function refreshStats() {
    try {
        const response = await fetch(`${API_URL}/projects`);
        const projects = await response.json();

        // Update stats
        if (document.getElementById('stat-components')) {
            document.getElementById('stat-components').textContent = '12';
            document.getElementById('stat-datasources').textContent = projects.length;
            document.getElementById('stat-containers').textContent = '3';
            document.getElementById('stat-endpoints').textContent = '8';
        }
    } catch (error) {
        console.error('Error fetching stats:', error);
    }
}

async function loadDatasources() {
    const tbody = document.querySelector('#datasources-table tbody');
    if (!tbody) return;

    try {
        const response = await fetch(`${API_URL}/projects`);
        const projects = await response.json();

        if (projects.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">No datasources yet. Create one to get started!</td></tr>';
            return;
        }

        tbody.innerHTML = '';

        for (const project of projects) {
            const dsResponse = await fetch(`${API_URL}/projects/${project.id}/datasources`);
            const datasources = await dsResponse.json();

            datasources.forEach(ds => {
                const row = document.createElement('tr');
                const typeUpper = ds.type ? ds.type.toUpperCase() : 'UNKNOWN';
                row.innerHTML = `
                    <td><strong>${ds.name}</strong></td>
                    <td>${typeUpper}</td>
                    <td><span class="badge success">Running</span></td>
                    <td>${ds.host || 'localhost'}:${ds.port}</td>
                    <td>
                        <button class="btn" onclick="manageDatasource(${ds.id})">Manage</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading datasources:', error);
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">⚠️ Error loading datasources. Make sure Admin API is running.</td></tr>';
    }
}

function manageDatasource(id) {
    window.location.href = `datasource.html?id=${id}`;
}

// Auto-refresh every 30 seconds
setInterval(refreshStats, 30000);
