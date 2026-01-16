/**
 * Quantum Admin - Database Schema Viewer
 * Visualize and manage database schema
 */

const API_BASE = 'http://localhost:8000';

let currentSchema = null;
let selectedTable = null;

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    mermaid.initialize({ startOnLoad: false, theme: 'default' });
    loadSchema();
});

// ============================================================================
// Schema Loading
// ============================================================================

async function loadSchema() {
    try {
        const response = await fetch(`${API_BASE}/schema/inspect`);
        const data = await response.json();

        currentSchema = data;
        renderStats(data);
        renderTableList(data.tables);
        renderERD(data.mermaid);
        renderRelationships(data.relationships);

    } catch (error) {
        console.error('Error loading schema:', error);
        alert('Failed to load database schema');
    }
}

async function refreshSchema() {
    await loadSchema();
    alert('Schema refreshed successfully!');
}

// ============================================================================
// Stats Rendering
// ============================================================================

function renderStats(schema) {
    const statsHtml = `
        <div class="stat-card">
            <div class="stat-value">${Object.keys(schema.tables).length}</div>
            <div class="stat-label">Total Tables</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="stat-value">${getTotalColumns(schema.tables)}</div>
            <div class="stat-label">Total Columns</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <div class="stat-value">${schema.relationships.length}</div>
            <div class="stat-label">Relationships</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <div class="stat-value">${schema.database_type.toUpperCase()}</div>
            <div class="stat-label">Database Type</div>
        </div>
    `;

    document.getElementById('stats-grid').innerHTML = statsHtml;
}

function getTotalColumns(tables) {
    return Object.values(tables).reduce((sum, table) => sum + table.columns.length, 0);
}

// ============================================================================
// Table List Rendering
// ============================================================================

function renderTableList(tables) {
    const tableList = document.getElementById('table-list');
    tableList.innerHTML = '';

    for (const [tableName, tableInfo] of Object.entries(tables)) {
        const tableItem = document.createElement('div');
        tableItem.className = 'table-item';
        tableItem.innerHTML = `
            <div class="table-name">${tableName}</div>
            <div class="table-meta">${tableInfo.columns.length} columns</div>
        `;

        tableItem.onclick = () => selectTable(tableName, tableInfo);
        tableList.appendChild(tableItem);
    }
}

function selectTable(tableName, tableInfo) {
    selectedTable = { name: tableName, info: tableInfo };

    // Update active state
    document.querySelectorAll('.table-item').forEach(item => {
        item.classList.remove('active');
        if (item.querySelector('.table-name').textContent === tableName) {
            item.classList.add('active');
        }
    });

    // Switch to columns tab and render
    switchTab('columns');
    renderTableColumns(tableName, tableInfo);
}

// ============================================================================
// Tab Switching
// ============================================================================

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Load tab-specific content
    if (tabName === 'models') {
        loadSQLAlchemyModels();
    } else if (tabName === 'migrations') {
        loadMigrations();
    }
}

// ============================================================================
// ERD Rendering
// ============================================================================

async function renderERD(mermaidCode) {
    const element = document.getElementById('erd-diagram');

    try {
        const { svg } = await mermaid.render('erd-svg', mermaidCode);
        element.innerHTML = svg;
    } catch (error) {
        console.error('Error rendering ERD:', error);
        element.innerHTML = '<p>Error rendering diagram. Check console for details.</p>';
    }
}

// ============================================================================
// Table Columns Rendering
// ============================================================================

function renderTableColumns(tableName, tableInfo) {
    document.getElementById('selected-table-name').textContent = tableName;

    const tbody = document.querySelector('#columns-table tbody');
    tbody.innerHTML = '';

    const pkColumns = tableInfo.primary_key.constrained_columns || [];
    const fkColumns = tableInfo.foreign_keys.flatMap(fk => fk.constrained_columns);

    for (const column of tableInfo.columns) {
        const tr = document.createElement('tr');

        const badges = [];
        if (pkColumns.includes(column.name)) {
            badges.push('<span class="badge badge-pk">PK</span>');
        }
        if (fkColumns.includes(column.name)) {
            badges.push('<span class="badge badge-fk">FK</span>');
        }
        if (column.nullable) {
            badges.push('<span class="badge badge-nullable">NULL</span>');
        }

        tr.innerHTML = `
            <td><strong>${column.name}</strong></td>
            <td><code>${column.type}</code></td>
            <td>${badges.join('')}</td>
            <td>${column.default || '-'}</td>
        `;

        tbody.appendChild(tr);
    }
}

// ============================================================================
// Relationships Rendering
// ============================================================================

function renderRelationships(relationships) {
    const tbody = document.getElementById('relationships-tbody');
    tbody.innerHTML = '';

    for (const rel of relationships) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${rel.from_table}</strong></td>
            <td>${rel.from_columns.join(', ')}</td>
            <td><strong>${rel.to_table}</strong></td>
            <td>${rel.to_columns.join(', ')}</td>
            <td>${rel.constraint_name || '-'}</td>
        `;
        tbody.appendChild(tr);
    }
}

// ============================================================================
// SQLAlchemy Models
// ============================================================================

async function loadSQLAlchemyModels() {
    try {
        const response = await fetch(`${API_BASE}/schema/models`);
        const data = await response.json();

        document.getElementById('models-code').textContent = data.models;

    } catch (error) {
        console.error('Error loading models:', error);
    }
}

async function downloadModels() {
    const modelsCode = document.getElementById('models-code').textContent;

    const blob = new Blob([modelsCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'models.py';
    a.click();
    URL.revokeObjectURL(url);
}

async function copyModels() {
    const modelsCode = document.getElementById('models-code').textContent;

    try {
        await navigator.clipboard.writeText(modelsCode);
        alert('Models copied to clipboard!');
    } catch (error) {
        console.error('Failed to copy:', error);
    }
}

// ============================================================================
// Export Functions
// ============================================================================

async function exportSchema() {
    const format = prompt('Export format (json/mermaid/dbml/dot/models):', 'json');

    if (!format) return;

    try {
        const response = await fetch(`${API_BASE}/schema/export?format=${format}`);
        const data = await response.json();

        const blob = new Blob([data.content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `schema.${format}`;
        a.click();
        URL.revokeObjectURL(url);

    } catch (error) {
        console.error('Error exporting schema:', error);
        alert('Failed to export schema');
    }
}

async function downloadERD(format) {
    try {
        const response = await fetch(`${API_BASE}/schema/export?format=${format}`);
        const data = await response.json();

        const blob = new Blob([data.content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `erd.${format}`;
        a.click();
        URL.revokeObjectURL(url);

    } catch (error) {
        console.error('Error downloading ERD:', error);
    }
}

// ============================================================================
// Migrations
// ============================================================================

async function loadMigrations() {
    try {
        const response = await fetch(`${API_BASE}/schema/migrations`);
        const data = await response.json();

        const migrationsHtml = data.migrations.map(migration => `
            <div class="card" style="margin-bottom: 16px;">
                <div class="card-header">
                    <h3>${migration.revision}</h3>
                    <span>${migration.created_at}</span>
                </div>
                <p>${migration.message}</p>
            </div>
        `).join('');

        document.getElementById('migrations-list').innerHTML = migrationsHtml || '<p>No migrations yet</p>';

    } catch (error) {
        console.error('Error loading migrations:', error);
    }
}

async function createMigration() {
    const message = prompt('Migration message:');

    if (!message) return;

    try {
        const response = await fetch(`${API_BASE}/schema/migrations/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const data = await response.json();
        alert(`Migration created: ${data.revision}`);
        loadMigrations();

    } catch (error) {
        console.error('Error creating migration:', error);
        alert('Failed to create migration');
    }
}

async function runMigrations() {
    if (!confirm('Run all pending migrations?')) return;

    try {
        const response = await fetch(`${API_BASE}/schema/migrations/upgrade`, {
            method: 'POST'
        });

        const data = await response.json();
        alert(data.message);
        loadMigrations();

    } catch (error) {
        console.error('Error running migrations:', error);
        alert('Failed to run migrations');
    }
}

async function rollbackMigration() {
    if (!confirm('Rollback last migration?')) return;

    try {
        const response = await fetch(`${API_BASE}/schema/migrations/downgrade`, {
            method: 'POST'
        });

        const data = await response.json();
        alert(data.message);
        loadMigrations();

    } catch (error) {
        console.error('Error rolling back migration:', error);
        alert('Failed to rollback migration');
    }
}
