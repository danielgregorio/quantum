/**
 * Quantum Admin - AI Assistant Interface
 * Handles AI chat interactions with SLM and RAG
 */

const API_BASE = 'http://localhost:8000';

let conversationHistory = [];
let isAIOnline = false;

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    checkAIStatus();
    loadFunctions();
    setupInputHandlers();

    // Auto-resize textarea
    const textarea = document.getElementById('ai-input');
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Handle Enter key
    textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
});

// ============================================================================
// AI Status Check
// ============================================================================

async function checkAIStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            setAIStatus(true);
        } else {
            setAIStatus(false);
        }
    } catch (error) {
        console.error('AI status check failed:', error);
        setAIStatus(false);
    }
}

function setAIStatus(online) {
    isAIOnline = online;
    const statusEl = document.getElementById('ai-status');
    const indicator = statusEl.querySelector('.status-indicator');

    if (online) {
        statusEl.className = 'ai-status online';
        statusEl.innerHTML = '<span class="status-indicator online"></span>AI Online';
    } else {
        statusEl.className = 'ai-status offline';
        statusEl.innerHTML = '<span class="status-indicator offline"></span>AI Offline (Fallback)';
    }
}

// ============================================================================
// Load Available Functions
// ============================================================================

async function loadFunctions() {
    try {
        const response = await fetch(`${API_BASE}/ai/functions`);
        const data = await response.json();

        const functionsHtml = data.functions.map(func => `
            <div class="function-item">
                <div class="function-name">${func.name}</div>
                <div class="function-desc">${func.description}</div>
            </div>
        `).join('');

        document.getElementById('functions-list').innerHTML = functionsHtml || '<p>No functions available</p>';
    } catch (error) {
        console.error('Error loading functions:', error);
        document.getElementById('functions-list').innerHTML = '<p>Failed to load functions</p>';
    }
}

// ============================================================================
// Send Message
// ============================================================================

async function sendMessage() {
    const input = document.getElementById('ai-input');
    const message = input.value.trim();

    if (!message) return;

    // Clear input
    input.value = '';
    input.style.height = 'auto';

    // Hide empty state
    document.getElementById('empty-state').style.display = 'none';

    // Add user message
    addMessage('user', message);

    // Show typing indicator
    showTypingIndicator();

    // Get options
    const useSlm = document.getElementById('use-slm').checked;
    const includeSchema = document.getElementById('include-schema').checked;

    try {
        const response = await fetch(`${API_BASE}/ai/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                use_slm: useSlm,
                include_schema: includeSchema
            })
        });

        const data = await response.json();

        // Hide typing indicator
        hideTypingIndicator();

        // Add assistant message
        addMessage('assistant', data.response, {
            function_called: data.function_called,
            tokens: data.tokens_used,
            provider: data.provider
        });

        // Update conversation history
        conversationHistory.push({
            role: 'user',
            content: message
        }, {
            role: 'assistant',
            content: data.response
        });

    } catch (error) {
        hideTypingIndicator();
        addMessage('assistant', '❌ Error: Failed to get response from AI. Please try again.', {
            error: true
        });
        console.error('Error sending message:', error);
    }
}

// ============================================================================
// Add Message to Chat
// ============================================================================

function addMessage(role, content, meta = {}) {
    const messagesContainer = document.getElementById('ai-messages');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    // Format content (convert markdown-like syntax)
    let formattedContent = content
        .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');

    messageDiv.innerHTML = `
        <div class="message-content">${formattedContent}</div>
        ${meta.function_called || meta.provider ? `
            <div class="message-meta">
                ${meta.function_called ? `<span class="function-call-badge">🔧 ${meta.function_called}</span>` : ''}
                ${meta.provider ? `<span>${meta.provider}</span>` : ''}
                ${meta.tokens ? `<span>${meta.tokens} tokens</span>` : ''}
            </div>
        ` : ''}
    `;

    messagesContainer.appendChild(messageDiv);

    // Scroll to bottom
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ============================================================================
// Typing Indicator
// ============================================================================

function showTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    indicator.classList.add('active');

    const messagesContainer = document.getElementById('ai-messages');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    indicator.classList.remove('active');
}

// ============================================================================
// Quick Prompts
// ============================================================================

function usePrompt(prompt) {
    const input = document.getElementById('ai-input');
    input.value = prompt;
    input.focus();
    input.style.height = 'auto';
    input.style.height = (input.scrollHeight) + 'px';
}

// ============================================================================
// Clear Conversation
// ============================================================================

async function clearConversation() {
    if (!confirm('Clear entire conversation?')) return;

    try {
        await fetch(`${API_BASE}/ai/clear`, {
            method: 'POST'
        });

        conversationHistory = [];

        const messagesContainer = document.getElementById('ai-messages');
        messagesContainer.innerHTML = `
            <div class="empty-state" id="empty-state">
                <div class="empty-state-icon">🤖</div>
                <div class="empty-state-title">Quantum AI Assistant</div>
                <div class="empty-state-text">Ask me anything about databases, migrations, containers, and more!</div>
            </div>
            <div class="typing-indicator" id="typing-indicator">
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;

        showToast('Conversation cleared', 'success');
    } catch (error) {
        console.error('Error clearing conversation:', error);
        showToast('Failed to clear conversation', 'error');
    }
}

// ============================================================================
// Show Functions Modal
// ============================================================================

async function showFunctions() {
    try {
        const response = await fetch(`${API_BASE}/ai/functions`);
        const data = await response.json();

        let functionsHtml = '<h2>Available AI Functions</h2><div style="display: grid; gap: 16px; margin-top: 20px;">';

        for (const func of data.functions) {
            functionsHtml += `
                <div style="padding: 16px; background: #f8f9fa; border-radius: 8px;">
                    <h3 style="margin-top: 0; color: #667eea;">${func.name}</h3>
                    <p style="color: #7f8c8d; margin-bottom: 12px;">${func.description}</p>
                    ${func.parameters ? `
                        <div style="font-size: 12px; font-family: monospace; background: #2d2d2d; color: #f8f8f2; padding: 12px; border-radius: 4px;">
                            ${JSON.stringify(func.parameters, null, 2)}
                        </div>
                    ` : ''}
                </div>
            `;
        }

        functionsHtml += '</div>';

        showModal('AI Functions', functionsHtml);
    } catch (error) {
        console.error('Error loading functions:', error);
        showToast('Failed to load functions', 'error');
    }
}

// ============================================================================
// Helper Functions
// ============================================================================

function showModal(title, content) {
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    // Create modal
    const modal = document.createElement('div');
    modal.style.cssText = `
        background: white;
        border-radius: 12px;
        padding: 24px;
        max-width: 800px;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    `;

    modal.innerHTML = `
        ${content}
        <button onclick="this.closest('[style*=\"position: fixed\"]').remove()"
                style="margin-top: 20px; padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
            Close
        </button>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Close on overlay click
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#667eea'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        z-index: 10001;
        animation: slideInRight 0.3s ease;
    `;
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function setupInputHandlers() {
    // Add styles for animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

// ============================================================================
// Export for testing
// ============================================================================

window.QuantumAI = {
    sendMessage,
    clearConversation,
    usePrompt,
    showFunctions,
    checkAIStatus
};
