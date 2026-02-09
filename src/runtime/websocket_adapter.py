"""
WebSocket HTML Adapter - Client-side Code Generation

Generates JavaScript code for WebSocket connections in HTML target.

Features:
- Connection management with auto-reconnect
- Event handler binding
- Message queue buffering
- Heartbeat/ping support
- State synchronization

Usage:
    from runtime.websocket_adapter import WebSocketHTMLAdapter

    adapter = WebSocketHTMLAdapter()
    js_code = adapter.generate(websocket_node, context)
"""

import json
from typing import Dict, Any, List
from dataclasses import dataclass

from core.features.websocket.src import WebSocketNode, WebSocketHandlerNode


@dataclass
class WebSocketClientConfig:
    """Configuration for client-side WebSocket."""
    name: str
    url: str
    auto_connect: bool = True
    reconnect: bool = True
    reconnect_delay: int = 1000
    max_reconnects: int = 10
    heartbeat: int = 30000
    protocols: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "autoConnect": self.auto_connect,
            "reconnect": self.reconnect,
            "reconnectDelay": self.reconnect_delay,
            "maxReconnects": self.max_reconnects,
            "heartbeat": self.heartbeat,
            "protocols": self.protocols or []
        }


class WebSocketHTMLAdapter:
    """
    Generates client-side JavaScript for WebSocket connections.

    The generated code:
    1. Creates WebSocket connection pool
    2. Handles connect/disconnect/reconnect
    3. Dispatches messages to handlers
    4. Provides send API
    5. Manages connection state
    """

    # Client-side WebSocket manager script
    WEBSOCKET_MANAGER_SCRIPT = '''
<!-- Quantum WebSocket Manager -->
<script>
(function() {
    'use strict';

    // WebSocket connection pool
    window.__qWebSockets = window.__qWebSockets || {};

    // WebSocket state constants
    const WS_CONNECTING = 0;
    const WS_OPEN = 1;
    const WS_CLOSING = 2;
    const WS_CLOSED = 3;

    /**
     * Quantum WebSocket Connection Manager
     */
    class QuantumWebSocket {
        constructor(config) {
            this.name = config.name;
            this.url = config.url;
            this.autoConnect = config.autoConnect !== false;
            this.reconnect = config.reconnect !== false;
            this.reconnectDelay = config.reconnectDelay || 1000;
            this.maxReconnects = config.maxReconnects || 10;
            this.heartbeatInterval = config.heartbeat || 30000;
            this.protocols = config.protocols || [];

            this.ws = null;
            this.reconnectAttempts = 0;
            this.reconnectTimer = null;
            this.heartbeatTimer = null;
            this.messageQueue = [];
            this.handlers = {
                connect: [],
                open: [],
                message: [],
                error: [],
                close: []
            };

            // State object exposed to Quantum
            this.state = {
                connected: false,
                readyState: WS_CLOSED,
                url: this.url,
                lastMessage: null,
                error: null,
                messageCount: 0,
                connectedAt: null
            };

            // Auto-connect if configured
            if (this.autoConnect) {
                this.connect();
            }
        }

        connect() {
            if (this.ws && (this.ws.readyState === WS_CONNECTING || this.ws.readyState === WS_OPEN)) {
                console.log(`[QWS:${this.name}] Already connected or connecting`);
                return;
            }

            try {
                console.log(`[QWS:${this.name}] Connecting to ${this.url}`);
                this.state.readyState = WS_CONNECTING;
                this.state.error = null;

                this.ws = this.protocols.length > 0
                    ? new WebSocket(this.url, this.protocols)
                    : new WebSocket(this.url);

                this.ws.onopen = (event) => this._onOpen(event);
                this.ws.onmessage = (event) => this._onMessage(event);
                this.ws.onerror = (event) => this._onError(event);
                this.ws.onclose = (event) => this._onClose(event);

            } catch (error) {
                console.error(`[QWS:${this.name}] Connection error:`, error);
                this.state.error = error.message;
                this._dispatch('error', { error: error.message });
            }
        }

        disconnect(code = 1000, reason = '') {
            this.reconnect = false; // Disable auto-reconnect
            if (this.ws) {
                this.ws.close(code, reason);
            }
            this._stopHeartbeat();
            this._stopReconnect();
        }

        send(data, type = 'text') {
            if (!this.ws || this.ws.readyState !== WS_OPEN) {
                console.warn(`[QWS:${this.name}] Cannot send - not connected`);
                this.messageQueue.push({ data, type });
                return false;
            }

            try {
                let payload = data;
                if (type === 'json' && typeof data !== 'string') {
                    payload = JSON.stringify(data);
                }
                this.ws.send(payload);
                console.log(`[QWS:${this.name}] Sent:`, payload.substring ? payload.substring(0, 100) : payload);
                return true;
            } catch (error) {
                console.error(`[QWS:${this.name}] Send error:`, error);
                return false;
            }
        }

        on(event, handler) {
            if (this.handlers[event]) {
                this.handlers[event].push(handler);
            }
        }

        off(event, handler) {
            if (this.handlers[event]) {
                this.handlers[event] = this.handlers[event].filter(h => h !== handler);
            }
        }

        _onOpen(event) {
            console.log(`[QWS:${this.name}] Connected`);
            this.state.connected = true;
            this.state.readyState = WS_OPEN;
            this.state.connectedAt = new Date().toISOString();
            this.state.error = null;
            this.reconnectAttempts = 0;

            // Start heartbeat
            this._startHeartbeat();

            // Flush message queue
            this._flushQueue();

            // Dispatch event
            this._dispatch('connect', {});
            this._dispatch('open', {});

            // Update Quantum state
            this._updateQuantumState();
        }

        _onMessage(event) {
            let data = event.data;

            // Try to parse as JSON
            try {
                data = JSON.parse(event.data);
            } catch (e) {
                // Keep as string
            }

            this.state.lastMessage = data;
            this.state.messageCount++;

            console.log(`[QWS:${this.name}] Message #${this.state.messageCount}:`,
                typeof data === 'string' ? data.substring(0, 100) : data);

            this._dispatch('message', { data, raw: event.data, timestamp: new Date().toISOString() });
            this._updateQuantumState();
        }

        _onError(event) {
            console.error(`[QWS:${this.name}] Error:`, event);
            this.state.error = 'WebSocket error occurred';
            this._dispatch('error', { error: this.state.error, event });
            this._updateQuantumState();
        }

        _onClose(event) {
            console.log(`[QWS:${this.name}] Closed (code: ${event.code}, reason: ${event.reason})`);
            this.state.connected = false;
            this.state.readyState = WS_CLOSED;

            this._stopHeartbeat();

            this._dispatch('close', {
                code: event.code,
                reason: event.reason,
                wasClean: event.wasClean
            });

            this._updateQuantumState();

            // Auto-reconnect
            if (this.reconnect && this.reconnectAttempts < this.maxReconnects) {
                this._scheduleReconnect();
            }
        }

        _dispatch(event, data) {
            const handlers = this.handlers[event] || [];
            for (const handler of handlers) {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`[QWS:${this.name}] Handler error for ${event}:`, error);
                }
            }
        }

        _startHeartbeat() {
            if (this.heartbeatInterval <= 0) return;

            this._stopHeartbeat();
            this.heartbeatTimer = setInterval(() => {
                if (this.ws && this.ws.readyState === WS_OPEN) {
                    // Send ping (some servers expect this format)
                    try {
                        this.ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
                    } catch (e) {
                        // Ignore ping errors
                    }
                }
            }, this.heartbeatInterval);
        }

        _stopHeartbeat() {
            if (this.heartbeatTimer) {
                clearInterval(this.heartbeatTimer);
                this.heartbeatTimer = null;
            }
        }

        _scheduleReconnect() {
            this._stopReconnect();

            const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts);
            const maxDelay = 30000; // Max 30 seconds
            const actualDelay = Math.min(delay, maxDelay);

            console.log(`[QWS:${this.name}] Reconnecting in ${actualDelay}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnects})`);

            this.reconnectTimer = setTimeout(() => {
                this.reconnectAttempts++;
                this.connect();
            }, actualDelay);
        }

        _stopReconnect() {
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
        }

        _flushQueue() {
            while (this.messageQueue.length > 0) {
                const { data, type } = this.messageQueue.shift();
                this.send(data, type);
            }
        }

        _updateQuantumState() {
            // Update global Quantum state if available
            if (window.__qContext && window.__qContext[this.name] !== undefined) {
                window.__qContext[this.name] = { ...this.state };
            }
        }
    }

    // Factory function
    window.__qCreateWebSocket = function(config) {
        const ws = new QuantumWebSocket(config);
        window.__qWebSockets[config.name] = ws;
        return ws;
    };

    // Get WebSocket by name
    window.__qGetWebSocket = function(name) {
        return window.__qWebSockets[name];
    };

    // Send message helper
    window.__qWebSocketSend = function(name, data, type) {
        const ws = window.__qWebSockets[name];
        if (ws) {
            return ws.send(data, type || 'text');
        }
        console.error(`[QWS] WebSocket not found: ${name}`);
        return false;
    };

    // Close connection helper
    window.__qWebSocketClose = function(name, code, reason) {
        const ws = window.__qWebSockets[name];
        if (ws) {
            ws.disconnect(code || 1000, reason || '');
        }
    };

})();
</script>
'''

    def __init__(self):
        self._generated_manager = False

    def generate_manager_script(self) -> str:
        """Generate the WebSocket manager script (once per page)."""
        if not self._generated_manager:
            self._generated_manager = True
            return self.WEBSOCKET_MANAGER_SCRIPT
        return ""

    def generate_connection(
        self,
        node: WebSocketNode,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate JavaScript for a WebSocket connection.

        Args:
            node: WebSocketNode from AST
            context: Current execution context

        Returns:
            JavaScript code string
        """
        config = WebSocketClientConfig(
            name=node.name,
            url=node.url,
            auto_connect=node.auto_connect,
            reconnect=node.reconnect,
            reconnect_delay=node.reconnect_delay,
            max_reconnects=node.max_reconnects,
            heartbeat=node.heartbeat,
            protocols=[p.strip() for p in node.protocols.split(",") if p.strip()] if node.protocols else []
        )

        # Generate handler registrations
        handler_code = self._generate_handlers(node)

        js = f'''
<script>
(function() {{
    // Initialize WebSocket: {node.name}
    var config = {json.dumps(config.to_dict())};
    var ws = window.__qCreateWebSocket(config);

    // Initialize state in context
    window.__qContext = window.__qContext || {{}};
    window.__qContext['{node.name}'] = ws.state;

    {handler_code}
}})();
</script>
'''
        return js

    def _generate_handlers(self, node: WebSocketNode) -> str:
        """Generate event handler registrations."""
        handlers = []

        for handler in node.handlers:
            event = handler.event
            # Normalize event names
            if event == "disconnect":
                event = "close"
            elif event == "open":
                event = "connect"

            # Generate handler body
            # For now, we'll create a simple handler that updates state
            # Full handler execution would require server-side coordination
            handler_js = f'''
    ws.on('{event}', function(eventData) {{
        console.log('[QWS:{node.name}] Event: {event}', eventData);
        // Update context with event data
        window.__qContext['{node.name}'] = ws.state;
        window.__qContext['{node.name}_event'] = eventData;
        window.__qContext['{node.name}_lastEvent'] = '{event}';

        // Trigger UI update if available
        if (window.__qUpdate) {{
            window.__qUpdate();
        }}
    }});'''
            handlers.append(handler_js)

        return "\n".join(handlers)

    def generate_send(
        self,
        connection: str,
        message: str,
        msg_type: str = "text"
    ) -> str:
        """
        Generate JavaScript for sending a message.

        Args:
            connection: Connection name
            message: Message content (may contain databinding)
            msg_type: Message type (text, json)

        Returns:
            JavaScript code
        """
        # Handle databinding in message
        if message.startswith("{") and message.endswith("}"):
            # It's a databinding expression
            var_name = message[1:-1]
            return f"window.__qWebSocketSend('{connection}', window.__qContext['{var_name}'], '{msg_type}');"
        else:
            # Static message
            return f"window.__qWebSocketSend('{connection}', {json.dumps(message)}, '{msg_type}');"

    def generate_close(
        self,
        connection: str,
        code: int = 1000,
        reason: str = ""
    ) -> str:
        """Generate JavaScript for closing a connection."""
        return f"window.__qWebSocketClose('{connection}', {code}, {json.dumps(reason)});"


# Global adapter instance
_html_adapter: WebSocketHTMLAdapter = None


def get_websocket_html_adapter() -> WebSocketHTMLAdapter:
    """Get the global WebSocket HTML adapter."""
    global _html_adapter
    if _html_adapter is None:
        _html_adapter = WebSocketHTMLAdapter()
    return _html_adapter
