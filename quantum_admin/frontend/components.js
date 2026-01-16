// Component directories to scan
const COMPONENT_DIRS = ['../components', '../src/components', './components'];

// Global state
let components = [];
let currentComponent = null;

// Load initial data
window.addEventListener('DOMContentLoaded', function() {
    loadComponents();

    // Search functionality
    document.getElementById('search-components').addEventListener('input', function(e) {
        filterComponents(e.target.value);
    });
});

// =====================
// COMPONENT LOADING
// =====================

async function loadComponents() {
    // Mock component data (in production, scan filesystem via API)
    const mockComponents = [
        {
            path: 'components/home.q',
            name: 'home.q',
            size: '2.4 KB',
            lines: 45,
            modified: '2 hours ago',
            content: `<?quantum version="1.0"?>
<component name="home">
    <h1>Welcome to Quantum</h1>
    <p>Hello, {user.name}!</p>

    <div class="stats">
        <loop array="stats">
            <div class="stat-card">
                <h3>{item.value}</h3>
                <p>{item.label}</p>
            </div>
        </loop>
    </div>
</component>`
        },
        {
            path: 'components/auth/login.q',
            name: 'login.q',
            size: '3.1 KB',
            lines: 67,
            modified: '1 day ago',
            content: `<?quantum version="1.0"?>
<component name="login">
    <form action="/auth/login" method="POST">
        <input type="text" name="username" placeholder="Username" />
        <input type="password" name="password" placeholder="Password" />
        <button type="submit">Login</button>
    </form>

    <if condition="{error}">
        <div class="error">{error}</div>
    </if>
</component>`
        },
        {
            path: 'components/dashboard/stats.q',
            name: 'stats.q',
            size: '1.8 KB',
            lines: 32,
            modified: '3 hours ago',
            content: `<?quantum version="1.0"?>
<component name="stats">
    <div class="stats-grid">
        <loop array="metrics">
            <div class="stat-card">
                <h2>{item.value}</h2>
                <p>{item.name}</p>
                <span class="trend {item.trend}">{item.change}</span>
            </div>
        </loop>
    </div>
</component>`
        },
        {
            path: 'components/users/profile.q',
            name: 'profile.q',
            size: '4.2 KB',
            lines: 89,
            modified: '5 hours ago',
            content: `<?quantum version="1.0"?>
<component name="profile">
    <div class="profile-header">
        <img src="{user.avatar}" alt="{user.name}" />
        <h1>{user.name}</h1>
        <p>{user.email}</p>
    </div>

    <div class="profile-info">
        <if condition="{user.isAdmin}">
            <span class="badge">Administrator</span>
        </if>

        <p>Member since: {user.createdAt}</p>
        <p>Last login: {user.lastLogin}</p>
    </div>
</component>`
        }
    ];

    components = mockComponents;

    // Update stats
    updateStats();

    // Render file tree
    renderFileTree();
}

function updateStats() {
    document.getElementById('total-components').textContent = components.length;

    // Count unique directories
    const dirs = new Set(components.map(c => c.path.split('/').slice(0, -1).join('/')));
    document.getElementById('total-folders').textContent = dirs.size;

    // Total lines
    const totalLines = components.reduce((sum, c) => sum + c.lines, 0);
    document.getElementById('total-lines').textContent = totalLines;

    // Last modified
    if (components.length > 0) {
        document.getElementById('last-modified').textContent = components[0].modified;
    }
}

function renderFileTree() {
    const treeDiv = document.getElementById('file-tree');

    // Build tree structure
    const tree = {};

    components.forEach(comp => {
        const parts = comp.path.split('/');
        let current = tree;

        parts.forEach((part, index) => {
            if (index === parts.length - 1) {
                // File
                if (!current._files) current._files = [];
                current._files.push(comp);
            } else {
                // Directory
                if (!current[part]) current[part] = {};
                current = current[part];
            }
        });
    });

    // Render tree HTML
    treeDiv.innerHTML = renderTreeNode(tree, 0);
}

function renderTreeNode(node, level) {
    let html = '';

    // Render directories
    for (const key in node) {
        if (key === '_files') continue;

        const indent = '&nbsp;'.repeat(level * 4);
        html += `
            <div style="cursor: pointer; padding: 4px 0;" onclick="toggleFolder(this)">
                ${indent}📁 <strong>${key}</strong>
            </div>
            <div class="folder-contents">${renderTreeNode(node[key], level + 1)}</div>
        `;
    }

    // Render files
    if (node._files) {
        node._files.forEach(file => {
            const indent = '&nbsp;'.repeat(level * 4);
            html += `
                <div style="cursor: pointer; padding: 4px 0; color: #667eea;" onclick='viewComponent(${JSON.stringify(file).replace(/'/g, "&#39;")})'>
                    ${indent}📄 ${file.name}
                </div>
            `;
        });
    }

    return html;
}

function toggleFolder(element) {
    const contents = element.nextElementSibling;
    if (contents && contents.classList.contains('folder-contents')) {
        if (contents.style.display === 'none') {
            contents.style.display = 'block';
        } else {
            contents.style.display = 'none';
        }
    }
}

function filterComponents(query) {
    if (!query) {
        renderFileTree();
        return;
    }

    const filtered = components.filter(c =>
        c.name.toLowerCase().includes(query.toLowerCase()) ||
        c.path.toLowerCase().includes(query.toLowerCase())
    );

    const treeDiv = document.getElementById('file-tree');
    treeDiv.innerHTML = filtered.map(comp => `
        <div style="cursor: pointer; padding: 4px 0; color: #667eea;" onclick='viewComponent(${JSON.stringify(comp).replace(/'/g, "&#39;")})'>
            📄 ${comp.path}
        </div>
    `).join('');
}

// =====================
// COMPONENT VIEWER
// =====================

function viewComponent(component) {
    currentComponent = component;

    // Update header
    document.getElementById('component-title').textContent = `📄 ${component.path}`;
    document.getElementById('format-btn').style.display = 'inline-block';
    document.getElementById('download-btn').style.display = 'inline-block';

    // Render component code
    const viewer = document.getElementById('component-viewer');
    viewer.innerHTML = `
        <pre style="background: #f8f9fa; padding: 20px; border-radius: 8px; overflow-x: auto; font-family: 'Monaco', 'Courier New', monospace; font-size: 13px; line-height: 1.6; margin: 0;">${escapeHtml(component.content)}</pre>
    `;

    // Analyze component
    analyzeComponent(component);
}

function analyzeComponent(component) {
    const analysisSection = document.getElementById('analysis-section');
    analysisSection.style.display = 'block';

    // Extract elements
    const elementRegex = /<(\w+)/g;
    const elements = new Set();
    let match;

    while ((match = elementRegex.exec(component.content)) !== null) {
        elements.add(match[1]);
    }

    // Extract variables/expressions
    const variableRegex = /\{([^}]+)\}/g;
    const variables = new Set();

    while ((match = variableRegex.exec(component.content)) !== null) {
        variables.add(match[1]);
    }

    // Render elements
    const elementsList = document.querySelector('#elements-list ul');
    elementsList.innerHTML = Array.from(elements).map(el =>
        `<li style="padding: 4px 0;"><span class="badge default">&lt;${el}&gt;</span></li>`
    ).join('');

    // Render variables
    const variablesList = document.querySelector('#variables-list ul');
    variablesList.innerHTML = Array.from(variables).map(v =>
        `<li style="padding: 4px 0;"><code>{${v}}</code></li>`
    ).join('');

    // Update stats
    document.getElementById('stat-filesize').textContent = component.size;
    document.getElementById('stat-lines').textContent = component.lines;
    document.getElementById('stat-elements').textContent = elements.size;

    // Calculate complexity (simple heuristic)
    const complexity = elements.size + variables.size + (component.content.match(/<loop/g) || []).length * 2;
    document.getElementById('stat-complexity').textContent = complexity;
}

function formatComponent() {
    if (!currentComponent) return;

    // Simple formatting (add proper indentation)
    let formatted = currentComponent.content;

    // This is a placeholder - implement proper XML formatting
    formatted = formatted.replace(/></g, '>\n<');

    currentComponent.content = formatted;
    viewComponent(currentComponent);

    showSuccess('Component formatted');
}

function downloadComponent() {
    if (!currentComponent) return;

    const blob = new Blob([currentComponent.content], { type: 'text/xml' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = currentComponent.name;
    a.click();

    URL.revokeObjectURL(url);
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
    alert('✅ ' + message);
}
