<q:component name="SimpleRAG">
  <!--
    🔥 RAG + LLM SUPER SIMPLES

    Como usar:
    http://localhost:8000/simple-rag?q=how+to+use+quantum

    O que faz:
    1. Busca nos docs (semantic search)
    2. Pega top 3 chunks
    3. Manda pro LLM com contexto
    4. Mostra resposta + fontes
  -->

  <h1>🔍 Quantum RAG Demo</h1>

  <q:if condition="{query.q}">
    <!-- 1. BUSCA (semantic search) -->
    <q:query name="docs" datasource="knowledge_base" top_k="3">
      {query.q}
    </q:query>

    <!-- 2. MONTA CONTEXTO -->
    <q:set name="context" value="" />
    <q:loop type="array" array="{docs.results}" item="doc">
      <q:set name="context" operation="add" value="{context}

---
{doc.content}
" />
    </q:loop>

    <!-- 3. PERGUNTA PRA IA -->
    <q:query name="answer" datasource="ai">
Context from Quantum documentation:
{context}

User question: {query.q}

Based ONLY on the context above, provide a helpful answer.
If the context doesn't contain enough information, say so.
    </q:query>

    <!-- 4. MOSTRA RESPOSTA -->
    <div class="answer-box">
      <h2>💡 Answer:</h2>
      <div class="answer-content">{answer}</div>

      <details class="sources">
        <summary>📚 Sources ({docs.count} documents)</summary>
        <q:loop type="array" array="{docs.results}" item="src">
          <div class="source-card">
            <div class="source-score">
              Relevance: {src.score}
            </div>
            <div class="source-content">
              {src.content}
            </div>
            <small class="source-meta">
              Source: {src.metadata.source}
            </small>
          </div>
        </q:loop>
      </details>
    </div>
  </q:if>

  <q:else>
    <!-- FORMULÁRIO DE BUSCA -->
    <div class="search-box">
      <h2>Ask anything about Quantum:</h2>
      <form method="GET">
        <input type="text" name="q"
          placeholder="e.g., How do I create a component?"
          autofocus />
        <button type="submit">🔍 Search</button>
      </form>

      <div class="examples">
        <h3>Try these:</h3>
        <ul>
          <li><a href="?q=how+to+create+components">How to create components?</a></li>
          <li><a href="?q=what+is+databinding">What is databinding?</a></li>
          <li><a href="?q=how+to+use+loops">How to use loops?</a></li>
          <li><a href="?q=database+queries">How do database queries work?</a></li>
        </ul>
      </div>
    </div>
  </q:else>

  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      max-width: 900px;
      margin: 0 auto;
      padding: 20px;
      background: #f5f5f5;
    }

    h1 {
      color: #2c3e50;
      text-align: center;
    }

    .search-box {
      background: white;
      padding: 40px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .search-box input {
      width: 100%;
      padding: 15px;
      font-size: 16px;
      border: 2px solid #e0e0e0;
      border-radius: 8px;
      margin-bottom: 10px;
    }

    .search-box input:focus {
      outline: none;
      border-color: #3498db;
    }

    .search-box button {
      width: 100%;
      padding: 15px;
      font-size: 16px;
      background: #3498db;
      color: white;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-weight: bold;
    }

    .search-box button:hover {
      background: #2980b9;
    }

    .examples {
      margin-top: 30px;
    }

    .examples h3 {
      color: #7f8c8d;
      font-size: 14px;
      text-transform: uppercase;
    }

    .examples ul {
      list-style: none;
      padding: 0;
    }

    .examples li {
      margin: 8px 0;
    }

    .examples a {
      color: #3498db;
      text-decoration: none;
    }

    .examples a:hover {
      text-decoration: underline;
    }

    .answer-box {
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      margin-top: 20px;
    }

    .answer-box h2 {
      margin-top: 0;
      color: #2c3e50;
      border-bottom: 3px solid #3498db;
      padding-bottom: 10px;
    }

    .answer-content {
      line-height: 1.8;
      color: #34495e;
      margin: 20px 0;
      white-space: pre-wrap;
    }

    .sources {
      margin-top: 30px;
      border-top: 2px solid #ecf0f1;
      padding-top: 20px;
    }

    .sources summary {
      cursor: pointer;
      font-weight: bold;
      color: #7f8c8d;
      padding: 10px;
      background: #ecf0f1;
      border-radius: 6px;
    }

    .sources summary:hover {
      background: #d5dbdb;
    }

    .source-card {
      background: #f8f9fa;
      border-left: 4px solid #3498db;
      padding: 15px;
      margin: 15px 0;
      border-radius: 4px;
    }

    .source-score {
      display: inline-block;
      background: #3498db;
      color: white;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
      margin-bottom: 10px;
    }

    .source-content {
      color: #555;
      line-height: 1.6;
      margin: 10px 0;
    }

    .source-meta {
      color: #95a5a6;
      font-size: 12px;
    }
  </style>
</q:component>
