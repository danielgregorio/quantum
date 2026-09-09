<!-- Quantum Chat - Real-time chat app using HTMX polling -->
<q:component name="Chat" xmlns:q="https://quantum.lang/ns">

  <!-- Initialize application-scoped shared state (only if not already set) -->
  <q:if condition="{application.chatMessages} == ''">
    <q:set name="application.chatMessages" type="array" value="[]" />
    <q:set name="application.onlineUsers" type="array" value="[]" />
  </q:if>

  <!-- Handle login POST -->
  <q:if condition="{form.username}">
    <q:set name="session.chatUser" value="{form.username}" />
    <q:set name="application.onlineUsers" operation="append" value="{form.username}" />
  </q:if>

  <!-- Handle logout POST -->
  <q:if condition="{form.action_type} == 'logout'">
    <q:set name="application.onlineUsers" operation="remove" value="{session.chatUser}" />
    <q:set name="session.chatUser" value="" />
  </q:if>

  <!-- Handle send message POST -->
  <q:if condition="{form.message}">
    <q:set name="application.chatMessages" operation="append" value="{session.chatUser}: {form.message}" />
  </q:if>

  <!-- Main UI: Chat screen (logged in) or Login screen -->
  <q:if condition="{session.chatUser}">
    <!-- CHAT SCREEN -->
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
      .chat-layout { display: flex; flex-direction: column; height: 100vh; background: #f0f2f5; }
      .chat-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }
      .chat-header h1 { font-size: 20px; font-weight: 600; }
      .chat-header .meta { font-size: 12px; opacity: 0.85; margin-top: 4px; }
      .chat-header .user-info { display: flex; align-items: center; gap: 12px; }
      .chat-header .user-info span { font-size: 14px; opacity: 0.9; }
      .btn-leave { padding: 8px 16px; background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; font-size: 13px; cursor: pointer; }
      .messages-area { flex: 1; overflow-y: auto; padding: 20px 24px; }
      .msg-bubble { margin-bottom: 8px; }
      .msg-content { background: white; padding: 10px 16px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); max-width: 70%; word-wrap: break-word; font-size: 14px; line-height: 1.5; display: inline-block; }
      .empty-state { text-align: center; color: #999; padding: 60px 20px; }
      .empty-state p { font-size: 16px; }
      .input-area { padding: 16px 24px; background: white; border-top: 1px solid #e0e0e0; }
      .input-area form { display: flex; gap: 12px; align-items: center; }
      .input-area input[type="text"] { flex: 1; padding: 14px 18px; border: 2px solid #e0e0e0; border-radius: 24px; font-size: 15px; outline: none; }
      .input-area input[type="text"]:focus { border-color: #667eea; }
      .btn-send { padding: 14px 24px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 24px; font-size: 15px; font-weight: 600; cursor: pointer; white-space: nowrap; }
    </style>

    <div class="chat-layout">
      <!-- Header -->
      <div class="chat-header">
        <div>
          <h1>Quantum Chat</h1>
          <div class="meta">Online: {application.onlineUsers}</div>
        </div>
        <div class="user-info">
          <span>Hello, {session.chatUser}</span>
          <form method="POST" action="/chat" style="margin: 0;">
            <input type="hidden" name="action_type" value="logout" />
            <button type="submit" class="btn-leave">Leave</button>
          </form>
        </div>
      </div>

      <!-- Messages area with HTMX polling -->
      <div id="messages-container" class="messages-area"
           hx-get="/_partial/chat-messages"
           hx-trigger="every 2s"
           hx-target="#messages-container"
           hx-swap="innerHTML">

        <q:if condition="{application.chatMessages.length} == 0">
          <div class="empty-state">
            <p>No messages yet. Start the conversation!</p>
          </div>
        </q:if>

        <q:loop type="array" var="msg" items="{application.chatMessages}" index="idx">
          <div class="msg-bubble">
            <div class="msg-content">{msg}</div>
          </div>
        </q:loop>

      </div>

      <!-- Input area -->
      <div class="input-area">
        <form method="POST" action="/chat">
          <input type="text" name="message" placeholder="Type a message..." required="required" autocomplete="off" />
          <button type="submit" class="btn-send">Send</button>
        </form>
      </div>

    </div>

  <q:else>
    <!-- LOGIN SCREEN -->
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
      .login-bg { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
      .login-card { background: white; border-radius: 16px; padding: 48px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); width: 100%; max-width: 400px; text-align: center; }
      .login-card h1 { font-size: 28px; color: #1a1a2e; margin-bottom: 8px; }
      .login-card p { color: #666; font-size: 14px; margin-bottom: 32px; }
      .login-card form { display: flex; flex-direction: column; gap: 12px; }
      .login-card input { padding: 14px 16px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 16px; outline: none; }
      .login-card input:focus { border-color: #667eea; }
      .btn-join { padding: 14px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; }
    </style>

    <div class="login-bg">
      <div class="login-card">
        <h1>Quantum Chat</h1>
        <p>Enter your name to join the conversation</p>
        <form method="POST" action="/chat">
          <input type="text" name="username" placeholder="Your name..." required="required" />
          <button type="submit" class="btn-join">Join Chat</button>
        </form>
      </div>
    </div>
  </q:else>
  </q:if>

</q:component>
