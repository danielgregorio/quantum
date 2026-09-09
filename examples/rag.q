<q:component name="RAGDemo">

    <!-- Knowledge base with inline text sources -->
    <q:knowledge name="docs" model="phi3" embedModel="nomic-embed-text" chunkSize="300" chunkOverlap="30">
        <q:source type="text">
            Quantum Framework is a full-stack framework for building declarative web applications.
            It is inspired by ColdFusion and Adobe Flex. Applications are written in XML using
            the q: namespace prefix. Variables are set with q:set, loops with q:loop, and
            conditionals with q:if. Database queries use q:query with parameterized SQL.
        </q:source>
        <q:source type="text">
            The q:knowledge tag enables RAG (Retrieval-Augmented Generation) by defining
            virtual knowledge bases. Text is chunked, embedded via Ollama, and stored in
            ChromaDB for vector similarity search. Queries against knowledge bases use
            the standard q:query tag with datasource="knowledge:name".
        </q:source>
        <q:source type="text">
            Quantum supports LLM integration through the q:llm tag. It connects to Ollama
            for local model inference. Supported operations include text generation, chat,
            and structured JSON output. Models like phi3, mistral, and llama3 are supported.
        </q:source>
    </q:knowledge>

    <!-- Initialize state -->
    <q:set name="hasQuestion" value="0" />
    <q:set name="userQuestion" value="" />

    <!-- Process form submission (executor correctly evaluates form.question as falsy on GET) -->
    <q:if condition="{form.question}">
        <q:set name="hasQuestion" value="1" />
        <q:set name="userQuestion" value="{form.question}" />

        <!-- Vector search -->
        <q:query name="searchResults" datasource="knowledge:docs">
            SELECT content, relevance, source
            FROM chunks
            WHERE content SIMILAR TO :question
            LIMIT 3
            <q:param name="question" value="{userQuestion}" type="string" />
        </q:query>

        <!-- RAG query -->
        <q:query name="answer" datasource="knowledge:docs" mode="rag" model="phi3">
            SELECT answer, sources, confidence
            FROM knowledge
            WHERE question = :question
            <q:param name="question" value="{userQuestion}" type="string" />
        </q:query>
    </q:if>

    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f2f5; }
        .rag-container { max-width: 800px; margin: 0 auto; padding: 40px 20px; }
        .rag-header { text-align: center; margin-bottom: 32px; }
        .rag-header h1 { font-size: 28px; color: #1a1a2e; margin-bottom: 8px; }
        .rag-header p { color: #666; font-size: 15px; }
        .search-card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 24px; }
        .search-card form { display: flex; gap: 12px; }
        .search-card input[type="text"] { flex: 1; padding: 14px 18px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 15px; outline: none; }
        .search-card input[type="text"]:focus { border-color: #667eea; }
        .btn-ask { padding: 14px 28px; background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; cursor: pointer; white-space: nowrap; }
        .answer-card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 24px; }
        .answer-card h2 { font-size: 18px; color: #1a1a2e; margin-bottom: 12px; }
        .answer-text { font-size: 15px; line-height: 1.7; color: #333; margin-bottom: 12px; }
        .confidence-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600; background: #e8f5e9; color: #2e7d32; }
        .question-echo { color: #667eea; font-weight: 600; margin-bottom: 16px; font-size: 16px; }
        .chunks-card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
        .chunks-card h2 { font-size: 18px; color: #1a1a2e; margin-bottom: 16px; }
        .chunk-item { padding: 12px 16px; border-left: 3px solid #667eea; background: #f8f9ff; border-radius: 0 8px 8px 0; margin-bottom: 10px; }
        .chunk-item p { font-size: 14px; line-height: 1.6; color: #444; }
        .chunk-meta { font-size: 12px; color: #999; margin-top: 6px; }
    </style>

    <div class="rag-container">

        <div class="rag-header">
            <h1>Quantum RAG Demo</h1>
            <p>Ask questions about the Quantum Framework knowledge base</p>
        </div>

        <!-- Search form (always visible) -->
        <div class="search-card">
            <form method="POST">
                <input type="text" name="question" placeholder="Ask a question..." value="{userQuestion}" />
                <button type="submit" class="btn-ask">Ask</button>
            </form>
        </div>

        <!-- Results (only when hasQuestion was set to 1 by the executor) -->
        <q:if condition="{hasQuestion} == 1">

            <!-- Answer -->
            <div class="answer-card">
                <h2>Answer</h2>
                <div class="question-echo">{userQuestion}</div>
                <div class="answer-text">{answer.answer}</div>
                <span class="confidence-badge">Confidence: {answer.confidence}</span>
            </div>

            <!-- Retrieved chunks -->
            <div class="chunks-card">
                <h2>Retrieved Chunks</h2>
                <q:loop query="searchResults">
                    <div class="chunk-item">
                        <p>{searchResults.content}</p>
                        <div class="chunk-meta">Relevance: {searchResults.relevance} | Source: {searchResults.source}</div>
                    </div>
                </q:loop>
            </div>

        </q:if>

    </div>

</q:component>
