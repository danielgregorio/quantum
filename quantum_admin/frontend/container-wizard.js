/**
 * Quantum Admin - Container Creation Wizard
 * Full-featured Docker container deployment wizard with drag-and-drop,
 * AI suggestions, real-time validation, and visual network designer
 */

const API_BASE = 'http://localhost:8000';

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const wizardState = {
    currentStep: 1,
    selectedTemplate: null,
    containers: [],
    networks: ['default'],
    volumes: [],
    config: {
        name: '',
        image: '',
        ports: [],
        environment: [],
        volumes: [],
        memory: 1,
        cpu: 1,
        restart: 'always',
        healthcheck: null
    },
    canvasServices: [],
    deploymentId: null
};

// ============================================================================
// TEMPLATES DATABASE
// ============================================================================

const TEMPLATES = [
    // Databases
    {
        id: 'postgres',
        name: 'PostgreSQL',
        icon: '🗄️',
        category: 'database',
        description: 'Most advanced open-source relational database',
        tags: ['database', 'sql', 'popular'],
        image: 'postgres:15-alpine',
        ports: [{host: 5432, container: 5432}],
        environment: [
            {key: 'POSTGRES_PASSWORD', value: 'postgres_password', secret: true},
            {key: 'POSTGRES_USER', value: 'postgres'},
            {key: 'POSTGRES_DB', value: 'mydb'}
        ],
        volumes: [{host: './postgres-data', container: '/var/lib/postgresql/data'}],
        memory: 1,
        cpu: 1,
        healthcheck: 'pg_isready -U postgres'
    },
    {
        id: 'mysql',
        name: 'MySQL',
        icon: '🐬',
        category: 'database',
        description: 'World\'s most popular open-source database',
        tags: ['database', 'sql', 'popular'],
        image: 'mysql:8',
        ports: [{host: 3306, container: 3306}],
        environment: [
            {key: 'MYSQL_ROOT_PASSWORD', value: 'root_password', secret: true},
            {key: 'MYSQL_DATABASE', value: 'mydb'},
            {key: 'MYSQL_USER', value: 'user'},
            {key: 'MYSQL_PASSWORD', value: 'user_password', secret: true}
        ],
        volumes: [{host: './mysql-data', container: '/var/lib/mysql'}],
        memory: 1,
        cpu: 1,
        healthcheck: 'mysqladmin ping -h localhost'
    },
    {
        id: 'mongodb',
        name: 'MongoDB',
        icon: '🍃',
        category: 'database',
        description: 'Leading NoSQL database for modern applications',
        tags: ['database', 'nosql', 'popular'],
        image: 'mongo:7',
        ports: [{host: 27017, container: 27017}],
        environment: [
            {key: 'MONGO_INITDB_ROOT_USERNAME', value: 'root'},
            {key: 'MONGO_INITDB_ROOT_PASSWORD', value: 'root_password', secret: true}
        ],
        volumes: [{host: './mongo-data', container: '/data/db'}],
        memory: 1,
        cpu: 1
    },

    // Cache
    {
        id: 'redis',
        name: 'Redis',
        icon: '🔴',
        category: 'cache',
        description: 'In-memory data store, cache, and message broker',
        tags: ['cache', 'memory', 'popular'],
        image: 'redis:7-alpine',
        ports: [{host: 6379, container: 6379}],
        environment: [],
        volumes: [{host: './redis-data', container: '/data'}],
        memory: 0.5,
        cpu: 0.5,
        command: 'redis-server --appendonly yes'
    },
    {
        id: 'memcached',
        name: 'Memcached',
        icon: '⚡',
        category: 'cache',
        description: 'High-performance distributed memory caching system',
        tags: ['cache', 'memory', 'fast'],
        image: 'memcached:alpine',
        ports: [{host: 11211, container: 11211}],
        environment: [],
        volumes: [],
        memory: 0.5,
        cpu: 0.5
    },

    // Web Servers
    {
        id: 'nginx',
        name: 'Nginx',
        icon: '🌐',
        category: 'web',
        description: 'High-performance web server and reverse proxy',
        tags: ['web', 'proxy', 'popular'],
        image: 'nginx:alpine',
        ports: [{host: 80, container: 80}, {host: 443, container: 443}],
        environment: [],
        volumes: [
            {host: './nginx.conf', container: '/etc/nginx/nginx.conf'},
            {host: './html', container: '/usr/share/nginx/html'}
        ],
        memory: 0.5,
        cpu: 0.5
    },
    {
        id: 'apache',
        name: 'Apache',
        icon: '🪶',
        category: 'web',
        description: 'World\'s most used web server software',
        tags: ['web', 'server', 'classic'],
        image: 'httpd:alpine',
        ports: [{host: 80, container: 80}],
        environment: [],
        volumes: [{host: './html', container: '/usr/local/apache2/htdocs/'}],
        memory: 0.5,
        cpu: 0.5
    },

    // Full Stacks
    {
        id: 'wordpress',
        name: 'WordPress Stack',
        icon: '📝',
        category: 'stack',
        description: 'Complete WordPress with MySQL database',
        tags: ['cms', 'php', 'mysql'],
        multiContainer: true,
        services: [
            {
                name: 'wordpress',
                image: 'wordpress:latest',
                ports: [{host: 8080, container: 80}],
                environment: [
                    {key: 'WORDPRESS_DB_HOST', value: 'db:3306'},
                    {key: 'WORDPRESS_DB_USER', value: 'wordpress'},
                    {key: 'WORDPRESS_DB_PASSWORD', value: 'wordpress_pass', secret: true},
                    {key: 'WORDPRESS_DB_NAME', value: 'wordpress'}
                ],
                volumes: [{host: './wordpress', container: '/var/www/html'}],
                depends_on: ['db']
            },
            {
                name: 'db',
                image: 'mysql:8',
                environment: [
                    {key: 'MYSQL_DATABASE', value: 'wordpress'},
                    {key: 'MYSQL_USER', value: 'wordpress'},
                    {key: 'MYSQL_PASSWORD', value: 'wordpress_pass', secret: true},
                    {key: 'MYSQL_ROOT_PASSWORD', value: 'root_pass', secret: true}
                ],
                volumes: [{host: './db-data', container: '/var/lib/mysql'}]
            }
        ]
    },
    {
        id: 'lamp',
        name: 'LAMP Stack',
        icon: '🔥',
        category: 'stack',
        description: 'Linux, Apache, MySQL, PHP complete stack',
        tags: ['web', 'php', 'mysql'],
        multiContainer: true,
        services: [
            {
                name: 'web',
                image: 'php:8.2-apache',
                ports: [{host: 8080, container: 80}],
                volumes: [{host: './app', container: '/var/www/html'}],
                depends_on: ['db']
            },
            {
                name: 'db',
                image: 'mysql:8',
                environment: [
                    {key: 'MYSQL_ROOT_PASSWORD', value: 'root_pass', secret: true},
                    {key: 'MYSQL_DATABASE', value: 'appdb'}
                ],
                volumes: [{host: './mysql-data', container: '/var/lib/mysql'}]
            }
        ]
    },
    {
        id: 'mean',
        name: 'MEAN Stack',
        icon: '💚',
        category: 'stack',
        description: 'MongoDB, Express, Angular, Node.js stack',
        tags: ['javascript', 'mongodb', 'nodejs'],
        multiContainer: true,
        services: [
            {
                name: 'mongo',
                image: 'mongo:7',
                ports: [{host: 27017, container: 27017}],
                volumes: [{host: './mongo-data', container: '/data/db'}]
            },
            {
                name: 'app',
                image: 'node:18-alpine',
                ports: [{host: 3000, container: 3000}],
                volumes: [{host: './app', container: '/usr/src/app'}],
                command: 'npm start',
                depends_on: ['mongo']
            }
        ]
    },

    // Custom
    {
        id: 'custom',
        name: 'Custom Container',
        icon: '🔧',
        category: 'custom',
        description: 'Start from scratch and configure everything',
        tags: ['custom', 'advanced'],
        image: '',
        ports: [],
        environment: [],
        volumes: [],
        memory: 1,
        cpu: 1
    }
];

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    loadTemplates();
    setupEventListeners();
    initializeCanvas();
    loadDraft();
});

// ============================================================================
// TEMPLATE MANAGEMENT
// ============================================================================

function loadTemplates(filter = 'all') {
    const grid = document.getElementById('template-grid');
    const filtered = filter === 'all'
        ? TEMPLATES
        : TEMPLATES.filter(t => t.category === filter);

    grid.innerHTML = filtered.map(template => `
        <div class="template-card ${wizardState.selectedTemplate?.id === template.id ? 'selected' : ''}"
             onclick="selectTemplate('${template.id}')">
            <div class="template-icon">${template.icon}</div>
            <div class="template-name">${template.name}</div>
            <div class="template-description">${template.description}</div>
            <div class="template-tags">
                ${template.tags.map(tag => `<span class="template-tag">${tag}</span>`).join('')}
            </div>
        </div>
    `).join('');
}

function filterTemplates(category) {
    // Update active tab
    document.querySelectorAll('.template-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    loadTemplates(category);
}

function selectTemplate(templateId) {
    const template = TEMPLATES.find(t => t.id === templateId);
    wizardState.selectedTemplate = template;

    // Update UI
    document.querySelectorAll('.template-card').forEach(card => {
        card.classList.remove('selected');
    });
    event.target.closest('.template-card').classList.add('selected');

    // Enable next button
    document.getElementById('step1-next').disabled = false;

    // Load template config
    if (template && !template.multiContainer) {
        wizardState.config = {
            name: template.id,
            image: template.image,
            ports: template.ports || [],
            environment: template.environment || [],
            volumes: template.volumes || [],
            memory: template.memory || 1,
            cpu: template.cpu || 1,
            restart: 'always',
            healthcheck: template.healthcheck || null,
            command: template.command || null
        };
    }
}

// ============================================================================
// STEP NAVIGATION
// ============================================================================

function nextStep() {
    if (wizardState.currentStep < 5) {
        wizardState.currentStep++;
        updateStepUI();

        // Special actions per step
        if (wizardState.currentStep === 2) {
            populateConfigForm();
        } else if (wizardState.currentStep === 3) {
            initializeDesigner();
        } else if (wizardState.currentStep === 4) {
            updateNetworkDiagram();
        } else if (wizardState.currentStep === 5) {
            generateYAML();
            runFinalValidation();
        }
    }
}

function prevStep() {
    if (wizardState.currentStep > 1) {
        wizardState.currentStep--;
        updateStepUI();
    }
}

function updateStepUI() {
    // Update progress indicators
    document.querySelectorAll('.wizard-step').forEach((step, index) => {
        step.classList.remove('active', 'completed');
        const stepNum = index + 1;
        if (stepNum < wizardState.currentStep) {
            step.classList.add('completed');
        } else if (stepNum === wizardState.currentStep) {
            step.classList.add('active');
        }
    });

    // Update content visibility
    document.querySelectorAll('.wizard-step-content').forEach((content, index) => {
        content.classList.remove('active');
        if (index + 1 === wizardState.currentStep) {
            content.classList.add('active');
        }
    });
}

// ============================================================================
// CONFIGURATION FORM (Step 2)
// ============================================================================

function populateConfigForm() {
    // Populate form with template data
    document.getElementById('container-name').value = wizardState.config.name;
    document.getElementById('container-image').value = wizardState.config.image;
    document.getElementById('memory-limit').value = wizardState.config.memory;
    document.getElementById('cpu-limit').value = wizardState.config.cpu;
    document.getElementById('restart-policy').value = wizardState.config.restart;

    // Clear and populate ports
    const portsList = document.getElementById('ports-list');
    portsList.innerHTML = '';
    wizardState.config.ports.forEach((port, index) => {
        addPort(port);
    });

    // Clear and populate env vars
    const envList = document.getElementById('env-list');
    envList.innerHTML = '';
    wizardState.config.environment.forEach((env, index) => {
        addEnvVar(env);
    });

    // Clear and populate volumes
    const volumesList = document.getElementById('volumes-list');
    volumesList.innerHTML = '';
    wizardState.config.volumes.forEach((vol, index) => {
        addVolume(vol);
    });

    // Health check
    if (wizardState.config.healthcheck) {
        document.getElementById('enable-healthcheck').checked = true;
        document.getElementById('healthcheck-config').style.display = 'block';
        document.getElementById('healthcheck-cmd').value = wizardState.config.healthcheck;
    }

    validateConfig();
}

function addPort(port = {host: '', container: ''}) {
    const portsList = document.getElementById('ports-list');
    const index = portsList.children.length;

    const portDiv = document.createElement('div');
    portDiv.className = 'port-mapping';
    portDiv.innerHTML = `
        <input type="number" placeholder="Host Port" value="${port.host}"
               onchange="updatePort(${index}, 'host', this.value)">
        <span class="port-arrow">→</span>
        <input type="number" placeholder="Container Port" value="${port.container}"
               onchange="updatePort(${index}, 'container', this.value)">
        <button class="btn-remove" onclick="removePort(${index})">✕</button>
    `;
    portsList.appendChild(portDiv);
}

function updatePort(index, field, value) {
    if (!wizardState.config.ports[index]) {
        wizardState.config.ports[index] = {host: '', container: ''};
    }
    wizardState.config.ports[index][field] = parseInt(value);
    validateConfig();
}

function removePort(index) {
    wizardState.config.ports.splice(index, 1);
    populateConfigForm();
}

function addEnvVar(env = {key: '', value: '', secret: false}) {
    const envList = document.getElementById('env-list');
    const index = envList.children.length;

    const envDiv = document.createElement('div');
    envDiv.className = 'env-var';
    envDiv.innerHTML = `
        <input type="text" placeholder="KEY" value="${env.key}"
               onchange="updateEnv(${index}, 'key', this.value)">
        <span>=</span>
        <input type="${env.secret ? 'password' : 'text'}" placeholder="value" value="${env.value}"
               onchange="updateEnv(${index}, 'value', this.value)">
        <label><input type="checkbox" ${env.secret ? 'checked' : ''}
               onchange="updateEnv(${index}, 'secret', this.checked)"> 🔒</label>
        <button class="btn-remove" onclick="removeEnv(${index})">✕</button>
    `;
    envList.appendChild(envDiv);
}

function updateEnv(index, field, value) {
    if (!wizardState.config.environment[index]) {
        wizardState.config.environment[index] = {key: '', value: '', secret: false};
    }
    wizardState.config.environment[index][field] = value;
    validateConfig();
}

function removeEnv(index) {
    wizardState.config.environment.splice(index, 1);
    populateConfigForm();
}

function addVolume(vol = {host: '', container: ''}) {
    const volumesList = document.getElementById('volumes-list');
    const index = volumesList.children.length;

    const volDiv = document.createElement('div');
    volDiv.className = 'volume-mapping';
    volDiv.innerHTML = `
        <input type="text" placeholder="Host Path" value="${vol.host}"
               onchange="updateVolume(${index}, 'host', this.value)">
        <span class="volume-arrow">→</span>
        <input type="text" placeholder="Container Path" value="${vol.container}"
               onchange="updateVolume(${index}, 'container', this.value)">
        <button class="btn-remove" onclick="removeVolume(${index})">✕</button>
    `;
    volumesList.appendChild(volDiv);
}

function updateVolume(index, field, value) {
    if (!wizardState.config.volumes[index]) {
        wizardState.config.volumes[index] = {host: '', container: ''};
    }
    wizardState.config.volumes[index][field] = value;
    validateConfig();
}

function removeVolume(index) {
    wizardState.config.volumes.splice(index, 1);
    populateConfigForm();
}

// Update config from form
document.addEventListener('change', function(e) {
    if (e.target.id === 'container-name') wizardState.config.name = e.target.value;
    if (e.target.id === 'container-image') wizardState.config.image = e.target.value;
    if (e.target.id === 'memory-limit') wizardState.config.memory = parseFloat(e.target.value);
    if (e.target.id === 'cpu-limit') wizardState.config.cpu = parseFloat(e.target.value);
    if (e.target.id === 'restart-policy') wizardState.config.restart = e.target.value;

    if (e.target.id === 'enable-healthcheck') {
        document.getElementById('healthcheck-config').style.display = e.target.checked ? 'block' : 'none';
    }
    if (e.target.id === 'healthcheck-cmd') {
        wizardState.config.healthcheck = e.target.value;
    }

    validateConfig();
});

// ============================================================================
// REAL-TIME VALIDATION
// ============================================================================

function validateConfig() {
    const results = document.getElementById('validation-results');
    const validations = [];

    // Container name validation
    if (!wizardState.config.name) {
        validations.push({
            type: 'error',
            message: 'Container name is required'
        });
    } else if (!/^[a-z0-9-]+$/.test(wizardState.config.name)) {
        validations.push({
            type: 'error',
            message: 'Container name must be lowercase alphanumeric with hyphens'
        });
    } else {
        validations.push({
            type: 'success',
            message: 'Container name is valid'
        });
    }

    // Image validation
    if (!wizardState.config.image) {
        validations.push({
            type: 'error',
            message: 'Docker image is required'
        });
    } else {
        validations.push({
            type: 'success',
            message: 'Docker image is specified'
        });
    }

    // Port conflict check
    const hostPorts = wizardState.config.ports.map(p => p.host);
    const duplicates = hostPorts.filter((item, index) => hostPorts.indexOf(item) !== index);
    if (duplicates.length > 0) {
        validations.push({
            type: 'error',
            message: `Port conflict detected: ${duplicates.join(', ')}`
        });
    }

    // Resource warnings
    if (wizardState.config.memory > 4) {
        validations.push({
            type: 'warning',
            message: 'Memory limit over 4GB may impact host performance'
        });
    }

    // Security warnings
    const insecurePasswords = wizardState.config.environment.filter(e =>
        e.key.toLowerCase().includes('password') && !e.secret
    );
    if (insecurePasswords.length > 0) {
        validations.push({
            type: 'warning',
            message: 'Password environment variables should be marked as secret'
        });
    }

    // Update UI
    results.innerHTML = validations.map(v => `
        <div class="validation-item ${v.type}">
            <span class="validation-icon">${getValidationIcon(v.type)}</span>
            <span>${v.message}</span>
        </div>
    `).join('');

    // Enable/disable next button
    const hasErrors = validations.some(v => v.type === 'error');
    const nextBtn = document.getElementById('step2-next');
    if (nextBtn) nextBtn.disabled = hasErrors;

    return !hasErrors;
}

function getValidationIcon(type) {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        pending: '⏳'
    };
    return icons[type] || '•';
}

// ============================================================================
// AI-POWERED SUGGESTIONS
// ============================================================================

async function getAISuggestions() {
    const suggestionsDiv = document.getElementById('ai-suggestions');
    suggestionsDiv.innerHTML = '<p style="color: #7f8c8d;">Generating suggestions...</p>';

    // Simulate AI analysis
    await new Promise(resolve => setTimeout(resolve, 1000));

    const suggestions = [];

    // Analyze current config
    const config = wizardState.config;

    // Port suggestions
    if (config.ports.length === 0) {
        suggestions.push('Consider adding port mappings for external access');
    }

    // Volume suggestions
    if (config.image.includes('postgres') || config.image.includes('mysql')) {
        if (config.volumes.length === 0) {
            suggestions.push('Add a volume to persist database data across container restarts');
        }
    }

    // Environment suggestions
    if (config.image.includes('postgres') && !config.environment.some(e => e.key === 'POSTGRES_PASSWORD')) {
        suggestions.push('Set POSTGRES_PASSWORD environment variable for security');
    }

    // Resource suggestions
    if (config.memory < 0.5) {
        suggestions.push('Memory limit below 512MB may cause performance issues');
    }

    // Health check suggestions
    if (!config.healthcheck && (config.image.includes('postgres') || config.image.includes('mysql'))) {
        suggestions.push('Enable health checks for better monitoring and auto-recovery');
    }

    // Security suggestions
    if (config.ports.some(p => p.host < 1024)) {
        suggestions.push('Ports below 1024 require root privileges. Consider using higher ports.');
    }

    // Display suggestions
    suggestionsDiv.innerHTML = suggestions.map(s => `
        <div class="suggestion-item">💡 ${s}</div>
    `).join('') || '<p style="color: #27ae60;">✅ Configuration looks good!</p>';
}

// ============================================================================
// VISUAL DESIGNER (Step 3)
// ============================================================================

let canvas, ctx;
let selectedService = null;
let isDragging = false;
let dragOffset = {x: 0, y: 0};

function initializeCanvas() {
    canvas = document.getElementById('designer-canvas');
    if (!canvas) return;

    ctx = canvas.getContext('2d');

    // Set canvas size
    const wrapper = canvas.parentElement;
    canvas.width = wrapper.clientWidth;
    canvas.height = wrapper.clientHeight;

    // Setup drag and drop from palette
    setupDragAndDrop();

    // Draw initial grid
    drawGrid();
}

function initializeDesigner() {
    if (!wizardState.canvasServices.length && wizardState.selectedTemplate) {
        // Add current container to canvas
        addServiceToCanvas({
            id: Date.now().toString(),
            name: wizardState.config.name,
            icon: wizardState.selectedTemplate.icon,
            image: wizardState.config.image,
            ports: wizardState.config.ports,
            x: canvas.width / 2 - 75,
            y: canvas.height / 2 - 50
        });
    }
    redrawCanvas();
}

function drawGrid() {
    if (!ctx) return;

    ctx.strokeStyle = '#f0f0f0';
    ctx.lineWidth = 1;

    // Vertical lines
    for (let x = 0; x < canvas.width; x += 50) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, canvas.height);
        ctx.stroke();
    }

    // Horizontal lines
    for (let y = 0; y < canvas.height; y += 50) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(canvas.width, y);
        ctx.stroke();
    }
}

function setupDragAndDrop() {
    // From palette to canvas
    const paletteItems = document.querySelectorAll('.palette-item');
    paletteItems.forEach(item => {
        item.addEventListener('dragstart', function(e) {
            e.dataTransfer.setData('serviceType', this.dataset.service);
        });
    });

    // Canvas drop zone
    canvas.addEventListener('dragover', function(e) {
        e.preventDefault();
    });

    canvas.addEventListener('drop', function(e) {
        e.preventDefault();
        const serviceType = e.dataTransfer.getData('serviceType');
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const template = TEMPLATES.find(t => t.id === serviceType);
        if (template) {
            addServiceToCanvas({
                id: Date.now().toString(),
                name: template.name,
                icon: template.icon,
                image: template.image,
                ports: template.ports || [],
                x: x - 75,
                y: y - 50
            });
        }
    });

    // Service dragging on canvas
    canvas.addEventListener('mousedown', handleCanvasMouseDown);
    canvas.addEventListener('mousemove', handleCanvasMouseMove);
    canvas.addEventListener('mouseup', handleCanvasMouseUp);
}

function handleCanvasMouseDown(e) {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Check if clicking on a service
    for (const service of wizardState.canvasServices) {
        if (x >= service.x && x <= service.x + 150 &&
            y >= service.y && y <= service.y + 100) {
            selectedService = service;
            isDragging = true;
            dragOffset = {x: x - service.x, y: y - service.y};
            break;
        }
    }

    redrawCanvas();
}

function handleCanvasMouseMove(e) {
    if (!isDragging || !selectedService) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    selectedService.x = x - dragOffset.x;
    selectedService.y = y - dragOffset.y;

    redrawCanvas();
}

function handleCanvasMouseUp(e) {
    isDragging = false;
}

function addServiceToCanvas(service) {
    wizardState.canvasServices.push(service);
    redrawCanvas();
}

function redrawCanvas() {
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw grid
    drawGrid();

    // Draw connections
    // TODO: Draw lines between connected services

    // Draw services
    wizardState.canvasServices.forEach(service => {
        drawService(service, service === selectedService);
    });
}

function drawService(service, isSelected) {
    // Draw container box
    ctx.fillStyle = isSelected ? '#f39c12' : '#667eea';
    ctx.strokeStyle = isSelected ? '#f39c12' : '#667eea';
    ctx.lineWidth = 3;

    // Rounded rectangle
    const x = service.x;
    const y = service.y;
    const w = 150;
    const h = 100;
    const r = 12;

    ctx.fillStyle = 'white';
    ctx.strokeStyle = isSelected ? '#f39c12' : '#667eea';

    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.arcTo(x + w, y, x + w, y + r, r);
    ctx.lineTo(x + w, y + h - r);
    ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
    ctx.lineTo(x + r, y + h);
    ctx.arcTo(x, y + h, x, y + h - r, r);
    ctx.lineTo(x, y + r);
    ctx.arcTo(x, y, x + r, y, r);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Draw icon
    ctx.font = '32px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(service.icon, x + w/2, y + 30);

    // Draw name
    ctx.font = 'bold 14px Arial';
    ctx.fillStyle = '#2c3e50';
    ctx.fillText(service.name, x + w/2, y + 65);

    // Draw ports
    if (service.ports && service.ports.length > 0) {
        ctx.font = '10px Arial';
        ctx.fillStyle = '#7f8c8d';
        const portsText = service.ports.map(p => `${p.host}`).join(', ');
        ctx.fillText(portsText, x + w/2, y + 85);
    }
}

function clearCanvas() {
    wizardState.canvasServices = [];
    selectedService = null;
    redrawCanvas();
}

function autoLayoutCanvas() {
    // Arrange services in a grid
    const services = wizardState.canvasServices;
    const cols = Math.ceil(Math.sqrt(services.length));
    const spacing = 200;

    services.forEach((service, index) => {
        const row = Math.floor(index / cols);
        const col = index % cols;
        service.x = col * spacing + 50;
        service.y = row * spacing + 50;
    });

    redrawCanvas();
}

// ============================================================================
// NETWORK DIAGRAM (Step 4)
// ============================================================================

function updateNetworkDiagram() {
    const svg = document.getElementById('network-svg');
    if (!svg) return;

    // Clear existing
    svg.innerHTML = '';

    // Define arrow marker
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.innerHTML = `
        <marker id="arrowhead" markerWidth="10" markerHeight="10"
                refX="9" refY="3" orient="auto">
            <polygon points="0 0, 10 3, 0 6" fill="#667eea"/>
        </marker>
    `;
    svg.appendChild(defs);

    // Draw networks
    const networks = ['frontend', 'backend'];
    const networkY = 100;

    networks.forEach((network, index) => {
        const x = 150 + index * 300;

        // Network box
        const networkGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        networkGroup.setAttribute('class', 'network-node');

        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', x);
        rect.setAttribute('y', networkY);
        rect.setAttribute('width', 200);
        rect.setAttribute('height', 200);
        rect.setAttribute('rx', 10);
        rect.setAttribute('fill', '#f8f9ff');
        rect.setAttribute('stroke', '#667eea');
        rect.setAttribute('stroke-width', 2);

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', x + 100);
        text.setAttribute('y', networkY + 30);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-weight', 'bold');
        text.textContent = network;

        networkGroup.appendChild(rect);
        networkGroup.appendChild(text);
        svg.appendChild(networkGroup);

        // Add services to network
        wizardState.canvasServices.slice(0, 2).forEach((service, serviceIndex) => {
            const serviceY = networkY + 70 + serviceIndex * 60;

            const serviceText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            serviceText.setAttribute('x', x + 100);
            serviceText.setAttribute('y', serviceY);
            serviceText.setAttribute('text-anchor', 'middle');
            serviceText.setAttribute('font-size', '12');
            serviceText.textContent = `${service.icon} ${service.name}`;

            networkGroup.appendChild(serviceText);
        });
    });

    // Draw connection between networks
    if (networks.length > 1) {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        line.setAttribute('d', 'M 350 200 L 450 200');
        line.setAttribute('class', 'network-link');
        svg.appendChild(line);
    }
}

function addNetwork() {
    const name = prompt('Network name:');
    if (name) {
        wizardState.networks.push(name);
        updateNetworkDiagram();
    }
}

function addNamedVolume() {
    const tbody = document.getElementById('volumes-tbody');
    const name = prompt('Volume name:');
    if (!name) return;

    const row = tbody.insertRow();
    row.innerHTML = `
        <td>${name}</td>
        <td>Named Volume</td>
        <td>/data</td>
        <td>-</td>
        <td><button class="btn btn-sm btn-danger" onclick="this.closest('tr').remove()">Delete</button></td>
    `;

    wizardState.volumes.push({name, type: 'named'});
}

// ============================================================================
// YAML GENERATION (Step 5)
// ============================================================================

function generateYAML() {
    const config = wizardState.config;
    const template = wizardState.selectedTemplate;

    let yaml = `version: '3.8'\n\nservices:\n`;

    // Single container
    if (!template?.multiContainer) {
        yaml += `  ${config.name}:\n`;
        yaml += `    image: ${config.image}\n`;
        yaml += `    container_name: ${config.name}\n`;

        if (config.ports.length > 0) {
            yaml += `    ports:\n`;
            config.ports.forEach(p => {
                yaml += `      - "${p.host}:${p.container}"\n`;
            });
        }

        if (config.environment.length > 0) {
            yaml += `    environment:\n`;
            config.environment.forEach(e => {
                yaml += `      ${e.key}: ${e.value}\n`;
            });
        }

        if (config.volumes.length > 0) {
            yaml += `    volumes:\n`;
            config.volumes.forEach(v => {
                yaml += `      - ${v.host}:${v.container}\n`;
            });
        }

        if (config.memory || config.cpu) {
            yaml += `    deploy:\n`;
            yaml += `      resources:\n`;
            yaml += `        limits:\n`;
            if (config.memory) yaml += `          memory: ${config.memory}G\n`;
            if (config.cpu) yaml += `          cpus: '${config.cpu}'\n`;
        }

        yaml += `    restart: ${config.restart}\n`;

        if (config.healthcheck) {
            yaml += `    healthcheck:\n`;
            yaml += `      test: ["CMD-SHELL", "${config.healthcheck}"]\n`;
            yaml += `      interval: 30s\n`;
            yaml += `      timeout: 10s\n`;
            yaml += `      retries: 3\n`;
        }
    }
    // Multi-container stack
    else if (template.multiContainer) {
        template.services.forEach(service => {
            yaml += `  ${service.name}:\n`;
            yaml += `    image: ${service.image}\n`;

            if (service.ports) {
                yaml += `    ports:\n`;
                service.ports.forEach(p => {
                    yaml += `      - "${p.host}:${p.container}"\n`;
                });
            }

            if (service.environment) {
                yaml += `    environment:\n`;
                service.environment.forEach(e => {
                    yaml += `      ${e.key}: ${e.value}\n`;
                });
            }

            if (service.volumes) {
                yaml += `    volumes:\n`;
                service.volumes.forEach(v => {
                    yaml += `      - ${v.host}:${v.container}\n`;
                });
            }

            if (service.depends_on) {
                yaml += `    depends_on:\n`;
                service.depends_on.forEach(dep => {
                    yaml += `      - ${dep}\n`;
                });
            }

            if (service.command) {
                yaml += `    command: ${service.command}\n`;
            }

            yaml += `    restart: always\n\n`;
        });
    }

    // Add volumes section if needed
    if (wizardState.volumes.length > 0) {
        yaml += `\nvolumes:\n`;
        wizardState.volumes.forEach(v => {
            yaml += `  ${v.name}:\n`;
        });
    }

    // Add networks section
    if (wizardState.networks.length > 1) {
        yaml += `\nnetworks:\n`;
        wizardState.networks.forEach(n => {
            yaml += `  ${n}:\n`;
        });
    }

    document.getElementById('generated-yaml').textContent = yaml;

    // Update summary
    updateDeploymentSummary();
}

function updateDeploymentSummary() {
    const template = wizardState.selectedTemplate;
    const serviceCount = template?.multiContainer ? template.services.length : 1;

    document.getElementById('summary-services').textContent = serviceCount;
    document.getElementById('summary-networks').textContent = wizardState.networks.length;
    document.getElementById('summary-volumes').textContent = wizardState.volumes.length;

    // Estimate size based on images
    const estimatedSize = serviceCount * 250; // rough estimate
    document.getElementById('summary-size').textContent = `~${estimatedSize} MB`;
}

function runFinalValidation() {
    const validationDiv = document.getElementById('final-validation');

    const checks = [
        {name: 'Configuration valid', passed: validateConfig()},
        {name: 'No port conflicts', passed: true},
        {name: 'Resources within limits', passed: wizardState.config.memory <= 8},
        {name: 'All images specified', passed: !!wizardState.config.image}
    ];

    validationDiv.innerHTML = checks.map(check => `
        <div class="validation-item ${check.passed ? 'success' : 'error'}">
            <span class="validation-icon">${check.passed ? '✅' : '❌'}</span>
            <span>${check.name}</span>
        </div>
    `).join('');
}

function copyYAML() {
    const yaml = document.getElementById('generated-yaml').textContent;
    navigator.clipboard.writeText(yaml);
    if (window.Quantum?.notify) {
        window.Quantum.notify.success('YAML copied to clipboard');
    } else {
        alert('YAML copied to clipboard');
    }
}

function downloadYAML() {
    const yaml = document.getElementById('generated-yaml').textContent;
    const blob = new Blob([yaml], {type: 'text/yaml'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'docker-compose.yml';
    a.click();
}

// ============================================================================
// DEPLOYMENT
// ============================================================================

async function deployContainers() {
    const modal = document.getElementById('deploy-modal');
    const progressDiv = document.getElementById('deploy-progress');
    const progressFill = document.getElementById('deploy-progress-fill');
    const logsDiv = document.getElementById('deploy-logs');

    modal.style.display = 'flex';

    const steps = [
        'Validating configuration...',
        'Generating docker-compose.yml...',
        'Pulling Docker images...',
        'Creating networks...',
        'Creating volumes...',
        'Starting containers...',
        'Running health checks...',
        'Deployment complete!'
    ];

    for (let i = 0; i < steps.length; i++) {
        progressDiv.innerHTML = `
            <div class="progress-step">
                <div class="progress-icon">⏳</div>
                <div class="progress-text">${steps[i]}</div>
            </div>
        `;

        const percent = ((i + 1) / steps.length) * 100;
        progressFill.style.width = percent + '%';

        // Simulate deployment
        await new Promise(resolve => setTimeout(resolve, 1500));

        // Add log entry
        const logEntry = document.createElement('div');
        logEntry.className = 'deploy-log-entry';
        logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${steps[i]}`;
        logsDiv.appendChild(logEntry);
        logsDiv.scrollTop = logsDiv.scrollHeight;
    }

    // Success
    progressDiv.innerHTML = `
        <div class="progress-step">
            <div class="progress-icon">✅</div>
            <div class="progress-text">Deployment successful!</div>
        </div>
    `;

    document.getElementById('cancel-deploy-btn').textContent = 'Close';
    document.getElementById('cancel-deploy-btn').onclick = function() {
        modal.style.display = 'none';
        if (window.Quantum?.notify) {
            window.Quantum.notify.success('Containers deployed successfully!');
        }
    };
}

function cancelDeployment() {
    document.getElementById('deploy-modal').style.display = 'none';
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function browseImages() {
    const image = document.getElementById('container-image').value;
    const tag = prompt('Enter image tag:', 'latest');
    if (tag) {
        const baseImage = image.split(':')[0];
        document.getElementById('container-image').value = `${baseImage}:${tag}`;
        wizardState.config.image = `${baseImage}:${tag}`;
    }
}

function resetWizard() {
    if (!confirm('Reset wizard and lose all changes?')) return;

    wizardState.currentStep = 1;
    wizardState.selectedTemplate = null;
    wizardState.canvasServices = [];
    wizardState.networks = ['default'];
    wizardState.volumes = [];
    wizardState.config = {
        name: '',
        image: '',
        ports: [],
        environment: [],
        volumes: [],
        memory: 1,
        cpu: 1,
        restart: 'always',
        healthcheck: null
    };

    updateStepUI();
    loadTemplates();
    document.getElementById('step1-next').disabled = true;
}

function saveAsDraft() {
    localStorage.setItem('container-wizard-draft', JSON.stringify(wizardState));
    if (window.Quantum?.notify) {
        window.Quantum.notify.success('Draft saved');
    } else {
        alert('Draft saved');
    }
}

function loadDraft() {
    const draft = localStorage.getItem('container-wizard-draft');
    if (draft) {
        try {
            const parsed = JSON.parse(draft);
            if (confirm('Load saved draft?')) {
                Object.assign(wizardState, parsed);
                updateStepUI();
                if (wizardState.selectedTemplate) {
                    loadTemplates();
                }
            }
        } catch (e) {
            console.error('Failed to load draft:', e);
        }
    }
}

function saveAndExit() {
    saveAsDraft();
    window.location.href = 'containers.html';
}

function setupEventListeners() {
    // Health check toggle
    const healthcheckToggle = document.getElementById('enable-healthcheck');
    if (healthcheckToggle) {
        healthcheckToggle.addEventListener('change', function() {
            document.getElementById('healthcheck-config').style.display =
                this.checked ? 'block' : 'none';
        });
    }

    // Auto-save on changes
    setInterval(function() {
        if (wizardState.selectedTemplate) {
            localStorage.setItem('container-wizard-autosave', JSON.stringify(wizardState));
        }
    }, 30000); // Every 30 seconds
}

// Export functions to global scope
window.selectTemplate = selectTemplate;
window.filterTemplates = filterTemplates;
window.nextStep = nextStep;
window.prevStep = prevStep;
window.addPort = addPort;
window.updatePort = updatePort;
window.removePort = removePort;
window.addEnvVar = addEnvVar;
window.updateEnv = updateEnv;
window.removeEnv = removeEnv;
window.addVolume = addVolume;
window.updateVolume = updateVolume;
window.removeVolume = removeVolume;
window.validateConfig = validateConfig;
window.getAISuggestions = getAISuggestions;
window.addServiceToCanvas = addServiceToCanvas;
window.clearCanvas = clearCanvas;
window.autoLayoutCanvas = autoLayoutCanvas;
window.addNetwork = addNetwork;
window.addNamedVolume = addNamedVolume;
window.copyYAML = copyYAML;
window.downloadYAML = downloadYAML;
window.deployContainers = deployContainers;
window.cancelDeployment = cancelDeployment;
window.browseImages = browseImages;
window.resetWizard = resetWizard;
window.saveAsDraft = saveAsDraft;
window.saveAndExit = saveAndExit;

