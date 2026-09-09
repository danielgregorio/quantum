<q:component name="QuantumAssistant" xmlns:q="https://quantum.lang/ns">

  <!-- 1. Knowledge base: index features/ with persist (only indexes once) -->
  <q:knowledge name="quantum" model="phi3" embedModel="nomic-embed-text"
               chunkSize="400" chunkOverlap="50"
               persist="true" persistPath="./quantum_kb">
    <q:source type="directory" path="./src/core/features/" pattern="*.intent" />
    <q:source type="directory" path="./src/core/features/" pattern="*.q" />
    <q:source type="directory" path="./src/core/features/" pattern="*.yaml" />
  </q:knowledge>

  <!-- 2. If there's a question via POST: RAG + search -->
  <q:if condition="{form.question}">
    <q:set name="userQuestion" value="{form.question}" />

    <!-- RAG: full answer from LLM with context -->
    <q:query name="answer" datasource="knowledge:quantum" mode="rag" model="phi3">
      SELECT answer, sources, confidence FROM knowledge WHERE question = :q LIMIT 5
      <q:param name="q" value="{userQuestion}" type="string" />
    </q:query>

    <!-- Search: relevant chunks from dataset -->
    <q:query name="examples" datasource="knowledge:quantum">
      SELECT content, relevance, source FROM chunks WHERE content SIMILAR TO :q LIMIT 4
      <q:param name="q" value="{userQuestion}" type="string" />
    </q:query>
  </q:if>

  <!-- 3. UI -->
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; }

    .page { max-width: 800px; margin: 0 auto; padding: 24px 16px; min-height: 100vh; }

    .header { text-align: center; margin-bottom: 32px; }
    .header h1 {
      font-size: 32px; font-weight: 700; color: #1a1a2e;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .header p { color: #666; font-size: 15px; margin-top: 8px; }

    .search-form { margin-bottom: 24px; }
    .search-form form { display: flex; gap: 12px; }
    .search-form input[type="text"] {
      flex: 1; padding: 16px 20px; border: 2px solid #e0e0e0; border-radius: 12px;
      font-size: 16px; outline: none; background: white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .search-form input[type="text"]:focus { border-color: #667eea; }
    .btn-ask {
      padding: 16px 28px; background: linear-gradient(135deg, #667eea, #764ba2);
      color: white; border: none; border-radius: 12px; font-size: 16px;
      font-weight: 600; cursor: pointer; white-space: nowrap;
      box-shadow: 0 4px 12px rgba(102,126,234,0.4);
    }
    .btn-ask:hover { opacity: 0.95; }

    .suggestions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 32px; }
    .chip {
      padding: 10px 16px; background: white; border: 1px solid #e0e0e0;
      border-radius: 20px; font-size: 13px; color: #444; cursor: pointer;
      box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .chip:hover { border-color: #667eea; color: #667eea; background: #f8f7ff; }

    .answer-card {
      background: white; border-radius: 16px; padding: 28px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.08); margin-bottom: 24px;
    }
    .answer-card h2 { font-size: 18px; color: #1a1a2e; margin-bottom: 16px; }
    .answer-text { font-size: 15px; line-height: 1.7; color: #333; white-space: pre-wrap; }
    .answer-meta { display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; align-items: center; }
    .badge {
      display: inline-block; padding: 4px 12px; border-radius: 12px;
      font-size: 12px; font-weight: 600;
    }
    .badge-confidence { background: #e8f5e9; color: #2e7d32; }
    .badge-source { background: #e3f2fd; color: #1565c0; }

    .examples-section h2 { font-size: 18px; color: #1a1a2e; margin-bottom: 16px; }
    .example-card {
      background: white; border-radius: 12px; padding: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 12px;
    }
    .example-card pre {
      background: #f5f5f5; padding: 14px; border-radius: 8px;
      font-size: 13px; line-height: 1.5; overflow-x: auto;
      font-family: 'Fira Code', 'Consolas', monospace;
    }
    .example-meta { display: flex; gap: 8px; margin-top: 10px; }

    .question-label {
      font-size: 13px; color: #888; margin-bottom: 6px;
    }
    .question-text {
      font-size: 15px; color: #667eea; font-weight: 600; margin-bottom: 20px;
    }

    .footer { text-align: center; padding: 32px 0 16px; color: #999; font-size: 13px; }
    .footer a { color: #667eea; text-decoration: none; }
  </style>

  <div class="page">

    <!-- Header -->
    <div class="header">
      <h1>Quantum Assistant</h1>
      <p>Ask anything about the Quantum Framework — powered by its own dataset via RAG</p>
    </div>

    <!-- Search form -->
    <div class="search-form">
      <form method="POST" action="/quantum-assistant">
        <input type="text" name="question" placeholder="Ask about Quantum Framework..."
               value="{form.question}" autocomplete="off" />
        <button type="submit" class="btn-ask">Ask</button>
      </form>
    </div>

    <!-- Suggestion chips -->
    <div class="suggestions">
      <form method="POST" action="/quantum-assistant" style="display:inline">
        <input type="hidden" name="question" value="Como faco um loop?" />
        <button type="submit" class="chip">Como faco um loop?</button>
      </form>
      <form method="POST" action="/quantum-assistant" style="display:inline">
        <input type="hidden" name="question" value="Como funciona q:query?" />
        <button type="submit" class="chip">Como funciona q:query?</button>
      </form>
      <form method="POST" action="/quantum-assistant" style="display:inline">
        <input type="hidden" name="question" value="Como validar formularios?" />
        <button type="submit" class="chip">Como validar formularios?</button>
      </form>
      <form method="POST" action="/quantum-assistant" style="display:inline">
        <input type="hidden" name="question" value="Como usar sessoes?" />
        <button type="submit" class="chip">Como usar sessoes?</button>
      </form>
      <form method="POST" action="/quantum-assistant" style="display:inline">
        <input type="hidden" name="question" value="O que e q:set?" />
        <button type="submit" class="chip">O que e q:set?</button>
      </form>
      <form method="POST" action="/quantum-assistant" style="display:inline">
        <input type="hidden" name="question" value="Como funciona q:if?" />
        <button type="submit" class="chip">Como funciona q:if?</button>
      </form>
    </div>

    <!-- Answer section (only when there's a question) -->
    <q:if condition="{form.question}">

      <!-- RAG Answer -->
      <div class="answer-card">
        <div class="question-label">Your question:</div>
        <div class="question-text">{userQuestion}</div>
        <h2>Answer</h2>
        <div class="answer-text">{answer.answer}</div>
        <div class="answer-meta">
          <span class="badge badge-confidence">Confidence: {answer.confidence}</span>
          <span class="badge badge-source">Sources: {answer.sources}</span>
        </div>
      </div>

      <!-- Relevant examples from dataset -->
      <q:if condition="{examples.recordCount} > 0">
        <div class="examples-section">
          <h2>Relevant Examples from Dataset</h2>
          <q:loop query="examples">
            <div class="example-card">
              <pre>{content}</pre>
              <div class="example-meta">
                <span class="badge badge-source">{source}</span>
                <span class="badge badge-confidence">Relevance: {relevance}</span>
              </div>
            </div>
          </q:loop>
        </div>
      </q:if>

    </q:if>

    <!-- Footer -->
    <div class="footer">
      Built with <a href="#">Quantum Framework</a> — The framework that documents itself
    </div>

  </div>

</q:component>
