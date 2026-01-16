// API Base URL
const API_URL = 'http://localhost:8000';

// Default settings
const DEFAULT_SETTINGS = {
    // Server
    admin_port: 8000,
    quantum_port: 8080,
    server_host: 'localhost',
    base_url: 'http://localhost:8000',
    worker_threads: 4,
    request_timeout: 30,

    // Authentication
    auth_mode: 'local',
    session_timeout: 60,
    max_login_attempts: 5,
    require_https: false,
    enable_2fa: false,
    default_role: 'viewer',
    password_min_length: 8,
    password_require_special: true,

    // Database
    postgres_port: 5432,
    mysql_port: 3306,
    mongodb_port: 27017,
    redis_port: 6379,
    db_connection_timeout: 10,
    db_max_pool_size: 10,
    default_username: 'quantum',
    enable_query_cache: true,
    auto_start_containers: true,
    auto_pull_images: true,
    container_restart_policy: 'unless-stopped',

    // Email
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    from_email: 'noreply@quantum.dev',
    from_name: 'Quantum Framework',
    smtp_use_tls: true,
    smtp_use_ssl: false,

    // Development
    debug_mode: true,
    hot_reload: true,
    log_level: 'INFO',
    refresh_interval: 30,
    enable_source_maps: true,

    // Security
    enable_cors: true,
    allowed_origins: 'http://localhost:3000\nhttp://localhost:8080',
    require_api_key: false,
    api_key_header: 'X-API-Key',
    enable_rate_limiting: true,
    rate_limit_requests: 100,
    rate_limit_window: 60,

    // Storage
    upload_directory: '/var/quantum/uploads',
    max_file_size: 10,
    allowed_extensions: 'jpg, png, gif, pdf, doc, docx, txt, csv, xlsx',
    scan_uploads: true,
    auto_cleanup: false,
    cleanup_age: 30
};

// Current active tab
let currentTab = 'server';

// Load settings on page load
window.addEventListener('DOMContentLoaded', function() {
    loadSettings();
});

// =====================
// TAB SWITCHING
// =====================

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update sections
    document.querySelectorAll('.settings-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(`${tabName}-section`).classList.add('active');

    currentTab = tabName;
}

// =====================
// SETTINGS MANAGEMENT
// =====================

async function loadSettings() {
    try {
        // Try to load from backend first
        const response = await fetch(`${API_URL}/settings`);

        if (response.ok) {
            const settings = await response.json();
            applySettings(settings);
            console.log('Settings loaded from server');
        } else {
            // Fall back to localStorage
            loadFromLocalStorage();
        }
    } catch (error) {
        // Backend not available, use localStorage
        console.log('Loading settings from localStorage');
        loadFromLocalStorage();
    }
}

function loadFromLocalStorage() {
    const savedSettings = localStorage.getItem('quantum_settings');

    if (savedSettings) {
        try {
            const settings = JSON.parse(savedSettings);
            applySettings(settings);
        } catch (error) {
            console.error('Error parsing saved settings:', error);
            applySettings(DEFAULT_SETTINGS);
        }
    } else {
        applySettings(DEFAULT_SETTINGS);
    }
}

function applySettings(settings) {
    // Apply all settings to form fields
    Object.keys(settings).forEach(key => {
        const element = document.getElementById(key);

        if (element) {
            if (element.type === 'checkbox') {
                element.checked = settings[key];
            } else {
                element.value = settings[key];
            }
        }
    });
}

function gatherSettings() {
    const settings = {};

    // Gather all settings from form fields
    Object.keys(DEFAULT_SETTINGS).forEach(key => {
        const element = document.getElementById(key);

        if (element) {
            if (element.type === 'checkbox') {
                settings[key] = element.checked;
            } else if (element.type === 'number') {
                settings[key] = parseInt(element.value) || DEFAULT_SETTINGS[key];
            } else {
                settings[key] = element.value;
            }
        }
    });

    return settings;
}

async function saveAllSettings() {
    const settings = gatherSettings();

    try {
        // Try to save to backend
        const response = await fetch(`${API_URL}/settings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });

        if (response.ok) {
            showSuccess('Settings saved successfully to server!');
        } else {
            throw new Error('Backend save failed');
        }
    } catch (error) {
        // Fall back to localStorage
        console.log('Saving to localStorage');
        localStorage.setItem('quantum_settings', JSON.stringify(settings));
        showSuccess('Settings saved locally!');
    }

    // Show warning if critical settings changed
    if (settings.admin_port !== DEFAULT_SETTINGS.admin_port ||
        settings.quantum_port !== DEFAULT_SETTINGS.quantum_port) {
        showWarning('Port changes require server restart to take effect.');
    }
}

function resetToDefaults() {
    if (!confirm('Are you sure you want to reset all settings to defaults?\n\nThis will discard all your custom configuration.')) {
        return;
    }

    applySettings(DEFAULT_SETTINGS);
    showSuccess('Settings reset to defaults. Click "Save All Settings" to apply.');
}

// =====================
// EMAIL TESTING
// =====================

async function testEmailConnection() {
    const settings = gatherSettings();

    const emailConfig = {
        smtp_host: settings.smtp_host,
        smtp_port: settings.smtp_port,
        smtp_username: settings.smtp_username,
        smtp_password: settings.smtp_password,
        smtp_use_tls: settings.smtp_use_tls,
        smtp_use_ssl: settings.smtp_use_ssl
    };

    // Validate required fields
    if (!emailConfig.smtp_host || !emailConfig.smtp_username) {
        showError('Please fill in SMTP host and username before testing.');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/settings/test-email`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(emailConfig)
        });

        const result = await response.json();

        if (result.success) {
            showSuccess('✅ Email connection successful! Test email sent.');
        } else {
            showError('❌ Email connection failed: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error testing email:', error);
        showWarning('⚠️ Could not test email connection. Backend endpoint may not be available.');
    }
}

// =====================
// EXPORT / IMPORT
// =====================

function exportSettings() {
    const settings = gatherSettings();
    const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `quantum-settings-${new Date().toISOString().split('T')[0]}.json`;
    a.click();

    URL.revokeObjectURL(url);
    showSuccess('Settings exported successfully!');
}

function importSettings() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';

    input.onchange = function(e) {
        const file = e.target.files[0];
        const reader = new FileReader();

        reader.onload = function(event) {
            try {
                const settings = JSON.parse(event.target.result);
                applySettings(settings);
                showSuccess('Settings imported successfully! Click "Save All Settings" to apply.');
            } catch (error) {
                showError('Invalid settings file: ' + error.message);
            }
        };

        reader.readAsText(file);
    };

    input.click();
}

// =====================
// NOTIFICATION FUNCTIONS
// =====================

function showSuccess(message) {
    alert('✅ ' + message);
}

function showError(message) {
    alert('❌ ' + message);
}

function showWarning(message) {
    alert('⚠️ ' + message);
}

// =====================
// KEYBOARD SHORTCUTS
// =====================

document.addEventListener('keydown', function(e) {
    // Ctrl+S or Cmd+S to save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveAllSettings();
    }
});

// =====================
// UNSAVED CHANGES WARNING
// =====================

let originalSettings = null;

window.addEventListener('DOMContentLoaded', function() {
    // Store original settings after loading
    setTimeout(() => {
        originalSettings = JSON.stringify(gatherSettings());
    }, 1000);
});

window.addEventListener('beforeunload', function(e) {
    const currentSettings = JSON.stringify(gatherSettings());

    if (currentSettings !== originalSettings) {
        e.preventDefault();
        e.returnValue = '';
        return 'You have unsaved changes. Are you sure you want to leave?';
    }
});
