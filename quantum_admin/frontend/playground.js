/**
 * Component Playground - Live preview and testing
 */

let autoRefreshTimer = null;

// Initialize playground
window.addEventListener('DOMContentLoaded', function() {
    const editor = document.getElementById('code-editor');
    const contextEditor = document.getElementById('context-editor');
    const autoRefresh = document.getElementById('auto-refresh');

    // Auto-refresh on edit
    if (autoRefresh && autoRefresh.checked) {
        editor.addEventListener('input', debounce(renderPreview, 1000));
        contextEditor.addEventListener('input', debounce(renderPreview, 1000));
    }

    autoRefresh?.addEventListener('change', function() {
        if (this.checked) {
            editor.addEventListener('input', debounce(renderPreview, 1000));
            contextEditor.addEventListener('input', debounce(renderPreview, 1000));
        } else {
            editor.removeEventListener('input', renderPreview);
            contextEditor.removeEventListener('input', renderPreview);
        }
    });

    // Initial render
    renderPreview();

    // Keyboard shortcuts
    editor.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            renderPreview();
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            renderPreview();
        }
    });
});

// Render preview
async function renderPreview() {
    const code = document.getElementById('code-editor').value;
    const contextText = document.getElementById('context-editor').value;
    const frame = document.getElementById('preview-frame');
    const renderTime = document.getElementById('render-time');

    try {
        // Parse context
        const context = JSON.parse(contextText);

        // Send to backend for rendering
        const startTime = performance.now();

        const response = await fetch('http://localhost:8000/playground/render', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                context: context
            })
        });

        const endTime = performance.now();
        const duration = (endTime - startTime).toFixed(0);

        if (response.ok) {
            const data = await response.json();

            // Update iframe
            frame.srcdoc = data.html;

            // Update render time
            renderTime.textContent = `Rendered in ${duration}ms`;
            renderTime.style.color = 'var(--text-secondary)';
        } else {
            const error = await response.json();
            showError(frame, error.detail || 'Render error');
            renderTime.textContent = `Error after ${duration}ms`;
            renderTime.style.color = '#dc3545';
        }
    } catch (error) {
        console.error('Render error:', error);
        showError(frame, error.message);
    }
}

// Show error in iframe
function showError(frame, message) {
    frame.srcdoc = `
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    padding: 20px;
                    background: #fee;
                    color: #c00;
                }
                h2 { margin-top: 0; }
                pre {
                    background: white;
                    padding: 15px;
                    border-radius: 4px;
                    overflow-x: auto;
                }
            </style>
        </head>
        <body>
            <h2>❌ Render Error</h2>
            <pre>${escapeHtml(message)}</pre>
        </body>
        </html>
    `;
}

// Format code
function formatCode() {
    const editor = document.getElementById('code-editor');
    let code = editor.value;

    // Simple XML formatting (indent)
    try {
        code = code.replace(/></g, '>\n<');
        editor.value = code;
        Quantum.notify.success('Code formatted');
    } catch (error) {
        Quantum.notify.error('Format failed');
    }
}

// Copy code
function copyCode() {
    const editor = document.getElementById('code-editor');
    editor.select();
    document.execCommand('copy');
    Quantum.notify.success('Code copied to clipboard');
}

// Refresh preview
function refreshPreview() {
    renderPreview();
}

// Open in new tab
function openInNewTab() {
    const frame = document.getElementById('preview-frame');
    const html = frame.srcdoc;

    const newWindow = window.open();
    newWindow.document.write(html);
    newWindow.document.close();
}

// Load template
function loadTemplate() {
    window.location.href = 'templates.html';
}

// Share playground
async function sharePlayground() {
    const code = document.getElementById('code-editor').value;
    const context = document.getElementById('context-editor').value;

    try {
        const response = await fetch('http://localhost:8000/playground/share', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ code, context })
        });

        const data = await response.json();
        const shareUrl = `${window.location.origin}/playground.html?share=${data.id}`;

        // Copy to clipboard
        navigator.clipboard.writeText(shareUrl);
        Quantum.notify.success('Share link copied to clipboard!');
    } catch (error) {
        Quantum.notify.error('Failed to generate share link');
    }
}

// Load shared playground
async function loadShared() {
    const urlParams = new URLSearchParams(window.location.search);
    const shareId = urlParams.get('share');

    if (shareId) {
        try {
            const response = await fetch(`http://localhost:8000/playground/shared/${shareId}`);
            const data = await response.json();

            document.getElementById('code-editor').value = data.code;
            document.getElementById('context-editor').value = data.context;

            renderPreview();
            Quantum.notify.info('Loaded shared playground');
        } catch (error) {
            Quantum.notify.error('Failed to load shared playground');
        }
    }
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Check for shared playground on load
loadShared();
