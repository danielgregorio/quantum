<q:component name="LLMChat">

  <!-- Initialize session history if empty -->
  <q:if condition="{session.chatHistory} == ''">
    <q:set name="session.chatHistory" type="array" value="[]" />
  </q:if>

  <!-- Handle clear -->
  <q:if condition="{form.action_type} == 'clear'">
    <q:set name="session.chatHistory" type="array" value="[]" />
  </q:if>

  <!-- Handle user message POST -->
  <q:if condition="{form.message}">
    <!-- Store user message -->
    <q:set name="session.chatHistory" operation="append" value="YOU: {form.message}" />

    <!-- Call LLM -->
    <q:llm name="aiReply" model="phi3" endpoint="http://10.10.1.40:11434" maxTokens="300">
      <q:message role="system">You are a helpful, concise assistant. Answer in 1-3 sentences. Be friendly.</q:message>
      <q:message role="user">{form.message}</q:message>
    </q:llm>

    <!-- Store AI reply -->
    <q:set name="session.chatHistory" operation="append" value="AI: {aiReply}" />
  </q:if>

  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f0f1a; color: #e0e0e0; }
    .chat-container { display: flex; flex-direction: column; height: 100vh; max-width: 800px; margin: 0 auto; }
    .chat-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white; padding: 16px 24px;
      display: flex; align-items: center; justify-content: space-between;
    }
    .chat-header h1 { font-size: 20px; font-weight: 600; }
    .chat-header .subtitle { font-size: 12px; opacity: 0.8; margin-top: 2px; }
    .btn-clear {
      padding: 8px 16px; background: rgba(255,255,255,0.15); color: white;
      border: 1px solid rgba(255,255,255,0.25); border-radius: 8px;
      font-size: 13px; cursor: pointer; transition: background 0.2s;
    }
    .btn-clear:hover { background: rgba(255,255,255,0.25); }
    .messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 12px; }
    .msg {
      padding: 14px 18px; border-radius: 16px;
      font-size: 15px; line-height: 1.6; word-wrap: break-word; white-space: pre-wrap;
    }
    .msg-you {
      align-self: flex-end; max-width: 75%;
      background: linear-gradient(135deg, #667eea, #764ba2); color: white;
      border-bottom-right-radius: 4px;
    }
    .msg-ai {
      align-self: flex-start; max-width: 85%;
      background: #1e1e2e; color: #e0e0e0;
      border: 1px solid #2a2a3a; border-bottom-left-radius: 4px;
    }
    .msg-label {
      font-size: 11px; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.5px; margin-bottom: 6px; opacity: 0.7;
    }
    .empty-state {
      flex: 1; display: flex; align-items: center; justify-content: center;
      text-align: center; color: #555;
    }
    .empty-state p { font-size: 18px; margin-bottom: 8px; }
    .empty-state small { font-size: 13px; color: #444; }
    .input-area {
      padding: 16px 24px; background: #1a1a2e;
      border-top: 1px solid #2a2a3a;
    }
    .input-area form { display: flex; gap: 12px; align-items: center; }
    .input-area input[type="text"] {
      flex: 1; padding: 14px 18px; background: #0f0f1a; color: #e0e0e0;
      border: 2px solid #2a2a3a; border-radius: 24px; font-size: 15px; outline: none;
    }
    .input-area input[type="text"]:focus { border-color: #667eea; }
    .input-area input[type="text"]::placeholder { color: #555; }
    .btn-send {
      padding: 14px 28px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: white; border: none; border-radius: 24px;
      font-size: 15px; font-weight: 600; cursor: pointer; transition: opacity 0.2s;
    }
    .btn-send:hover { opacity: 0.9; }
  </style>

  <div class="chat-container">
    <!-- Header -->
    <div class="chat-header">
      <div>
        <h1>Quantum LLM Chat</h1>
        <div class="subtitle">Powered by phi3 via Ollama</div>
      </div>
      <form method="POST" style="margin:0;">
        <input type="hidden" name="action_type" value="clear" />
        <button type="submit" class="btn-clear">Clear Chat</button>
      </form>
    </div>

    <!-- Messages -->
    <div class="messages" id="chat-messages">
      <q:if condition="{session.chatHistory.length} == 0">
        <div class="empty-state">
          <div>
            <p>Start a conversation</p>
            <small>Type a message below to chat with the AI</small>
          </div>
        </div>
      </q:if>

      <q:loop type="array" var="entry" items="{session.chatHistory}" index="idx">
        <div class="msg">{entry}</div>
      </q:loop>
    </div>

    <!-- Input -->
    <div class="input-area">
      <form method="POST">
        <input type="text" name="message" placeholder="Type your message..." required="required" autocomplete="off" />
        <button type="submit" class="btn-send">Send</button>
      </form>
    </div>
  </div>

  <script>
    // Style messages based on YOU:/AI: prefix and auto-scroll
    var chatEl = document.getElementById('chat-messages');
    if (chatEl) {
      Array.prototype.slice.call(chatEl.querySelectorAll('.msg')).forEach(function(el) {
        var text = el.textContent || '';
        if (text.indexOf('YOU:') === 0) {
          el.className = 'msg msg-you';
          el.innerHTML = text.substring(5);
        } else if (text.indexOf('AI:') === 0) {
          el.className = 'msg msg-ai';
          el.innerHTML = text.substring(4);
        }
      });
      chatEl.scrollTop = chatEl.scrollHeight;
    }
  </script>

</q:component>
