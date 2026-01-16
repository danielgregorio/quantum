/**
 * Template Gallery - Ready-to-use Quantum components
 */

// Template database
const TEMPLATES = [
    // Authentication Templates
    {
        id: 'login-form',
        name: 'Login Form',
        category: 'auth',
        description: 'Beautiful login form with validation',
        preview: '🔐',
        code: `<?xml version="1.0"?>
<component name="login">
    <div class="login-container">
        <div class="login-box">
            <h1>Welcome Back</h1>
            <p>Sign in to your account</p>

            <form action="/auth/login" method="POST" class="login-form">
                <div class="form-group">
                    <label>Email</label>
                    <input type="email" name="email" placeholder="you@example.com" required />
                </div>

                <div class="form-group">
                    <label>Password</label>
                    <input type="password" name="password" placeholder="••••••••" required />
                </div>

                <if condition="{error}">
                    <div class="error-message">{error}</div>
                </if>

                <button type="submit" class="btn-primary">Sign In</button>

                <div class="forgot-password">
                    <a href="/auth/forgot">Forgot password?</a>
                </div>
            </form>
        </div>
    </div>

    <style>
        .login-container { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .login-box { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); max-width: 400px; width: 100%; }
        .login-form { margin-top: 30px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 8px; font-weight: 500; }
        .form-group input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        .btn-primary { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer; }
        .btn-primary:hover { background: #5568d3; }
        .error-message { padding: 12px; background: #fee; color: #c00; border-radius: 4px; margin-bottom: 15px; }
        .forgot-password { text-align: center; margin-top: 15px; }
    </style>
</component>`
    },

    {
        id: 'register-form',
        name: 'Registration Form',
        category: 'auth',
        description: 'User registration with validation',
        preview: '📝',
        code: `<?xml version="1.0"?>
<component name="register">
    <div class="register-container">
        <h1>Create Account</h1>
        <form action="/auth/register" method="POST">
            <input type="text" name="name" placeholder="Full Name" required />
            <input type="email" name="email" placeholder="Email" required />
            <input type="password" name="password" placeholder="Password" required />
            <button type="submit">Sign Up</button>
        </form>
    </div>
</component>`
    },

    // CRUD Templates
    {
        id: 'user-list',
        name: 'User List (CRUD)',
        category: 'crud',
        description: 'Complete user management with CRUD operations',
        preview: '👥',
        code: `<?xml version="1.0"?>
<component name="user-list">
    <div class="crud-container">
        <div class="crud-header">
            <h1>User Management</h1>
            <button onclick="createUser()" class="btn-primary">+ New User</button>
        </div>

        <table class="crud-table">
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                <loop array="users">
                    <tr>
                        <td>{item.name}</td>
                        <td>{item.email}</td>
                        <td><span class="badge">{item.role}</span></td>
                        <td>
                            <button onclick="editUser({item.id})">Edit</button>
                            <button onclick="deleteUser({item.id})">Delete</button>
                        </td>
                    </tr>
                </loop>
            </tbody>
        </table>
    </div>

    <style>
        .crud-container { padding: 20px; }
        .crud-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .crud-table { width: 100%; border-collapse: collapse; }
        .crud-table th, .crud-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        .badge { padding: 4px 12px; background: #e3f2fd; border-radius: 12px; font-size: 12px; }
    </style>
</component>`
    },

    // Dashboard Templates
    {
        id: 'stats-dashboard',
        name: 'Stats Dashboard',
        category: 'dashboard',
        description: 'Dashboard with stats cards and charts',
        preview: '📊',
        code: `<?xml version="1.0"?>
<component name="dashboard">
    <div class="dashboard">
        <h1>Dashboard</h1>

        <div class="stats-grid">
            <loop array="stats">
                <div class="stat-card">
                    <div class="stat-icon">{item.icon}</div>
                    <div class="stat-content">
                        <h3>{item.value}</h3>
                        <p>{item.label}</p>
                    </div>
                </div>
            </loop>
        </div>

        <div class="charts-grid">
            <div class="chart-card">
                <h2>Revenue</h2>
                <div class="chart-placeholder">📈 Chart goes here</div>
            </div>

            <div class="chart-card">
                <h2>Users</h2>
                <div class="chart-placeholder">📊 Chart goes here</div>
            </div>
        </div>
    </div>

    <style>
        .dashboard { padding: 20px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: flex; align-items: center; }
        .stat-icon { font-size: 40px; margin-right: 20px; }
        .stat-content h3 { margin: 0; font-size: 32px; }
        .stat-content p { margin: 5px 0 0; color: #666; }
        .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .chart-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .chart-placeholder { height: 200px; background: #f5f5f5; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
    </style>
</component>`
    },

    // Form Templates
    {
        id: 'contact-form',
        name: 'Contact Form',
        category: 'form',
        description: 'Contact form with validation',
        preview: '📬',
        code: `<?xml version="1.0"?>
<component name="contact">
    <div class="contact-form">
        <h1>Get in Touch</h1>
        <p>We'd love to hear from you</p>

        <form action="/contact" method="POST">
            <div class="form-row">
                <input type="text" name="name" placeholder="Your Name" required />
                <input type="email" name="email" placeholder="Your Email" required />
            </div>

            <input type="text" name="subject" placeholder="Subject" required />

            <textarea name="message" rows="5" placeholder="Your Message" required></textarea>

            <button type="submit" class="btn-submit">Send Message</button>
        </form>
    </div>

    <style>
        .contact-form { max-width: 600px; margin: 50px auto; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        input, textarea { width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 6px; }
        .btn-submit { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; }
    </style>
</component>`
    },

    // UI Components
    {
        id: 'card-grid',
        name: 'Card Grid',
        category: 'ui',
        description: 'Responsive card grid layout',
        preview: '🎴',
        code: `<?xml version="1.0"?>
<component name="card-grid">
    <div class="card-grid">
        <loop array="items">
            <div class="card">
                <img src="{item.image}" alt="{item.title}" />
                <div class="card-content">
                    <h3>{item.title}</h3>
                    <p>{item.description}</p>
                    <button>Learn More</button>
                </div>
            </div>
        </loop>
    </div>

    <style>
        .card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; padding: 20px; }
        .card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s; }
        .card:hover { transform: translateY(-4px); box-shadow: 0 4px 16px rgba(0,0,0,0.15); }
        .card img { width: 100%; height: 200px; object-fit: cover; }
        .card-content { padding: 20px; }
        .card button { width: 100%; padding: 10px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; }
    </style>
</component>`
    }
];

// Global state
let currentTemplate = null;
let filteredTemplates = TEMPLATES;

// Initialize
window.addEventListener('DOMContentLoaded', function() {
    renderTemplates();

    // Search
    document.getElementById('search-templates').addEventListener('input', function(e) {
        searchTemplates(e.target.value);
    });
});

// Render templates grid
function renderTemplates() {
    const grid = document.getElementById('templates-grid');
    grid.innerHTML = '';

    filteredTemplates.forEach(template => {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cursor = 'pointer';
        card.onclick = () => showTemplatePreview(template);

        card.innerHTML = `
            <div style="padding: 20px;">
                <div style="font-size: 48px; text-align: center; margin-bottom: 15px;">${template.preview}</div>
                <h3 style="margin: 0 0 10px 0; color: var(--text-primary);">${template.name}</h3>
                <p style="color: var(--text-secondary); margin: 0 0 15px 0; font-size: 14px;">${template.description}</p>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="badge info">${template.category}</span>
                    <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); openTemplateInPlayground('${template.id}')">Open</button>
                </div>
            </div>
        `;

        grid.appendChild(card);
    });
}

// Filter by category
function filterByCategory(category) {
    // Update active button
    document.querySelectorAll('.category-filter').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    // Filter templates
    if (category === 'all') {
        filteredTemplates = TEMPLATES;
    } else {
        filteredTemplates = TEMPLATES.filter(t => t.category === category);
    }

    renderTemplates();
}

// Search templates
function searchTemplates(query) {
    if (!query) {
        filteredTemplates = TEMPLATES;
    } else {
        query = query.toLowerCase();
        filteredTemplates = TEMPLATES.filter(t =>
            t.name.toLowerCase().includes(query) ||
            t.description.toLowerCase().includes(query) ||
            t.category.toLowerCase().includes(query)
        );
    }

    renderTemplates();
}

// Show template preview
function showTemplatePreview(template) {
    currentTemplate = template;

    document.getElementById('modal-title').textContent = template.name;
    document.getElementById('modal-description').textContent = template.description;
    document.getElementById('modal-code').textContent = template.code;

    document.getElementById('template-modal').style.display = 'flex';
}

// Close modal
function closeTemplateModal() {
    document.getElementById('template-modal').style.display = 'none';
    currentTemplate = null;
}

// Copy template code
function copyTemplateCode() {
    if (!currentTemplate) return;

    navigator.clipboard.writeText(currentTemplate.code);
    Quantum.notify.success('Template code copied to clipboard!');
}

// Open in playground
function openInPlayground() {
    if (!currentTemplate) return;

    // Store template in sessionStorage
    sessionStorage.setItem('playground-template', JSON.stringify(currentTemplate));

    // Navigate to playground
    window.location.href = 'playground.html?template=true';
}

// Open template in playground directly
function openTemplateInPlayground(templateId) {
    const template = TEMPLATES.find(t => t.id === templateId);
    if (!template) return;

    sessionStorage.setItem('playground-template', JSON.stringify(template));
    window.location.href = 'playground.html?template=true';
}

// Install template
async function installTemplate() {
    if (!currentTemplate) return;

    const filename = prompt('Enter filename:', `${currentTemplate.id}.q`);
    if (!filename) return;

    try {
        const response = await fetch('http://localhost:8000/components/install', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: filename,
                code: currentTemplate.code
            })
        });

        if (response.ok) {
            Quantum.notify.success(`Template installed as ${filename}!`);
            closeTemplateModal();
        } else {
            Quantum.notify.error('Failed to install template');
        }
    } catch (error) {
        Quantum.notify.error('Installation failed');
    }
}

// Close modal on backdrop click
document.getElementById('template-modal')?.addEventListener('click', function(e) {
    if (e.target === this) {
        closeTemplateModal();
    }
});
