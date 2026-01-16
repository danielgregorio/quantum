/**
 * Quantum Admin - Global Utilities & Enhancements
 * Dark Mode, Command Palette, Keyboard Shortcuts, Notifications
 */

// =====================
// THEME MANAGEMENT (DARK MODE)
// =====================

const ThemeManager = {
    current: localStorage.getItem('quantum-theme') || 'light',

    init() {
        this.apply(this.current);
        this.addToggleButton();
    },

    toggle() {
        this.current = this.current === 'light' ? 'dark' : 'light';
        this.apply(this.current);
        localStorage.setItem('quantum-theme', this.current);
    },

    apply(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.current = theme;
    },

    addToggleButton() {
        const header = document.querySelector('.header-actions');
        if (!header) return;

        const btn = document.createElement('button');
        btn.className = 'btn theme-toggle';
        btn.innerHTML = this.current === 'dark' ? '☀️' : '🌙';
        btn.onclick = () => {
            this.toggle();
            btn.innerHTML = this.current === 'dark' ? '☀️' : '🌙';
        };
        btn.title = 'Toggle Dark Mode';
        header.insertBefore(btn, header.firstChild);
    }
};

// =====================
// COMMAND PALETTE
// =====================

const CommandPalette = {
    isOpen: false,
    commands: [
        // Navigation
        { name: 'Dashboard', action: () => window.location.href = 'index.html', icon: '📊', category: 'Navigation' },
        { name: 'Monitoring', action: () => window.location.href = 'monitoring.html', icon: '📈', category: 'Navigation' },
        { name: 'Datasources', action: () => window.location.href = 'datasources.html', icon: '🗄️', category: 'Navigation' },
        { name: 'Containers', action: () => window.location.href = 'containers.html', icon: '🐳', category: 'Navigation' },
        { name: 'Components', action: () => window.location.href = 'components.html', icon: '📦', category: 'Navigation' },
        { name: 'API Explorer', action: () => window.location.href = 'api-explorer.html', icon: '🔌', category: 'Navigation' },
        { name: 'Logs', action: () => window.location.href = 'logs.html', icon: '📝', category: 'Navigation' },
        { name: 'Settings', action: () => window.location.href = 'settings.html', icon: '⚙️', category: 'Navigation' },
        { name: 'Security', action: () => window.location.href = 'security.html', icon: '🔒', category: 'Navigation' },

        // Actions
        { name: 'Toggle Dark Mode', action: () => ThemeManager.toggle(), icon: '🌙', category: 'Actions' },
        { name: 'Refresh Page', action: () => window.location.reload(), icon: '🔄', category: 'Actions' },
        { name: 'Open AI Assistant', action: () => AIAssistant.toggle(), icon: '🤖', category: 'Actions' },
        { name: 'New Datasource', action: () => window.location.href = 'datasources.html#new', icon: '➕', category: 'Actions' },
        { name: 'New User', action: () => window.location.href = 'security.html#new-user', icon: '👤', category: 'Actions' },
    ],

    init() {
        this.createModal();
        this.attachKeyboardShortcut();
    },

    createModal() {
        const modal = document.createElement('div');
        modal.id = 'command-palette';
        modal.className = 'command-palette-modal';
        modal.style.display = 'none';
        modal.innerHTML = `
            <div class="command-palette-backdrop" onclick="CommandPalette.close()"></div>
            <div class="command-palette-content">
                <div class="command-palette-search">
                    <span class="search-icon">🔍</span>
                    <input type="text" id="command-search" placeholder="Type a command or search..." autocomplete="off">
                    <kbd>ESC</kbd>
                </div>
                <div class="command-palette-results" id="command-results"></div>
                <div class="command-palette-footer">
                    <span>Navigate: <kbd>↑</kbd> <kbd>↓</kbd></span>
                    <span>Select: <kbd>Enter</kbd></span>
                    <span>Close: <kbd>ESC</kbd></span>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // Search input handler
        const searchInput = modal.querySelector('#command-search');
        searchInput.addEventListener('input', (e) => this.search(e.target.value));

        // Keyboard navigation
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.close();
            } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigate(e.key === 'ArrowDown' ? 1 : -1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                this.executeSelected();
            }
        });
    },

    attachKeyboardShortcut() {
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.toggle();
            }
        });
    },

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    },

    open() {
        const modal = document.getElementById('command-palette');
        modal.style.display = 'flex';
        this.isOpen = true;

        // Focus search
        setTimeout(() => {
            document.getElementById('command-search').focus();
            this.search(''); // Show all commands
        }, 50);
    },

    close() {
        const modal = document.getElementById('command-palette');
        modal.style.display = 'none';
        this.isOpen = false;
        document.getElementById('command-search').value = '';
    },

    search(query) {
        const results = document.getElementById('command-results');
        const filtered = this.fuzzySearch(query);

        if (filtered.length === 0) {
            results.innerHTML = '<div class="no-results">No commands found</div>';
            return;
        }

        // Group by category
        const grouped = {};
        filtered.forEach(cmd => {
            if (!grouped[cmd.category]) grouped[cmd.category] = [];
            grouped[cmd.category].push(cmd);
        });

        results.innerHTML = Object.keys(grouped).map(category => `
            <div class="command-category">
                <div class="category-name">${category}</div>
                ${grouped[category].map((cmd, idx) => `
                    <div class="command-item" data-index="${idx}" onclick="CommandPalette.execute(${this.commands.indexOf(cmd)})">
                        <span class="command-icon">${cmd.icon}</span>
                        <span class="command-name">${cmd.name}</span>
                    </div>
                `).join('')}
            </div>
        `).join('');

        // Select first item
        const firstItem = results.querySelector('.command-item');
        if (firstItem) firstItem.classList.add('selected');
    },

    fuzzySearch(query) {
        if (!query) return this.commands;

        query = query.toLowerCase();
        return this.commands.filter(cmd =>
            cmd.name.toLowerCase().includes(query) ||
            cmd.category.toLowerCase().includes(query)
        );
    },

    navigate(direction) {
        const items = Array.from(document.querySelectorAll('.command-item'));
        const selected = document.querySelector('.command-item.selected');
        const currentIndex = items.indexOf(selected);
        const newIndex = Math.max(0, Math.min(items.length - 1, currentIndex + direction));

        if (selected) selected.classList.remove('selected');
        items[newIndex].classList.add('selected');

        // Scroll into view
        items[newIndex].scrollIntoView({ block: 'nearest' });
    },

    executeSelected() {
        const selected = document.querySelector('.command-item.selected');
        if (selected) selected.click();
    },

    execute(index) {
        const command = this.commands[index];
        if (command && command.action) {
            command.action();
            this.close();
        }
    }
};

// =====================
// NOTIFICATION SYSTEM
// =====================

const NotificationSystem = {
    container: null,

    init() {
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
    },

    show(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;

        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };

        notification.innerHTML = `
            <span class="notification-icon">${icons[type]}</span>
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.remove()">×</button>
        `;

        this.container.appendChild(notification);

        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);

        // Auto-remove
        if (duration > 0) {
            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => notification.remove(), 300);
            }, duration);
        }

        return notification;
    },

    success(message, duration) { return this.show(message, 'success', duration); },
    error(message, duration) { return this.show(message, 'error', duration); },
    warning(message, duration) { return this.show(message, 'warning', duration); },
    info(message, duration) { return this.show(message, 'info', duration); }
};

// =====================
// AI ASSISTANT
// =====================

const AIAssistant = {
    isOpen: false,

    init() {
        this.createPanel();
        this.addToggleButton();
    },

    createPanel() {
        const panel = document.createElement('div');
        panel.id = 'ai-assistant';
        panel.className = 'ai-assistant-panel';
        panel.style.display = 'none';
        panel.innerHTML = `
            <div class="ai-header">
                <div>
                    <span class="ai-icon">🤖</span>
                    <strong>Quantum AI Assistant</strong>
                    <span class="ai-badge">Beta</span>
                </div>
                <button class="ai-close" onclick="AIAssistant.close()">×</button>
            </div>
            <div class="ai-chat" id="ai-chat">
                <div class="ai-message ai-assistant">
                    <strong>AI:</strong> Hi! I'm your Quantum AI Assistant. I can help you with:
                    <ul>
                        <li>Creating Quantum components</li>
                        <li>Understanding databinding syntax</li>
                        <li>Debugging errors</li>
                        <li>Best practices</li>
                    </ul>
                    Ask me anything!
                </div>
            </div>
            <div class="ai-input-container">
                <textarea id="ai-input" placeholder="Ask me anything about Quantum..." rows="3"></textarea>
                <button class="btn btn-primary" onclick="AIAssistant.send()">Send</button>
            </div>
        `;
        document.body.appendChild(panel);

        // Enter to send
        document.getElementById('ai-input').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.send();
            }
        });
    },

    addToggleButton() {
        const btn = document.createElement('button');
        btn.className = 'ai-fab';
        btn.innerHTML = '🤖';
        btn.title = 'Open AI Assistant (Ctrl+Shift+A)';
        btn.onclick = () => this.toggle();
        document.body.appendChild(btn);

        // Keyboard shortcut
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'A') {
                e.preventDefault();
                this.toggle();
            }
        });
    },

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    },

    open() {
        document.getElementById('ai-assistant').style.display = 'flex';
        this.isOpen = true;
        document.getElementById('ai-input').focus();
    },

    close() {
        document.getElementById('ai-assistant').style.display = 'none';
        this.isOpen = false;
    },

    async send() {
        const input = document.getElementById('ai-input');
        const message = input.value.trim();

        if (!message) return;

        // Add user message
        this.addMessage(message, 'user');
        input.value = '';

        // Show typing indicator
        const typingId = this.addTypingIndicator();

        try {
            // Call AI endpoint
            const response = await fetch('http://localhost:8000/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, context: 'quantum' })
            });

            const data = await response.json();

            // Remove typing indicator
            document.getElementById(typingId)?.remove();

            // Add AI response
            this.addMessage(data.response || 'Sorry, I encountered an error.', 'assistant');

        } catch (error) {
            document.getElementById(typingId)?.remove();
            this.addMessage('AI service is not available. Make sure the backend is running.', 'assistant');
        }
    },

    addMessage(text, role) {
        const chat = document.getElementById('ai-chat');
        const msg = document.createElement('div');
        msg.className = `ai-message ai-${role}`;
        msg.innerHTML = `<strong>${role === 'user' ? 'You' : 'AI'}:</strong> ${this.formatMessage(text)}`;
        chat.appendChild(msg);
        chat.scrollTop = chat.scrollHeight;
    },

    addTypingIndicator() {
        const chat = document.getElementById('ai-chat');
        const id = 'typing-' + Date.now();
        const indicator = document.createElement('div');
        indicator.id = id;
        indicator.className = 'ai-message ai-assistant typing';
        indicator.innerHTML = '<strong>AI:</strong> <span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
        chat.appendChild(indicator);
        chat.scrollTop = chat.scrollHeight;
        return id;
    },

    formatMessage(text) {
        // Convert markdown-style code blocks
        text = text.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
        text = text.replace(/\n/g, '<br>');
        return text;
    }
};

// =====================
// KEYBOARD SHORTCUTS
// =====================

const KeyboardShortcuts = {
    shortcuts: {
        'ctrl+k': () => CommandPalette.toggle(),
        'ctrl+shift+a': () => AIAssistant.toggle(),
        'ctrl+b': () => document.querySelector('.sidebar')?.classList.toggle('collapsed'),
        'ctrl+/': () => document.getElementById('search-components')?.focus() || document.getElementById('search-logs')?.focus(),
        'escape': () => {
            if (CommandPalette.isOpen) CommandPalette.close();
            if (AIAssistant.isOpen) AIAssistant.close();
        }
    },

    init() {
        document.addEventListener('keydown', (e) => {
            const key = this.getKeyCombo(e);
            if (this.shortcuts[key]) {
                e.preventDefault();
                this.shortcuts[key]();
            }
        });
    },

    getKeyCombo(e) {
        const parts = [];
        if (e.ctrlKey || e.metaKey) parts.push('ctrl');
        if (e.shiftKey) parts.push('shift');
        if (e.altKey) parts.push('alt');
        parts.push(e.key.toLowerCase());
        return parts.join('+');
    }
};

// =====================
// INITIALIZATION
// =====================

document.addEventListener('DOMContentLoaded', function() {
    ThemeManager.init();
    CommandPalette.init();
    NotificationSystem.init();
    AIAssistant.init();
    KeyboardShortcuts.init();

    console.log('🚀 Quantum Admin Enhanced Features Loaded!');
    console.log('📋 Press Ctrl+K for Command Palette');
    console.log('🤖 Press Ctrl+Shift+A for AI Assistant');
});

// Export for use in other scripts
window.Quantum = {
    theme: ThemeManager,
    command: CommandPalette,
    notify: NotificationSystem,
    ai: AIAssistant,
    shortcuts: KeyboardShortcuts
};
