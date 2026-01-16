// API endpoints collection
const API_ENDPOINTS = [
    { method: 'GET', path: '/health', description: 'Health check', category: 'System' },
    { method: 'GET', path: '/projects', description: 'List all projects', category: 'Projects' },
    { method: 'POST', path: '/projects', description: 'Create new project', category: 'Projects' },
    { method: 'GET', path: '/projects/{id}', description: 'Get project details', category: 'Projects' },
    { method: 'PUT', path: '/projects/{id}', description: 'Update project', category: 'Projects' },
    { method: 'DELETE', path: '/projects/{id}', description: 'Delete project', category: 'Projects' },
    { method: 'GET', path: '/projects/{id}/datasources', description: 'List datasources', category: 'Datasources' },
    { method: 'POST', path: '/projects/{id}/datasources', description: 'Create datasource', category: 'Datasources' },
    { method: 'GET', path: '/datasources/{id}', description: 'Get datasource details', category: 'Datasources' },
    { method: 'POST', path: '/datasources/{id}/start', description: 'Start container', category: 'Containers' },
    { method: 'POST', path: '/datasources/{id}/stop', description: 'Stop container', category: 'Containers' },
    { method: 'POST', path: '/datasources/{id}/restart', description: 'Restart container', category: 'Containers' },
    { method: 'GET', path: '/datasources/{id}/status', description: 'Get container status', category: 'Containers' },
    { method: 'GET', path: '/datasources/{id}/logs', description: 'Get container logs', category: 'Containers' },
    { method: 'GET', path: '/settings', description: 'Get settings', category: 'Settings' },
    { method: 'POST', path: '/settings', description: 'Save settings', category: 'Settings' },
];

// Current request
let currentRequest = {
    startTime: 0,
    endTime: 0
};

// Load initial data
window.addEventListener('DOMContentLoaded', function() {
    loadEndpoints();
    updateBodyEditor();
});

// =====================
// TAB SWITCHING
// =====================

function switchTab(tabName) {
    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

// =====================
// REQUEST BUILDER
// =====================

function addParam() {
    const paramsList = document.getElementById('params-list');
    const row = document.createElement('div');
    row.className = 'param-row';
    row.style.cssText = 'display: grid; grid-template-columns: 1fr 1fr 40px; gap: 10px; margin-bottom: 10px;';
    row.innerHTML = `
        <input type="text" placeholder="Key" class="param-key" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <input type="text" placeholder="Value" class="param-value" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <button class="btn btn-sm" onclick="this.parentElement.remove()">🗑️</button>
    `;
    paramsList.appendChild(row);
}

function addHeader() {
    const headersList = document.getElementById('headers-list');
    const row = document.createElement('div');
    row.className = 'header-row';
    row.style.cssText = 'display: grid; grid-template-columns: 1fr 1fr 40px; gap: 10px; margin-bottom: 10px;';
    row.innerHTML = `
        <input type="text" placeholder="Header Name" class="header-key" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <input type="text" placeholder="Header Value" class="header-value" style="padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <button class="btn btn-sm" onclick="this.parentElement.remove()">🗑️</button>
    `;
    headersList.appendChild(row);
}

function updateBodyEditor() {
    const bodyType = document.getElementById('body-type').value;
    const bodyContent = document.getElementById('body-content');
    const formDataEditor = document.getElementById('form-data-editor');

    if (bodyType === 'none') {
        bodyContent.style.display = 'none';
        formDataEditor.style.display = 'none';
    } else if (bodyType === 'form') {
        bodyContent.style.display = 'none';
        formDataEditor.style.display = 'block';
    } else {
        bodyContent.style.display = 'block';
        formDataEditor.style.display = 'none';

        if (bodyType === 'json') {
            bodyContent.placeholder = '{\n  "key": "value"\n}';
        } else {
            bodyContent.placeholder = 'Enter raw text here...';
        }
    }
}

// =====================
// SEND REQUEST
// =====================

async function sendRequest() {
    const method = document.getElementById('method').value;
    let url = document.getElementById('url').value;

    if (!url) {
        alert('⚠️ Please enter a URL');
        return;
    }

    // Add http:// if missing
    if (!url.startsWith('http')) {
        url = 'http://localhost:8000' + (url.startsWith('/') ? '' : '/') + url;
        document.getElementById('url').value = url;
    }

    // Build query params
    const params = new URLSearchParams();
    document.querySelectorAll('.param-row').forEach(row => {
        const key = row.querySelector('.param-key').value;
        const value = row.querySelector('.param-value').value;
        if (key) params.append(key, value);
    });

    if (params.toString()) {
        url += '?' + params.toString();
    }

    // Build headers
    const headers = {};
    document.querySelectorAll('.header-row').forEach(row => {
        const key = row.querySelector('.header-key').value;
        const value = row.querySelector('.header-value').value;
        if (key) headers[key] = value;
    });

    // Build body
    let body = null;
    const bodyType = document.getElementById('body-type').value;

    if (bodyType !== 'none' && method !== 'GET') {
        body = document.getElementById('body-content').value;

        if (bodyType === 'json' && body) {
            try {
                JSON.parse(body); // Validate JSON
            } catch (e) {
                alert('⚠️ Invalid JSON in request body');
                return;
            }
        }
    }

    // Send request
    currentRequest.startTime = performance.now();

    try {
        const options = {
            method: method,
            headers: headers
        };

        if (body && method !== 'GET') {
            options.body = body;
        }

        const response = await fetch(url, options);
        currentRequest.endTime = performance.now();

        const responseTime = (currentRequest.endTime - currentRequest.startTime).toFixed(0);

        // Display response
        displayResponse(response, responseTime);

    } catch (error) {
        currentRequest.endTime = performance.now();
        const responseTime = (currentRequest.endTime - currentRequest.startTime).toFixed(0);

        displayError(error, responseTime);
    }
}

async function displayResponse(response, responseTime) {
    const statusBadge = document.getElementById('status-badge');
    const responseTimeSpan = document.getElementById('response-time');
    const viewer = document.getElementById('response-viewer');

    // Status badge
    const statusClass = response.ok ? 'success' : 'error';
    statusBadge.innerHTML = `<span class="badge ${statusClass}">${response.status} ${response.statusText}</span>`;
    statusBadge.style.display = 'inline-block';

    // Response time
    responseTimeSpan.textContent = `⏱️ ${responseTime} ms`;

    // Response body
    const contentType = response.headers.get('content-type');
    let body = '';

    try {
        if (contentType && contentType.includes('application/json')) {
            const json = await response.json();
            body = JSON.stringify(json, null, 2);
        } else {
            body = await response.text();
        }
    } catch (e) {
        body = 'Error reading response body';
    }

    viewer.innerHTML = `
        <div style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 4px;">
            <strong>Response Headers:</strong><br>
            ${Array.from(response.headers.entries()).map(([key, value]) =>
                `<code style="font-size: 12px;">${key}: ${value}</code>`
            ).join('<br>')}
        </div>

        <div>
            <strong>Response Body:</strong>
            <pre style="background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 8px; overflow-x: auto; font-family: 'Monaco', monospace; font-size: 13px; margin-top: 10px;">${escapeHtml(body)}</pre>
        </div>
    `;
}

function displayError(error, responseTime) {
    const statusBadge = document.getElementById('status-badge');
    const responseTimeSpan = document.getElementById('response-time');
    const viewer = document.getElementById('response-viewer');

    statusBadge.innerHTML = `<span class="badge error">ERROR</span>`;
    statusBadge.style.display = 'inline-block';

    responseTimeSpan.textContent = `⏱️ ${responseTime} ms`;

    viewer.innerHTML = `
        <div style="padding: 30px; text-align: center; color: #dc3545;">
            <div style="font-size: 48px; margin-bottom: 20px;">❌</div>
            <h3>Request Failed</h3>
            <p>${error.message}</p>
        </div>
    `;
}

// =====================
// ENDPOINTS LIST
// =====================

function loadEndpoints() {
    const endpointsList = document.getElementById('endpoints-list');

    // Group by category
    const grouped = {};

    API_ENDPOINTS.forEach(endpoint => {
        if (!grouped[endpoint.category]) {
            grouped[endpoint.category] = [];
        }
        grouped[endpoint.category].push(endpoint);
    });

    // Render grouped endpoints
    endpointsList.innerHTML = '';

    Object.keys(grouped).forEach(category => {
        const categoryDiv = document.createElement('div');
        categoryDiv.style.gridColumn = '1 / -1';
        categoryDiv.innerHTML = `<h3 style="color: #2c3e50; margin-top: 20px; margin-bottom: 10px;">${category}</h3>`;
        endpointsList.appendChild(categoryDiv);

        grouped[category].forEach(endpoint => {
            const methodColor = {
                'GET': '#28a745',
                'POST': '#007bff',
                'PUT': '#ffc107',
                'PATCH': '#17a2b8',
                'DELETE': '#dc3545'
            }[endpoint.method] || '#6c757d';

            const card = document.createElement('div');
            card.className = 'endpoint-card';
            card.style.borderLeftColor = methodColor;
            card.innerHTML = `
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span class="badge" style="background: ${methodColor}; color: white; margin-right: 10px;">${endpoint.method}</span>
                    <code style="font-size: 13px;">${endpoint.path}</code>
                </div>
                <p style="color: #7f8c8d; margin: 0; font-size: 13px;">${endpoint.description}</p>
            `;

            card.onclick = () => loadEndpoint(endpoint);
            endpointsList.appendChild(card);
        });
    });
}

function loadEndpoint(endpoint) {
    document.getElementById('method').value = endpoint.method;
    document.getElementById('url').value = endpoint.path;

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    showSuccess(`Loaded endpoint: ${endpoint.method} ${endpoint.path}`);
}

function exportCollection() {
    const collection = {
        name: 'Quantum Admin API',
        endpoints: API_ENDPOINTS
    };

    const blob = new Blob([JSON.stringify(collection, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'quantum-api-collection.json';
    a.click();

    URL.revokeObjectURL(url);
    showSuccess('API collection exported');
}

// =====================
// UTILITIES
// =====================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showSuccess(message) {
    // Simple notification (could be improved with toast)
    console.log('✅', message);
}
