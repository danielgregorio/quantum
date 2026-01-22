/**
 * Visual Query Builder
 */

let currentDatasource = null;
let currentTable = null;
let selectedFields = [];
let conditions = [];

// Mock data
const MOCK_TABLES = {
    'users': ['id', 'name', 'email', 'role', 'created_at'],
    'posts': ['id', 'user_id', 'title', 'content', 'published_at'],
    'comments': ['id', 'post_id', 'user_id', 'text', 'created_at']
};

// Initialize
window.addEventListener('DOMContentLoaded', function() {
    loadDatasources();
    updateSQL();

    // Auto-update SQL on changes
    document.addEventListener('change', updateSQL);
    document.addEventListener('input', debounce(updateSQL, 500));
});

// Load datasources
async function loadDatasources() {
    const select = document.getElementById('datasource-select');

    // Mock datasources
    const datasources = [
        { id: 1, name: 'postgres_main' },
        { id: 2, name: 'mysql_analytics' }
    ];

    datasources.forEach(ds => {
        const option = document.createElement('option');
        option.value = ds.id;
        option.textContent = ds.name;
        select.appendChild(option);
    });

    select.addEventListener('change', function() {
        currentDatasource = this.value;
        loadTables();
    });
}

// Load tables
function loadTables() {
    const select = document.getElementById('table-select');
    select.innerHTML = '<option value="">Choose a table...</option>';

    Object.keys(MOCK_TABLES).forEach(table => {
        const option = document.createElement('option');
        option.value = table;
        option.textContent = table;
        select.appendChild(option);
    });
}

// Load table fields
function loadTableFields() {
    const table = document.getElementById('table-select').value;
    if (!table) return;

    currentTable = table;
    const fields = MOCK_TABLES[table];

    // Update fields selector
    const container = document.getElementById('fields-container');
    container.innerHTML = '';

    fields.forEach(field => {
        const chip = document.createElement('div');
        chip.className = 'field-chip';
        chip.textContent = field;
        chip.onclick = () => toggleField(field, chip);
        container.appendChild(chip);
    });

    // Update order by
    const orderBy = document.getElementById('order-by');
    orderBy.innerHTML = '<option value="">None</option>';
    fields.forEach(field => {
        const option = document.createElement('option');
        option.value = field;
        option.textContent = field;
        orderBy.appendChild(option);
    });

    updateSQL();
}

// Toggle field selection
function toggleField(field, chip) {
    const index = selectedFields.indexOf(field);

    if (index > -1) {
        selectedFields.splice(index, 1);
        chip.classList.remove('selected');
    } else {
        selectedFields.push(field);
        chip.classList.add('selected');
    }

    document.getElementById('select-all-fields').checked = false;
    updateSQL();
}

// Toggle all fields
function toggleAllFields() {
    const selectAll = document.getElementById('select-all-fields').checked;

    if (selectAll) {
        selectedFields = ['*'];
        document.querySelectorAll('.field-chip').forEach(chip => {
            chip.classList.remove('selected');
        });
    } else {
        selectedFields = [];
        document.querySelectorAll('.field-chip').forEach(chip => {
            chip.classList.remove('selected');
        });
    }

    updateSQL();
}

// Add condition
function addCondition() {
    if (!currentTable) {
        Quantum.notify.warning('Please select a table first');
        return;
    }

    const fields = MOCK_TABLES[currentTable];
    const container = document.getElementById('conditions-container');

    const row = document.createElement('div');
    row.className = 'condition-row';
    row.innerHTML = `
        <select class="condition-field">
            ${fields.map(f => `<option value="${f}">${f}</option>`).join('')}
        </select>
        <select class="condition-operator">
            <option value="=">=</option>
            <option value="!=">!=</option>
            <option value=">">></option>
            <option value="<"><</option>
            <option value=">=">>=</option>
            <option value="<="><=</option>
            <option value="LIKE">LIKE</option>
            <option value="IN">IN</option>
        </select>
        <input type="text" class="condition-value" placeholder="Value">
        <button class="btn btn-sm btn-danger" onclick="this.parentElement.remove(); updateSQL()">🗑️</button>
    `;

    container.appendChild(row);
    updateSQL();
}

// Update SQL
function updateSQL() {
    const table = currentTable;
    if (!table) {
        document.getElementById('sql-output').innerHTML = '<span style="color: #999;">-- Select a table to begin</span>';
        return;
    }

    // SELECT
    let sql = 'SELECT ';
    if (selectedFields.length === 0 || selectedFields.includes('*')) {
        sql += '*';
    } else {
        sql += selectedFields.join(', ');
    }

    // FROM
    sql += `\nFROM ${table}`;

    // WHERE
    const conditionRows = document.querySelectorAll('.condition-row');
    if (conditionRows.length > 0) {
        const whereClauses = [];

        conditionRows.forEach(row => {
            const field = row.querySelector('.condition-field').value;
            const operator = row.querySelector('.condition-operator').value;
            const value = row.querySelector('.condition-value').value;

            if (value) {
                if (operator === 'LIKE') {
                    whereClauses.push(`${field} LIKE '%${value}%'`);
                } else if (operator === 'IN') {
                    whereClauses.push(`${field} IN (${value})`);
                } else {
                    whereClauses.push(`${field} ${operator} '${value}'`);
                }
            }
        });

        if (whereClauses.length > 0) {
            sql += '\nWHERE ' + whereClauses.join('\n  AND ');
        }
    }

    // ORDER BY
    const orderBy = document.getElementById('order-by').value;
    if (orderBy) {
        const direction = document.getElementById('order-direction').value;
        sql += `\nORDER BY ${orderBy} ${direction}`;
    }

    // LIMIT
    const limit = document.getElementById('limit').value;
    if (limit) {
        sql += `\nLIMIT ${limit}`;
    }

    sql += ';';

    // Display with syntax highlighting
    document.getElementById('sql-output').innerHTML = highlightSQL(sql);
}

// Syntax highlighting
function highlightSQL(sql) {
    const keywords = ['SELECT', 'FROM', 'WHERE', 'ORDER BY', 'LIMIT', 'AND', 'OR', 'LIKE', 'IN'];

    let highlighted = sql;

    keywords.forEach(keyword => {
        const regex = new RegExp(`\\b${keyword}\\b`, 'g');
        highlighted = highlighted.replace(regex, `<span style="color: #569cd6;">${keyword}</span>`);
    });

    // Table names
    highlighted = highlighted.replace(/FROM\s+(\w+)/g, 'FROM <span style="color: #4ec9b0;">$1</span>');

    // Strings
    highlighted = highlighted.replace(/'([^']*)'/g, '<span style="color: #ce9178;">\'$1\'</span>');

    // Numbers
    highlighted = highlighted.replace(/\b(\d+)\b/g, '<span style="color: #b5cea8;">$1</span>');

    return highlighted;
}

// Execute query
async function executeQuery() {
    const sql = document.getElementById('sql-output').textContent;

    if (!currentDatasource) {
        Quantum.notify.error('Please select a datasource');
        return;
    }

    try {
        const response = await fetch(`http://localhost:8000/query/execute`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                datasource_id: currentDatasource,
                query: sql
            })
        });

        const data = await response.json();

        if (response.ok) {
            displayResults(data.results);
            Quantum.notify.success(`Query executed: ${data.results.length} rows`);
        } else {
            Quantum.notify.error('Query failed: ' + data.detail);
        }
    } catch (error) {
        // Mock results for demo
        displayMockResults();
    }
}

// Display results
function displayResults(results) {
    document.getElementById('results-section').style.display = 'block';
    document.getElementById('result-count').textContent = results.length;

    const thead = document.getElementById('results-thead');
    const tbody = document.getElementById('results-tbody');

    if (results.length === 0) {
        thead.innerHTML = '';
        tbody.innerHTML = '<tr><td>No results</td></tr>';
        return;
    }

    // Headers
    const columns = Object.keys(results[0]);
    thead.innerHTML = '<tr>' + columns.map(col => `<th>${col}</th>`).join('') + '</tr>';

    // Rows
    tbody.innerHTML = results.map(row =>
        '<tr>' + columns.map(col => `<td>${row[col]}</td>`).join('') + '</tr>'
    ).join('');
}

// Mock results
function displayMockResults() {
    const mockResults = [
        { id: 1, name: 'Alice', email: 'alice@example.com', role: 'admin' },
        { id: 2, name: 'Bob', email: 'bob@example.com', role: 'user' },
        { id: 3, name: 'Charlie', email: 'charlie@example.com', role: 'user' }
    ];

    displayResults(mockResults);
}

// Copy SQL
function copySQL() {
    const sql = document.getElementById('sql-output').textContent;
    navigator.clipboard.writeText(sql);
    Quantum.notify.success('SQL copied to clipboard');
}

// Format SQL
function formatSQL() {
    updateSQL();
    Quantum.notify.success('SQL formatted');
}

// Reset query
function resetQuery() {
    selectedFields = [];
    conditions = [];
    document.getElementById('table-select').value = '';
    document.getElementById('fields-container').innerHTML = '<p style="color: var(--text-secondary);">Select a table first</p>';
    document.getElementById('conditions-container').innerHTML = '';
    document.getElementById('select-all-fields').checked = false;
    document.getElementById('results-section').style.display = 'none';
    updateSQL();
}

// Debounce
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}
