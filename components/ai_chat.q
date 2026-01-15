<q:component name="AIChat">
  <!-- Define AI assistant -->
  <q:llm id="assistant" model="llama3" provider="ollama">
    <default-prompt>You are a helpful AI assistant named Quantum AI. Be friendly, concise, and helpful.</default-prompt>
  </q:llm>

  <html>
    <head>
      <title>Quantum AI Chat</title>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>
      <div class="chat-container">
        <div class="header">
          <h1>🤖 Quantum AI Chat</h1>
          <p>Powered by Ollama (Local & Free)</p>
        </div>

        <!-- Chat area -->
        <div class="chat-messages">
          <div class="message assistant">
            <strong>Quantum AI:</strong>
            <p>Hello! I'm your AI assistant. Ask me anything!</p>
          </div>

          <!-- Handle user message -->
          <q:if condition="{query.message}">
            <div class="message user">
              <strong>You:</strong>
              <p>{query.message}</p>
            </div>

            <!-- Generate AI response -->
            <q:llm-generate
              llm="assistant"
              prompt="{query.message}"
              result="aiResponse" />

            <div class="message assistant">
              <strong>Quantum AI:</strong>
              <p>{aiResponse}</p>
            </div>
          </q:if>
        </div>

        <!-- Input form -->
        <form method="GET" class="chat-input">
          <input
            type="text"
            name="message"
            placeholder="Type your message..."
            required
            autofocus />
          <button type="submit">Send</button>
        </form>

        <div class="footer">
          <p>💡 <strong>Tip:</strong> Make sure Ollama is running locally!</p>
          <p>Install: <code>curl https://ollama.ai/install.sh | sh</code></p>
          <p>Pull model: <code>ollama pull llama3</code></p>
        </div>
      </div>

      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
        }

        .chat-container {
          width: 100%;
          max-width: 800px;
          background: white;
          border-radius: 20px;
          box-shadow: 0 20px 60px rgba(0,0,0,0.3);
          overflow: hidden;
          display: flex;
          flex-direction: column;
          max-height: 90vh;
        }

        .header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 30px;
          text-align: center;
        }

        .header h1 {
          font-size: 2em;
          margin-bottom: 10px;
        }

        .header p {
          opacity: 0.9;
          font-size: 0.9em;
        }

        .chat-messages {
          flex: 1;
          padding: 20px;
          overflow-y: auto;
          background: #f8f9fa;
        }

        .message {
          margin-bottom: 20px;
          padding: 15px;
          border-radius: 10px;
          animation: fadeIn 0.3s ease-in;
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .message.user {
          background: #e3f2fd;
          border-left: 4px solid #2196f3;
        }

        .message.assistant {
          background: #f3e5f5;
          border-left: 4px solid #9c27b0;
        }

        .message strong {
          display: block;
          margin-bottom: 8px;
          color: #333;
        }

        .message p {
          color: #555;
          line-height: 1.6;
          white-space: pre-wrap;
        }

        .chat-input {
          display: flex;
          padding: 20px;
          background: white;
          border-top: 1px solid #e0e0e0;
        }

        .chat-input input {
          flex: 1;
          padding: 15px;
          border: 2px solid #e0e0e0;
          border-radius: 10px;
          font-size: 1em;
          outline: none;
          transition: border-color 0.3s;
        }

        .chat-input input:focus {
          border-color: #667eea;
        }

        .chat-input button {
          margin-left: 10px;
          padding: 15px 30px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 10px;
          font-size: 1em;
          font-weight: bold;
          cursor: pointer;
          transition: transform 0.2s, box-shadow 0.2s;
        }

        .chat-input button:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        .chat-input button:active {
          transform: translateY(0);
        }

        .footer {
          background: #f8f9fa;
          padding: 15px;
          text-align: center;
          border-top: 1px solid #e0e0e0;
          font-size: 0.85em;
          color: #666;
        }

        .footer p {
          margin: 5px 0;
        }

        .footer code {
          background: #e0e0e0;
          padding: 2px 6px;
          border-radius: 3px;
          font-family: 'Courier New', monospace;
        }
      </style>
    </body>
  </html>
</q:component>
