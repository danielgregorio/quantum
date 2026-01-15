<q:component name="AgentDemo">
  <!-- Setup Knowledge Base -->
  <q:knowledge
    id="docs"
    source="./docs/sample/*.md"
    embedding="ollama"
    chunk_size="500"
    vector_db="chromadb" />

  <!-- Setup LLM -->
  <q:llm id="assistant" model="llama3" temperature="0.7">
    <default-prompt>You are a helpful AI assistant.</default-prompt>
  </q:llm>

  <!-- Setup Agent with RAG Tools -->
  <q:agent id="docs_agent" llm="assistant" knowledge="docs">
    <goal>
      Help users understand Quantum Framework by:
      1. Searching the documentation when needed
      2. Providing accurate, helpful answers
      3. Citing sources when using retrieved information
    </goal>

    <tools>
      <tool name="search" knowledge="docs" top_k="3" />
    </tools>

    <personality>
      Be friendly, concise, and accurate.
      Always use the search tool to verify information before answering.
    </personality>
  </q:agent>

  <html>
    <head>
      <meta charset="UTF-8">
      <title>AI Agent Demo - RAG + Tools</title>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>🤖 Quantum AI Agent</h1>
          <p>Goal-Based Agent with RAG Tools</p>
          <div class="tech-badge">
            <span>🧠 Llama 3</span>
            <span>📚 RAG Search</span>
            <span>🛠️ Tools</span>
          </div>
        </div>

        <!-- Ask Agent -->
        <form method="GET" class="question-form">
          <input
            type="text"
            name="q"
            placeholder="Ask the agent anything about Quantum..."
            value="{query.q}"
            autofocus
            required />
          <label class="checkbox">
            <input type="checkbox" name="thinking" value="true" />
            Show agent's thinking process
          </label>
          <button type="submit">🤖 Ask Agent</button>
        </form>

        <!-- Agent Response -->
        <q:if condition="{query.q}">
          <div class="agent-section">
            <h2>🤖 Agent Response</h2>

            <div class="loading">
              <p>🔄 Agent is thinking and searching...</p>
            </div>

            <!-- Ask the Agent -->
            <q:agent-ask
              agent="docs_agent"
              question="{query.q}"
              result="agentAnswer"
              sources="agentSources"
              show_thinking="{query.thinking}" />

            <!-- Display Answer -->
            <div class="agent-answer">
              <h3>💬 Answer:</h3>
              <div class="answer-content">
                {agentAnswer.answer}
              </div>
            </div>

            <!-- Display Sources -->
            <q:if condition="{agentAnswer.sources}">
              <div class="sources-section">
                <h3>📚 Sources Used:</h3>
                <q:loop type="array" array="{agentAnswer.sources}" item="source">
                  <div class="source-card">
                    <div class="source-header">
                      <strong>Tool:</strong> {source.tool}
                    </div>
                    <div class="source-input">
                      <strong>Input:</strong> {source.input}
                    </div>
                    <div class="source-output">
                      <strong>Output:</strong>
                      <pre>{source.output}</pre>
                    </div>
                  </div>
                </q:loop>
              </div>
            </q:if>

            <!-- Display Thinking Process -->
            <q:if condition="{agentAnswer.thinking}">
              <div class="thinking-section">
                <h3>🧠 Agent's Thinking Process:</h3>
                <div class="thinking-steps">
                  <q:loop type="array" array="{agentAnswer.thinking}" item="step">
                    <div class="thinking-step">{step}</div>
                  </q:loop>
                </div>
              </div>
            </q:if>
          </div>
        </q:if>

        <!-- Instructions -->
        <div class="instructions">
          <h3>💡 How This Agent Works:</h3>

          <div class="workflow">
            <div class="workflow-step">
              <div class="step-number">1</div>
              <div class="step-content">
                <strong>User asks a question</strong>
                <p>Agent receives the question and understands its goal</p>
              </div>
            </div>

            <div class="workflow-step">
              <div class="step-number">2</div>
              <div class="step-content">
                <strong>Agent reasons</strong>
                <p>Uses LLM to think about what information is needed</p>
              </div>
            </div>

            <div class="workflow-step">
              <div class="step-number">3</div>
              <div class="step-content">
                <strong>Searches documentation</strong>
                <p>Uses RAG search tool to find relevant information</p>
              </div>
            </div>

            <div class="workflow-step">
              <div class="step-number">4</div>
              <div class="step-content">
                <strong>Synthesizes answer</strong>
                <p>Combines retrieved info to generate accurate answer</p>
              </div>
            </div>
          </div>

          <h3>🎯 Try These Questions:</h3>
          <ul>
            <li>"What is Quantum Framework?"</li>
            <li>"How do I use LLMs in Quantum?"</li>
            <li>"What are the key features?"</li>
            <li>"How does RAG work?"</li>
          </ul>

          <h3>🔧 Agent Configuration:</h3>
          <pre>
&lt;q:agent id="docs_agent" llm="assistant" knowledge="docs"&gt;
  &lt;goal&gt;Help users understand Quantum Framework&lt;/goal&gt;
  &lt;tools&gt;
    &lt;tool name="search" knowledge="docs" /&gt;
  &lt;/tools&gt;
&lt;/q:agent&gt;
          </pre>
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
          padding: 20px;
        }

        .container {
          max-width: 1100px;
          margin: 0 auto;
        }

        .header {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          padding: 40px;
          border-radius: 20px;
          text-align: center;
          color: white;
          margin-bottom: 30px;
        }

        .header h1 {
          font-size: 2.5em;
          margin-bottom: 10px;
        }

        .tech-badge {
          margin-top: 15px;
          display: flex;
          gap: 10px;
          justify-content: center;
        }

        .tech-badge span {
          background: rgba(255, 255, 255, 0.2);
          padding: 8px 15px;
          border-radius: 20px;
          font-size: 0.9em;
        }

        .question-form {
          background: white;
          padding: 30px;
          border-radius: 20px;
          margin-bottom: 30px;
        }

        .question-form input[type="text"] {
          width: 100%;
          padding: 15px 20px;
          font-size: 1.1em;
          border: 2px solid #e0e0e0;
          border-radius: 10px;
          outline: none;
          margin-bottom: 15px;
        }

        .question-form input[type="text"]:focus {
          border-color: #667eea;
        }

        .checkbox {
          display: block;
          margin-bottom: 15px;
          font-size: 0.95em;
          color: #666;
        }

        .question-form button {
          width: 100%;
          padding: 15px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 10px;
          font-size: 1.1em;
          font-weight: bold;
          cursor: pointer;
          transition: transform 0.2s;
        }

        .question-form button:hover {
          transform: translateY(-2px);
        }

        .agent-section {
          background: white;
          border-radius: 20px;
          padding: 30px;
          margin-bottom: 30px;
        }

        .agent-section h2, .agent-section h3 {
          color: #333;
          margin-bottom: 20px;
        }

        .loading {
          text-align: center;
          padding: 20px;
          background: #f0f7ff;
          border-radius: 10px;
          color: #667eea;
          margin-bottom: 20px;
        }

        .agent-answer {
          background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
          border-left: 4px solid #667eea;
          padding: 25px;
          border-radius: 10px;
          margin-bottom: 30px;
        }

        .answer-content {
          color: #333;
          line-height: 1.8;
          font-size: 1.05em;
        }

        .sources-section {
          margin-bottom: 30px;
          padding-top: 20px;
          border-top: 2px solid #f0f0f0;
        }

        .source-card {
          background: #f8f9fa;
          border-left: 4px solid #28a745;
          padding: 20px;
          margin-bottom: 15px;
          border-radius: 8px;
        }

        .source-header, .source-input {
          margin-bottom: 10px;
          color: #555;
        }

        .source-output pre {
          background: #2c3e50;
          color: #ecf0f1;
          padding: 15px;
          border-radius: 5px;
          overflow-x: auto;
          margin-top: 10px;
          font-size: 0.9em;
        }

        .thinking-section {
          padding-top: 20px;
          border-top: 2px solid #f0f0f0;
        }

        .thinking-steps {
          background: #fff8e1;
          padding: 20px;
          border-radius: 10px;
          border-left: 4px solid #ffc107;
        }

        .thinking-step {
          padding: 10px 0;
          color: #666;
          font-family: 'Courier New', monospace;
          font-size: 0.9em;
          border-bottom: 1px solid #f0f0f0;
        }

        .thinking-step:last-child {
          border-bottom: none;
        }

        .instructions {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          padding: 30px;
          border-radius: 20px;
          color: white;
        }

        .instructions h3 {
          margin-top: 30px;
          margin-bottom: 15px;
          font-size: 1.3em;
        }

        .instructions h3:first-child {
          margin-top: 0;
        }

        .workflow {
          display: grid;
          gap: 15px;
          margin: 20px 0;
        }

        .workflow-step {
          display: flex;
          gap: 15px;
          background: rgba(255, 255, 255, 0.1);
          padding: 20px;
          border-radius: 10px;
        }

        .step-number {
          width: 40px;
          height: 40px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: bold;
          font-size: 1.2em;
          flex-shrink: 0;
        }

        .step-content strong {
          display: block;
          margin-bottom: 5px;
        }

        .step-content p {
          opacity: 0.9;
          font-size: 0.9em;
        }

        .instructions ul {
          margin-left: 20px;
          line-height: 1.8;
        }

        .instructions pre {
          background: rgba(0, 0, 0, 0.3);
          padding: 20px;
          border-radius: 10px;
          overflow-x: auto;
          margin: 15px 0;
        }
      </style>
    </body>
  </html>
</q:component>
