/**
 * Quantum Admin - DevOps Page
 * Handles deployments, tasks, environments, cache, and performance monitoring
 */

const API_BASE = 'http://localhost:8000';

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    loadActiveTasks();
    loadEnvironments();
    loadCacheStats();
    loadRateLimitStatus();
    loadSlowQueries();

    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadActiveTasks();
        loadCacheStats();
    }, 30000);
});

// ============================================================================
// Tab Switching
// ============================================================================

function switchTab(event, tabId) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => content.style.display = 'none');

    // Remove active class from all tabs
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Show selected tab and mark button as active
    document.getElementById(tabId).style.display = 'block';
    event.target.classList.add('active');
}

// ============================================================================
// Deployments
// ============================================================================

async function deployApplication() {
    const environment = document.getElementById('deploy-environment').value;
    const branch = document.getElementById('deploy-branch').value;
    const runMigrations = document.getElementById('deploy-migrations').checked;

    if (!confirm(`Deploy ${branch} to ${environment}? This will affect the ${environment} environment.`)) {
        return;
    }

    try {
        // Show progress
        document.getElementById('deploy-status').style.display = 'block';
        document.getElementById('deploy-message').textContent = 'Queuing deployment...';

        const response = await fetch(`${API_BASE}/tasks/deploy`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({environment, branch, run_migrations: runMigrations})
        });

        const data = await response.json();

        if (data.task_id) {
            // Monitor task progress
            monitorDeployment(data.task_id);
        } else {
            throw new Error('Failed to queue deployment');
        }

    } catch (error) {
        console.error('Deployment error:', error);
        alert('Deployment failed: ' + error.message);
        document.getElementById('deploy-status').style.display = 'none';
    }
}

async function monitorDeployment(taskId) {
    const checkStatus = async () => {
        try {
            const response = await fetch(`${API_BASE}/tasks/${taskId}`);
            const data = await response.json();

            const state = data.state;
            const progress = data.progress || {};

            if (state === 'PROGRESS') {
                const percent = (progress.current / progress.total) * 100;
                document.getElementById('deploy-progress').style.width = percent + '%';
                document.getElementById('deploy-message').textContent = progress.status || 'Deploying...';

                // Continue monitoring
                setTimeout(checkStatus, 2000);

            } else if (state === 'SUCCESS') {
                document.getElementById('deploy-progress').style.width = '100%';
                document.getElementById('deploy-message').textContent = 'Deployment completed successfully!';
                document.getElementById('deploy-message').style.color = '#27ae60';

                setTimeout(() => {
                    document.getElementById('deploy-status').style.display = 'none';
                    document.getElementById('deploy-progress').style.width = '0%';
                    document.getElementById('deploy-message').style.color = '#7f8c8d';
                }, 3000);

            } else if (state === 'FAILURE') {
                document.getElementById('deploy-message').textContent = 'Deployment failed: ' + (data.error || 'Unknown error');
                document.getElementById('deploy-message').style.color = '#e74c3c';
            }

        } catch (error) {
            console.error('Failed to check task status:', error);
        }
    };

    checkStatus();
}

function showDeployModal() {
    document.getElementById('deploy-tab').scrollIntoView({behavior: 'smooth'});
}

// ============================================================================
// Background Tasks
// ============================================================================

async function loadActiveTasks() {
    try {
        const response = await fetch(`${API_BASE}/tasks/active`);
        const data = await response.json();

        const tasks = data.tasks || [];
        const tbody = document.getElementById('tasks-list');

        // Update count
        document.getElementById('active-tasks-count').textContent = tasks.length;

        if (tasks.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="text-align: center; color: #7f8c8d; padding: 20px;">
                        No active tasks
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = tasks.map(task => `
            <tr>
                <td><code>${task.task_id.substring(0, 8)}...</code></td>
                <td><strong>${task.task_name}</strong></td>
                <td>${task.worker}</td>
                <td><span class="badge success">Running</span></td>
                <td>${new Date(task.started_at * 1000).toLocaleString()}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="cancelTask('${task.task_id}')">
                        🛑 Cancel
                    </button>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Failed to load tasks:', error);
    }
}

async function cancelTask(taskId) {
    if (!confirm('Cancel this task?')) return;

    try {
        const response = await fetch(`${API_BASE}/tasks/${taskId}/cancel`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.status === 'cancelled') {
            alert('Task cancelled successfully');
            loadActiveTasks();
        } else {
            alert('Failed to cancel task');
        }

    } catch (error) {
        console.error('Failed to cancel task:', error);
        alert('Error cancelling task');
    }
}

// ============================================================================
// Environments
// ============================================================================

async function loadEnvironments() {
    try {
        const response = await fetch(`${API_BASE}/environments`);
        const data = await response.json();

        const environments = data.environments || [];
        const tbody = document.getElementById('environments-list');

        tbody.innerHTML = environments.map(env => `
            <tr>
                <td>
                    <strong>${env.name}</strong>
                    ${env.is_current ? '<span class="badge success" style="margin-left: 10px;">Current</span>' : ''}
                </td>
                <td><span class="badge">${env.type}</span></td>
                <td><code>${env.api_url}</code></td>
                <td>${env.debug ? '✅ Enabled' : '❌ Disabled'}</td>
                <td><span class="badge ${env.is_current ? 'success' : ''}">
                    ${env.is_current ? 'Active' : 'Inactive'}
                </span></td>
                <td>
                    ${!env.is_current ? `
                        <button class="btn btn-sm" onclick="activateEnvironment('${env.name}')">
                            ✅ Activate
                        </button>
                    ` : ''}
                    <button class="btn btn-sm" onclick="viewEnvironment('${env.name}')">
                        👁️ View
                    </button>
                    <button class="btn btn-sm" onclick="exportEnvironment('${env.name}')">
                        📥 Export
                    </button>
                </td>
            </tr>
        `).join('');

        // Update current environment in stats
        const currentEnv = environments.find(e => e.is_current);
        if (currentEnv) {
            document.getElementById('current-environment').textContent = currentEnv.name;
        }

    } catch (error) {
        console.error('Failed to load environments:', error);
    }
}

async function activateEnvironment(name) {
    if (!confirm(`Switch to ${name} environment?`)) return;

    try {
        const response = await fetch(`${API_BASE}/environments/${name}/activate`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.status === 'activated') {
            alert(`Switched to ${name} environment`);
            loadEnvironments();
        } else {
            alert('Failed to switch environment');
        }

    } catch (error) {
        console.error('Failed to activate environment:', error);
        alert('Error activating environment');
    }
}

async function viewEnvironment(name) {
    try {
        const response = await fetch(`${API_BASE}/environments/${name}`);
        const data = await response.json();

        const env = data.environment;
        const content = JSON.stringify(env, null, 2);

        alert(`Environment: ${name}\n\n${content}`);

    } catch (error) {
        console.error('Failed to view environment:', error);
        alert('Error loading environment');
    }
}

async function exportEnvironment(name) {
    try {
        const response = await fetch(`${API_BASE}/environments/${name}/export`);
        const data = await response.json();

        const envFile = data.env_file;

        // Create download
        const blob = new Blob([envFile], {type: 'text/plain'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${name}.env`;
        a.click();

    } catch (error) {
        console.error('Failed to export environment:', error);
        alert('Error exporting environment');
    }
}

// ============================================================================
// Cache Management
// ============================================================================

async function loadCacheStats() {
    try {
        const response = await fetch(`${API_BASE}/cache/stats`);
        const data = await response.json();

        document.getElementById('cache-hits').textContent = data.hits || 0;
        document.getElementById('cache-misses').textContent = data.misses || 0;
        document.getElementById('cache-total').textContent = data.total_requests || 0;
        document.getElementById('cache-errors').textContent = data.errors || 0;
        document.getElementById('cache-hit-rate').textContent = (data.hit_rate || 0) + '%';

    } catch (error) {
        console.error('Failed to load cache stats:', error);
    }
}

async function clearAllCache() {
    if (!confirm('Clear all cache? This will temporarily reduce performance.')) return;

    try {
        const response = await fetch(`${API_BASE}/cache/clear`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.status === 'success') {
            alert('Cache cleared successfully');
            loadCacheStats();
        } else {
            alert('Failed to clear cache');
        }

    } catch (error) {
        console.error('Failed to clear cache:', error);
        alert('Error clearing cache');
    }
}

// ============================================================================
// Performance Monitoring
// ============================================================================

async function loadSlowQueries() {
    try {
        const response = await fetch(`${API_BASE}/query/slow`);
        const data = await response.json();

        const queries = data.slow_queries || [];
        const tbody = document.getElementById('slow-queries-list');

        if (queries.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; color: #7f8c8d; padding: 20px;">
                        No slow queries detected
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = queries.map(q => `
            <tr>
                <td><code>${q.query.substring(0, 100)}...</code></td>
                <td><strong>${q.avg_time_ms.toFixed(2)} ms</strong></td>
                <td>${q.calls}</td>
                <td>${q.avg_time_ms.toFixed(2)} ms</td>
                <td>
                    <button class="btn btn-sm" onclick="optimizeQuery(\`${q.query.replace(/`/g, '\\`')}\`)">
                        ⚡ Optimize
                    </button>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Failed to load slow queries:', error);
    }
}

async function optimizeQuery(query) {
    try {
        const response = await fetch(`${API_BASE}/query/optimize`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query})
        });

        const data = await response.json();

        alert(`Query Optimization:\n\n` +
              `Original: ${data.original}\n\n` +
              `Optimized: ${data.optimized}\n\n` +
              `Improvement: ${data.improvement_estimate}\n\n` +
              `Changes:\n${data.changes.join('\n')}`);

    } catch (error) {
        console.error('Failed to optimize query:', error);
        alert('Error optimizing query');
    }
}

async function loadRateLimitStatus() {
    try {
        const response = await fetch(`${API_BASE}/rate-limit/status`);
        const data = await response.json();

        document.getElementById('rate-limit-remaining').textContent = data.remaining || 0;
        document.getElementById('rate-limit-limit').textContent = data.limit || 1000;
        document.getElementById('rate-limit-status').textContent = data.enabled ? 'Active' : 'Disabled';

    } catch (error) {
        console.error('Failed to load rate limit status:', error);
    }
}

// ============================================================================
// Utilities
// ============================================================================

function refreshAll() {
    loadActiveTasks();
    loadEnvironments();
    loadCacheStats();
    loadRateLimitStatus();
    loadSlowQueries();

    // Show notification
    if (window.Quantum && window.Quantum.notify) {
        window.Quantum.notify.success('All data refreshed');
    }
}
