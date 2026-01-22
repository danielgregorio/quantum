<q:component name="RAGDemo">
  <!-- Define Knowledge Base -->
  <q:knowledge
    id="docs"
    source="./docs/sample/*.md"
    embedding="ollama"
    chunk_size="500"
    chunk_overlap="100"
    vector_db="chromadb" />

  <!-- Define LLM -->
  <q:llm id="assistant" model="llama3" temperature="0.7">
    <default-prompt>
      You are a helpful Quantum Framework assistant.
      Answer questions based on the provided context.
      Be concise and accurate.
    </default-prompt>
  </q:llm>

  <html>
    <head>
      <meta charset="UTF-8">
      <title>RAG Demo - Smart Docs Search</title>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>🔍 Smart Documentation Search</h1>
          <p>Powered by RAG (Retrieval-Augmented Generation)</p>
          <p class="tech-stack">
            Ollama (LLM) + ChromaDB (Vector Store) + Local Embeddings
          </p>
        </div>

        <!-- Search Form -->
        <form method="GET" class="search-form">
          <input
            type="text"
            name="q"
            placeholder="Ask anything about Quantum Framework..."
            value="{query.q}"
            autofocus
            required />
          <button type="submit">🔍 Search</button>
        </form>

        <!-- Search Results -->
        <q:if condition="{query.q}">
          <div class="loading">
            <p>🔄 Searching knowledge base...</p>
          </div>

          <!-- Perform Semantic Search -->
          <q:search
            knowledge="docs"
            query="{query.q}"
            result="searchResults"
            top_k="3" />

          <div class="results">
            <h2>📚 Retrieved Documents</h2>

            <q:if condition="{searchResults}">
              <q:loop type="array" array="{searchResults}" item="result">
                <div class="result-card">
                  <div class="result-score">
                    Relevance: {result.score}
                  </div>
                  <div class="result-content">
                    {result.content}
                  </div>
                  <div class="result-meta">
                    Source: {result.metadata.source}
                  </div>
                </div>
              </q:loop>

              <!-- Build context from results -->
              <q:set name="context" value="" />
              <q:loop type="array" array="{searchResults}" item="result">
                <q:set name="context" value="{context}\n\n{result.content}" />
              </q:loop>

              <!-- Generate AI Answer -->
              <div class="ai-section">
                <h2>🤖 AI-Generated Answer</h2>

                <q:llm-generate
                  llm="assistant"
                  prompt="Based on this context:\n{context}\n\nAnswer this question: {query.q}"
                  result="aiAnswer"
                  cache="true" />

                <div class="ai-answer">
                  {aiAnswer}
                </div>
              </div>
            </q:if>

            <q:else>
              <div class="no-results">
                <p>❌ No relevant documents found.</p>
                <p>Try a different query or check if documents are loaded.</p>
              </div>
            </q:else>
          </div>
        </q:if>

        <!-- Instructions -->
        <div class="instructions">
          <h3>💡 How it works:</h3>
          <ol>
            <li><strong>Knowledge Base</strong>: Documents from <code>./docs/sample/*.md</code></li>
            <li><strong>Semantic Search</strong>: Finds relevant chunks using embeddings</li>
            <li><strong>AI Generation</strong>: Llama 3 generates answer from context</li>
          </ol>

          <h3>🔧 Setup:</h3>
          <pre>
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama3
ollama pull nomic-embed-text  # For embeddings

# Install Python deps
pip install chromadb ollama

# Start server
python quantum.py start
          </pre>

          <h3>📝 Example Queries:</h3>
          <ul>
            <li>"What is Quantum Framework?"</li>
            <li>"How do I use LLMs in Quantum?"</li>
            <li>"What models are supported?"</li>
            <li>"How do I create a component?"</li>
          </ul>
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
          max-width: 1000px;
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

        .tech-stack {
          font-size: 0.9em;
          opacity: 0.9;
          margin-top: 10px;
        }

        .search-form {
          display: flex;
          gap: 10px;
          margin-bottom: 30px;
        }

        .search-form input {
          flex: 1;
          padding: 15px 20px;
          font-size: 1.1em;
          border: none;
          border-radius: 10px;
          outline: none;
        }

        .search-form button {
          padding: 15px 30px;
          font-size: 1.1em;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 10px;
          cursor: pointer;
          font-weight: bold;
          transition: transform 0.2s;
        }

        .search-form button:hover {
          transform: translateY(-2px);
        }

        .loading {
          background: rgba(255, 255, 255, 0.1);
          padding: 20px;
          border-radius: 10px;
          text-align: center;
          color: white;
          margin-bottom: 20px;
        }

        .results {
          background: white;
          border-radius: 20px;
          padding: 30px;
          margin-bottom: 30px;
        }

        .results h2 {
          color: #333;
          margin-bottom: 20px;
          border-bottom: 3px solid #667eea;
          padding-bottom: 10px;
        }

        .result-card {
          background: #f8f9fa;
          border-left: 4px solid #667eea;
          padding: 20px;
          margin-bottom: 15px;
          border-radius: 8px;
        }

        .result-score {
          font-size: 0.9em;
          color: #667eea;
          font-weight: bold;
          margin-bottom: 10px;
        }

        .result-content {
          color: #333;
          line-height: 1.6;
          margin-bottom: 10px;
        }

        .result-meta {
          font-size: 0.85em;
          color: #666;
          font-style: italic;
        }

        .ai-section {
          margin-top: 30px;
          padding-top: 30px;
          border-top: 2px solid #eee;
        }

        .ai-answer {
          background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
          padding: 25px;
          border-radius: 10px;
          border-left: 4px solid #764ba2;
          color: #333;
          line-height: 1.8;
          font-size: 1.05em;
        }

        .no-results {
          text-align: center;
          padding: 40px;
          color: #666;
        }

        .instructions {
          background: rgba(255, 255, 255, 0.1);
          backdrop-filter: blur(10px);
          padding: 30px;
          border-radius: 20px;
          color: white;
        }

        .instructions h3 {
          margin-top: 20px;
          margin-bottom: 15px;
          font-size: 1.3em;
        }

        .instructions ol, .instructions ul {
          margin-left: 20px;
          line-height: 1.8;
        }

        .instructions code {
          background: rgba(0, 0, 0, 0.3);
          padding: 2px 8px;
          border-radius: 4px;
          font-family: 'Courier New', monospace;
        }

        .instructions pre {
          background: rgba(0, 0, 0, 0.3);
          padding: 20px;
          border-radius: 10px;
          overflow-x: auto;
          margin: 15px 0;
          line-height: 1.6;
        }
      </style>
    </body>
  </html>
</q:component>
