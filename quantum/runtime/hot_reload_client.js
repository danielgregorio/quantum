/**
 * Quantum Hot Reload Client
 *
 * Browser-side script that connects to the hot reload WebSocket server
 * and handles live reloading of pages during development.
 *
 * Features:
 * - WebSocket connection with auto-reconnect
 * - Full page reload on structure changes
 * - CSS-only reload for style changes
 * - State preservation across reloads (forms, scroll position)
 * - Error overlay for parse errors
 * - Toast notifications for reload events
 */

(function() {
    'use strict';

    // Configuration - these can be overridden before script loads
    var config = window.__QUANTUM_HOT_RELOAD_CONFIG || {};
    var WS_HOST = config.host || 'localhost';
    var WS_PORT = config.port || 35729;
    var WS_URL = 'ws://' + WS_HOST + ':' + WS_PORT;
    var RECONNECT_INTERVAL = config.reconnectInterval || 1000;
    var MAX_RECONNECT_ATTEMPTS = config.maxReconnectAttempts || 30;
    var ENABLE_LOGGING = config.enableLogging !== false;
    var ENABLE_TOASTS = config.enableToasts !== false;
    var ENABLE_STATE_PRESERVATION = config.preserveState !== false;

    // Internal state
    var socket = null;
    var reconnectAttempts = 0;
    var overlay = null;
    var isConnected = false;
    var lastReloadTime = 0;

    // State preservation storage
    var preservedState = {};

    /**
     * Log message to console
     */
    function log(msg, level) {
        if (!ENABLE_LOGGING) return;
        level = level || 'log';
        console[level]('[Quantum Hot Reload] ' + msg);
    }

    /**
     * Connect to WebSocket server
     */
    function connect() {
        if (socket && socket.readyState === WebSocket.OPEN) {
            return;
        }

        try {
            socket = new WebSocket(WS_URL);

            socket.onopen = function() {
                log('Connected to development server');
                reconnectAttempts = 0;
                isConnected = true;
                hideOverlay();
                showToast('Hot reload connected', 'success');
            };

            socket.onclose = function() {
                var wasConnected = isConnected;
                isConnected = false;

                if (wasConnected) {
                    log('Disconnected from development server');
                    showToast('Hot reload disconnected', 'warning');
                }

                scheduleReconnect();
            };

            socket.onerror = function(err) {
                log('WebSocket error', 'error');
            };

            socket.onmessage = function(event) {
                try {
                    var data = JSON.parse(event.data);
                    handleMessage(data);
                } catch (e) {
                    log('Error parsing message: ' + e, 'error');
                }
            };

        } catch (e) {
            log('Failed to connect: ' + e, 'error');
            scheduleReconnect();
        }
    }

    /**
     * Schedule reconnection attempt
     */
    function scheduleReconnect() {
        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            log('Max reconnect attempts reached', 'warn');
            showOverlay({
                type: 'connection_lost',
                message: 'Lost connection to development server.\nPlease restart the server with: quantum dev'
            });
            return;
        }

        reconnectAttempts++;
        var delay = RECONNECT_INTERVAL * Math.min(reconnectAttempts, 5);

        setTimeout(connect, delay);
    }

    /**
     * Handle incoming WebSocket message
     */
    function handleMessage(data) {
        switch (data.type) {
            case 'connected':
                log('Server acknowledged connection');
                break;

            case 'reload':
                handleReload(data);
                break;

            case 'error':
                handleError(data.error);
                break;

            case 'clear_error':
                hideOverlay();
                showToast('Error cleared', 'success');
                break;

            case 'pong':
                // Heartbeat response - connection alive
                break;

            default:
                log('Unknown message type: ' + data.type, 'warn');
        }
    }

    /**
     * Handle reload event
     */
    function handleReload(data) {
        // Debounce rapid reloads
        var now = Date.now();
        if (now - lastReloadTime < 500) {
            log('Debouncing rapid reload');
            return;
        }
        lastReloadTime = now;

        var reloadType = data.reloadType || 'full';
        var fileCount = (data.files || []).length;

        log('Reload triggered: ' + reloadType + ' (' + fileCount + ' files changed)');

        if (reloadType === 'css') {
            reloadCSS(data.files);
            showToast('Styles updated', 'info');
        } else {
            // Full page reload
            if (ENABLE_STATE_PRESERVATION) {
                preserveState();
            }

            showToast('Reloading page...', 'info');

            // Small delay to show toast
            setTimeout(function() {
                location.reload();
            }, 150);
        }
    }

    /**
     * Handle error event (e.g., parse error)
     */
    function handleError(error) {
        log('Error received: ' + error.message, 'error');
        showOverlay(error);
    }

    /**
     * Reload CSS stylesheets without full page reload
     */
    function reloadCSS(changedFiles) {
        var links = document.querySelectorAll('link[rel="stylesheet"]');
        var timestamp = Date.now();

        // Build list of changed CSS files
        var changedPaths = (changedFiles || [])
            .filter(function(f) { return f.extension === '.css'; })
            .map(function(f) { return f.path.replace(/\\/g, '/'); });

        links.forEach(function(link) {
            var href = link.href.split('?')[0];

            // If specific files provided, only reload matching ones
            if (changedPaths.length > 0) {
                var shouldReload = changedPaths.some(function(path) {
                    return href.indexOf(path) !== -1 || href.indexOf(path.split('/').pop()) !== -1;
                });

                if (!shouldReload) return;
            }

            // Force reload by adding timestamp query param
            link.href = href + '?_hr=' + timestamp;
        });

        // Also reload any inline styles from external files that might have been extracted
        var style = document.createElement('style');
        style.textContent = '/* Hot reload trigger: ' + timestamp + ' */';
        document.head.appendChild(style);
        setTimeout(function() {
            if (style.parentNode) {
                style.parentNode.removeChild(style);
            }
        }, 100);

        log('CSS reloaded');
    }

    /**
     * Preserve state before full page reload
     */
    function preserveState() {
        preservedState = {};

        // Save form values
        var forms = document.querySelectorAll('form');
        forms.forEach(function(form, i) {
            var formId = form.id || ('__hr_form_' + i);
            preservedState[formId] = {};

            var inputs = form.querySelectorAll('input, textarea, select');
            inputs.forEach(function(input) {
                if (!input.name && !input.id) return;

                var key = input.name || input.id;

                if (input.type === 'checkbox') {
                    preservedState[formId][key] = input.checked;
                } else if (input.type === 'radio') {
                    if (input.checked) {
                        preservedState[formId][key] = input.value;
                    }
                } else if (input.type !== 'password' && input.type !== 'file') {
                    preservedState[formId][key] = input.value;
                }
            });
        });

        // Save scroll position
        preservedState.__scroll = {
            x: window.scrollX || window.pageXOffset,
            y: window.scrollY || window.pageYOffset
        };

        // Save active element (focus)
        if (document.activeElement && document.activeElement.id) {
            preservedState.__focus = document.activeElement.id;
        }

        // Save tab states
        var activeTabs = document.querySelectorAll('.q-tab-header.active');
        preservedState.__tabs = [];
        activeTabs.forEach(function(tab) {
            if (tab.dataset.tab) {
                preservedState.__tabs.push(tab.dataset.tab);
            }
        });

        // Store in sessionStorage
        try {
            sessionStorage.setItem('__quantum_hr_state', JSON.stringify(preservedState));
            log('State preserved');
        } catch (e) {
            log('Failed to preserve state: ' + e, 'warn');
        }
    }

    /**
     * Restore state after page reload
     */
    function restoreState() {
        if (!ENABLE_STATE_PRESERVATION) return;

        try {
            var saved = sessionStorage.getItem('__quantum_hr_state');
            if (!saved) return;

            var state = JSON.parse(saved);
            sessionStorage.removeItem('__quantum_hr_state');

            // Restore form values
            Object.keys(state).forEach(function(formId) {
                if (formId.startsWith('__')) return;

                var form = document.getElementById(formId);
                if (!form && formId.startsWith('__hr_form_')) {
                    var index = parseInt(formId.replace('__hr_form_', ''), 10);
                    form = document.forms[index];
                }
                if (!form) return;

                var formState = state[formId];
                Object.keys(formState).forEach(function(key) {
                    var input = form.querySelector('[name="' + key + '"]') ||
                                form.querySelector('#' + key);

                    if (!input) return;

                    if (input.type === 'checkbox') {
                        input.checked = formState[key];
                    } else if (input.type === 'radio') {
                        var radios = form.querySelectorAll('[name="' + key + '"]');
                        radios.forEach(function(radio) {
                            radio.checked = radio.value === formState[key];
                        });
                    } else {
                        input.value = formState[key];
                    }
                });
            });

            // Restore scroll position
            if (state.__scroll) {
                setTimeout(function() {
                    window.scrollTo(state.__scroll.x, state.__scroll.y);
                }, 100);
            }

            // Restore focus
            if (state.__focus) {
                setTimeout(function() {
                    var el = document.getElementById(state.__focus);
                    if (el && el.focus) {
                        el.focus();
                    }
                }, 150);
            }

            // Restore tabs
            if (state.__tabs && state.__tabs.length > 0) {
                state.__tabs.forEach(function(tabId) {
                    var tab = document.querySelector('[data-tab="' + tabId + '"]');
                    if (tab) {
                        tab.click();
                    }
                });
            }

            log('State restored');

        } catch (e) {
            log('Error restoring state: ' + e, 'warn');
        }
    }

    /**
     * Show error overlay
     */
    function showOverlay(error) {
        hideOverlay();

        overlay = document.createElement('div');
        overlay.id = '__quantum_hr_overlay';
        overlay.style.cssText = [
            'position: fixed',
            'top: 0',
            'left: 0',
            'right: 0',
            'bottom: 0',
            'background: rgba(0, 0, 0, 0.92)',
            'z-index: 999999',
            'display: flex',
            'align-items: center',
            'justify-content: center',
            'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            'padding: 20px',
            'box-sizing: border-box'
        ].join(';');

        var content = document.createElement('div');
        content.style.cssText = [
            'max-width: 800px',
            'width: 100%',
            'max-height: 90vh',
            'overflow: auto',
            'padding: 32px',
            'background: #1a1a1a',
            'border-radius: 12px',
            'color: #fff',
            'box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5)'
        ].join(';');

        var isConnectionError = error.type === 'connection_lost';
        var titleColor = isConnectionError ? '#ffc107' : '#ef4444';
        var icon = isConnectionError ? '&#x26A0;' : '&#x2717;';
        var title = isConnectionError ? 'Connection Lost' : 'Parse Error';

        var html = [
            '<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">',
            '  <span style="font-size:32px;color:' + titleColor + ';">' + icon + '</span>',
            '  <h2 style="margin:0;font-size:24px;font-weight:600;color:' + titleColor + ';">' + title + '</h2>',
            '</div>'
        ];

        if (error.file) {
            var fileName = error.file.split(/[/\\]/).pop();
            html.push('<p style="color:#888;margin:0 0 16px 0;font-size:14px;">');
            html.push('  <span style="color:#666;">File:</span> <code style="background:#2a2a2a;padding:2px 6px;border-radius:3px;">' + escapeHtml(fileName) + '</code>');
            if (error.line) {
                html.push(' <span style="color:#666;">Line:</span> ' + error.line);
            }
            html.push('</p>');
        }

        html.push('<pre style="background:#0d0d0d;padding:20px;border-radius:8px;overflow-x:auto;margin:0;font-size:14px;line-height:1.6;color:#ff6b6b;white-space:pre-wrap;word-break:break-word;border:1px solid #333;">');
        html.push(escapeHtml(error.message));
        html.push('</pre>');

        html.push('<div style="margin-top:20px;padding-top:16px;border-top:1px solid #333;">');
        html.push('  <p style="color:#888;margin:0;font-size:13px;">');
        if (isConnectionError) {
            html.push('    Restart the development server with <code style="background:#2a2a2a;padding:2px 6px;border-radius:3px;">quantum dev</code>');
        } else {
            html.push('    Fix the error and save the file to reload automatically.');
        }
        html.push('  </p>');
        html.push('</div>');

        content.innerHTML = html.join('\n');
        overlay.appendChild(content);
        document.body.appendChild(overlay);

        // ESC key to dismiss
        overlay._escHandler = function(e) {
            if (e.key === 'Escape') {
                hideOverlay();
            }
        };
        document.addEventListener('keydown', overlay._escHandler);

        // Click outside to dismiss
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) {
                hideOverlay();
            }
        });
    }

    /**
     * Hide error overlay
     */
    function hideOverlay() {
        if (overlay) {
            if (overlay._escHandler) {
                document.removeEventListener('keydown', overlay._escHandler);
            }
            if (overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
            overlay = null;
        }
    }

    /**
     * Show toast notification
     */
    function showToast(message, type) {
        if (!ENABLE_TOASTS) return;

        // Remove existing toast
        var existing = document.getElementById('__quantum_hr_toast');
        if (existing && existing.parentNode) {
            existing.parentNode.removeChild(existing);
        }

        var toast = document.createElement('div');
        toast.id = '__quantum_hr_toast';

        var colors = {
            success: '#22c55e',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };

        toast.style.cssText = [
            'position: fixed',
            'bottom: 20px',
            'right: 20px',
            'padding: 12px 20px',
            'background: ' + (colors[type] || colors.info),
            'color: #fff',
            'border-radius: 6px',
            'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            'font-size: 14px',
            'font-weight: 500',
            'z-index: 999998',
            'box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2)',
            'transform: translateY(0)',
            'opacity: 1',
            'transition: transform 0.3s ease, opacity 0.3s ease'
        ].join(';');

        toast.textContent = message;
        document.body.appendChild(toast);

        // Animate in
        toast.style.transform = 'translateY(20px)';
        toast.style.opacity = '0';
        setTimeout(function() {
            toast.style.transform = 'translateY(0)';
            toast.style.opacity = '1';
        }, 10);

        // Auto-hide after delay
        setTimeout(function() {
            if (toast.parentNode) {
                toast.style.transform = 'translateY(20px)';
                toast.style.opacity = '0';
                setTimeout(function() {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, 300);
            }
        }, 2500);
    }

    /**
     * Escape HTML special characters
     */
    function escapeHtml(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Send heartbeat ping to keep connection alive
     */
    function sendHeartbeat() {
        if (socket && socket.readyState === WebSocket.OPEN) {
            try {
                socket.send(JSON.stringify({ type: 'ping' }));
            } catch (e) {
                // Connection might be closing
            }
        }
    }

    // Start heartbeat interval
    setInterval(sendHeartbeat, 30000);

    /**
     * Initialize hot reload client
     */
    function init() {
        // Restore state from previous reload
        restoreState();

        // Connect to WebSocket server
        connect();

        log('Initialized');
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose API for debugging
    window.__quantumHotReload = {
        connect: connect,
        disconnect: function() {
            if (socket) {
                socket.close();
            }
        },
        forceReload: function() {
            location.reload();
        },
        reloadCSS: reloadCSS,
        showToast: showToast,
        isConnected: function() { return isConnected; },
        config: config
    };

})();
