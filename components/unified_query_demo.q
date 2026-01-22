<q:component name="UnifiedQueryDemo">
  <!--
    QUANTUM UNIFIED QUERY SYNTAX

    This demo shows the new unified query syntax where EVERYTHING is a datasource!
    - SQL databases
    - LLMs (AI)
    - Knowledge bases (RAG)
    - Cache (Redis)
    - External APIs

    All use the same <q:query> tag!
  -->

  <h1>🎯 Quantum Unified Query System</h1>

  <!-- ============================================ -->
  <!-- 1. SQL DATABASE QUERY -->
  <!-- ============================================ -->
  <h2>1. SQL Database</h2>
  <q:query name="users" datasource="db">
    SELECT * FROM users WHERE active = true LIMIT 5
  </q:query>

  <p>Found {users.recordCount} active users</p>

  <!-- ============================================ -->
  <!-- 2. LLM QUERY (AI Generation) -->
  <!-- ============================================ -->
  <h2>2. AI / LLM Query</h2>
  <q:set name="topic" value="quantum computing" />

  <!-- This looks like a query, but actually calls an LLM! -->
  <q:query name="explanation" datasource="ai">
    Explain {topic} in simple terms for beginners
  </q:query>

  <div class="ai-response">
    <h3>AI Explanation:</h3>
    <p>{explanation}</p>
  </div>

  <!-- ============================================ -->
  <!-- 3. KNOWLEDGE BASE QUERY (RAG / Semantic Search) -->
  <!-- ============================================ -->
  <h2>3. Knowledge Base / RAG Query</h2>
  <q:set name="searchTerm" value="authentication" />

  <!-- This looks like a query, but actually does semantic search! -->
  <q:query name="docs" datasource="knowledge_base">
    {searchTerm}
  </q:query>

  <div class="search-results">
    <h3>Found {docs.count} relevant docs:</h3>
    <q:loop type="array" array="{docs.results}" item="doc">
      <div class="result">
        <span class="score">Score: {doc.score}</span>
        <p>{doc.content}</p>
      </div>
    </q:loop>
  </div>

  <!-- ============================================ -->
  <!-- 4. COMBINED: RAG + LLM -->
  <!-- ============================================ -->
  <h2>4. Combined RAG + AI Answer</h2>

  <!-- Step 1: Search knowledge base -->
  <q:query name="context" datasource="knowledge_base" top_k="3">
    How to implement user authentication?
  </q:query>

  <!-- Step 2: Build context from results -->
  <q:set name="contextText" value="" />
  <q:loop type="array" array="{context.results}" item="result">
    <q:set name="contextText" operation="add" value="{contextText}\n\n{result.content}" />
  </q:loop>

  <!-- Step 3: Ask AI with context -->
  <q:query name="aiAnswer" datasource="ai">
    Based on this documentation:
    {contextText}

    Question: How to implement user authentication?

    Provide a concise, practical answer.
  </q:query>

  <div class="rag-answer">
    <h3>AI Answer with Context:</h3>
    <p>{aiAnswer}</p>

    <details>
      <summary>Sources ({context.count})</summary>
      <q:loop type="array" array="{context.results}" item="src">
        <p><small>{src.content}</small></p>
      </q:loop>
    </details>
  </div>

  <!-- ============================================ -->
  <!-- 5. COMPARISON: Old vs New Syntax -->
  <!-- ============================================ -->
  <hr />
  <h2>📊 Syntax Comparison</h2>

  <div class="comparison">
    <div class="old-way">
      <h3>❌ Old Way (Verbose)</h3>
      <pre><code>&lt;!-- SQL --&gt;
&lt;q:query name="users" datasource="db"&gt;
  SELECT * FROM users
&lt;/q:query&gt;

&lt;!-- LLM --&gt;
&lt;q:llm id="ai" model="llama3" /&gt;
&lt;q:llm-generate llm="ai"
  prompt="Explain {topic}"
  result="explanation" /&gt;

&lt;!-- RAG --&gt;
&lt;q:knowledge id="kb" source="./docs/*.md" /&gt;
&lt;q:search knowledge="kb"
  query="authentication"
  result="docs" /&gt;</code></pre>
    </div>

    <div class="new-way">
      <h3>✅ New Way (Unified)</h3>
      <pre><code>&lt;!-- Define datasources ONCE in Application.q --&gt;
&lt;datasource id="db" type="postgres" /&gt;
&lt;datasource id="ai" type="llm" model="llama3" /&gt;
&lt;datasource id="kb" type="knowledge" source="./docs/*.md" /&gt;

&lt;!-- Use SAME syntax everywhere --&gt;
&lt;q:query name="users" datasource="db"&gt;
  SELECT * FROM users
&lt;/q:query&gt;

&lt;q:query name="explanation" datasource="ai"&gt;
  Explain {topic}
&lt;/q:query&gt;

&lt;q:query name="docs" datasource="kb"&gt;
  authentication
&lt;/q:query&gt;</code></pre>
    </div>
  </div>

  <!-- ============================================ -->
  <!-- 6. BENEFITS -->
  <!-- ============================================ -->
  <div class="benefits">
    <h3>✨ Benefits of Unified Query Syntax:</h3>
    <ul>
      <li>✅ <strong>Consistency</strong> - Same pattern for all data sources</li>
      <li>✅ <strong>Simplicity</strong> - One tag to learn, not three</li>
      <li>✅ <strong>Reusability</strong> - Define datasource once, use everywhere</li>
      <li>✅ <strong>Flexibility</strong> - Swap datasources without changing queries</li>
      <li>✅ <strong>Clarity</strong> - Intent is obvious (querying data)</li>
      <li>✅ <strong>Power</strong> - All datasource features available (cache, reactive, etc)</li>
    </ul>
  </div>

  <style>
    .comparison {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin: 20px 0;
    }
    .old-way, .new-way {
      border: 2px solid #ddd;
      padding: 15px;
      border-radius: 8px;
    }
    .new-way {
      border-color: #4CAF50;
      background: #f1f8f4;
    }
    pre {
      background: #282c34;
      color: #abb2bf;
      padding: 15px;
      border-radius: 4px;
      overflow-x: auto;
    }
    .ai-response, .search-results, .rag-answer {
      background: #f5f5f5;
      padding: 15px;
      margin: 15px 0;
      border-left: 4px solid #2196F3;
    }
    .result {
      background: white;
      padding: 10px;
      margin: 10px 0;
      border-radius: 4px;
    }
    .score {
      background: #4CAF50;
      color: white;
      padding: 2px 8px;
      border-radius: 3px;
      font-size: 0.9em;
    }
    .benefits {
      background: #fff3cd;
      padding: 20px;
      border-radius: 8px;
      margin: 20px 0;
    }
    .benefits ul {
      list-style: none;
      padding-left: 0;
    }
    .benefits li {
      padding: 8px 0;
      font-size: 1.1em;
    }
  </style>
</q:component>
