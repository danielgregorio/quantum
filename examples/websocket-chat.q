<?xml version="1.0" encoding="UTF-8"?>
<!--
    WebSocket Chat Example

    Demonstrates real-time bidirectional communication using WebSockets.
    Features:
    - Auto-connect with reconnect on disconnect
    - Event handlers for connect, message, error, close
    - Message sending via websocket-send
    - Connection status display
-->
<q:component name="WebSocketChat" xmlns:q="urn:quantum">
    <!-- State variables -->
    <q:set name="connected" value="false" />
    <q:set name="messages" value="[]" />
    <q:set name="userInput" value="" />
    <q:set name="connectionStatus" value="Disconnected" />
    <q:set name="errorMessage" value="" />

    <!-- WebSocket connection with auto-reconnect -->
    <q:websocket name="chat"
                 url="wss://echo.websocket.org"
                 auto_connect="true"
                 reconnect="true"
                 reconnect_delay="2000"
                 max_reconnects="5"
                 heartbeat="30000">

        <!-- Handle connection open -->
        <q:on-connect>
            <q:set name="connected" value="true" />
            <q:set name="connectionStatus" value="Connected" />
            <q:set name="errorMessage" value="" />
            <q:log message="WebSocket connected to chat server" />
        </q:on-connect>

        <!-- Handle incoming messages -->
        <q:on-message>
            <q:set name="newMessage" value="{data}" />
            <!-- Add message to list -->
            <q:log level="info" message="Received: {data}" />
        </q:on-message>

        <!-- Handle errors -->
        <q:on-error>
            <q:set name="errorMessage" value="Connection error occurred" />
            <q:log level="error" message="WebSocket error" />
        </q:on-error>

        <!-- Handle connection close -->
        <q:on-close>
            <q:set name="connected" value="false" />
            <q:set name="connectionStatus" value="Disconnected" />
            <q:log level="warn" message="WebSocket closed" />
        </q:on-close>
    </q:websocket>

    <!-- Send message action -->
    <q:action name="sendMessage">
        <q:if condition="{connected}">
            <q:websocket-send connection="chat" message="{userInput}" type="text" />
            <q:set name="userInput" value="" />
        </q:if>
    </q:action>

    <!-- Disconnect action -->
    <q:action name="disconnect">
        <q:websocket-close connection="chat" code="1000" reason="User disconnected" />
    </q:action>

    <!-- UI -->
    <div class="chat-container">
        <!-- Status bar -->
        <div class="status-bar">
            <span class="status-indicator {connected ? 'connected' : 'disconnected'}"></span>
            <span>{connectionStatus}</span>
            <q:if condition="{errorMessage}">
                <span class="error">{errorMessage}</span>
            </q:if>
        </div>

        <!-- Messages area -->
        <div class="messages">
            <q:loop name="msg" items="{messages}">
                <div class="message">{msg}</div>
            </q:loop>
        </div>

        <!-- Input area -->
        <div class="input-area">
            <input type="text"
                   q:bind="userInput"
                   placeholder="Type a message..."
                   onkeypress="if(event.key==='Enter') sendMessage()" />
            <button q:action="sendMessage" disabled="{!connected}">Send</button>
            <button q:action="disconnect" disabled="{!connected}">Disconnect</button>
        </div>
    </div>

    <style>
        .chat-container {
            max-width: 600px;
            margin: 20px auto;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .status-bar {
            padding: 10px;
            background: #f5f5f5;
            border-bottom: 1px solid #ddd;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .status-indicator.connected { background: #4caf50; }
        .status-indicator.disconnected { background: #f44336; }
        .error { color: #f44336; margin-left: auto; }
        .messages {
            height: 300px;
            overflow-y: auto;
            padding: 10px;
        }
        .message {
            padding: 8px 12px;
            margin: 5px 0;
            background: #e3f2fd;
            border-radius: 4px;
        }
        .input-area {
            padding: 10px;
            display: flex;
            gap: 10px;
            border-top: 1px solid #ddd;
        }
        .input-area input {
            flex: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .input-area button {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .input-area button:first-of-type {
            background: #2196f3;
            color: white;
        }
        .input-area button:last-of-type {
            background: #f44336;
            color: white;
        }
        .input-area button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    </style>
</q:component>
