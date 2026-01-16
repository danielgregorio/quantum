/**
 * Quantum Admin - Login Page
 * Handles JWT authentication
 */

const API_BASE = 'http://localhost:8000';

// ============================================================================
// Authentication
// ============================================================================

async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const rememberMe = document.getElementById('remember-me').checked;

    // Show loading state
    const loginBtn = document.getElementById('login-btn');
    const originalText = loginBtn.textContent;
    loginBtn.disabled = true;
    loginBtn.innerHTML = '<span class="loading-spinner"></span> Signing in...';

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Store tokens
            if (rememberMe) {
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                localStorage.setItem('user', JSON.stringify(data.user));
            } else {
                sessionStorage.setItem('access_token', data.access_token);
                sessionStorage.setItem('refresh_token', data.refresh_token);
                sessionStorage.setItem('user', JSON.stringify(data.user));
            }

            // Show success message
            showAlert('Login successful! Redirecting...', 'success');

            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 1000);

        } else {
            // Show error message
            showAlert(data.detail || 'Login failed. Please check your credentials.', 'error');
            loginBtn.disabled = false;
            loginBtn.textContent = originalText;
        }

    } catch (error) {
        console.error('Login error:', error);
        showAlert('Network error. Please check your connection and try again.', 'error');
        loginBtn.disabled = false;
        loginBtn.textContent = originalText;
    }
}

// ============================================================================
// UI Helpers
// ============================================================================

function showAlert(message, type = 'error') {
    const alertContainer = document.getElementById('alert-container');
    const alertClass = type === 'success' ? 'alert-success' : 'alert-error';

    alertContainer.innerHTML = `
        <div class="alert ${alertClass}">
            ${message}
        </div>
    `;

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertContainer.innerHTML = '';
    }, 5000);
}

// ============================================================================
// Check if already logged in
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');

    if (token) {
        // Already logged in, verify token
        verifyToken(token).then(valid => {
            if (valid) {
                window.location.href = 'index.html';
            }
        });
    }
});

async function verifyToken(token) {
    try {
        const response = await fetch(`${API_BASE}/auth/verify`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        return response.ok;
    } catch (error) {
        return false;
    }
}

// ============================================================================
// Handle Enter key
// ============================================================================

document.getElementById('username').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        document.getElementById('password').focus();
    }
});
