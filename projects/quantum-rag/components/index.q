<q:component name="RAGDemo">

    <!-- Initialize state -->
    <q:set name="hasQuestion" value="0" />
    <q:set name="userQuestion" value="" />
    <q:set name="answerText" value="" />

    <!-- Process form submission -->
    <q:if condition="{form.question}">
        <q:set name="hasQuestion" value="1" />
        <q:set name="userQuestion" value="{form.question}" />

        <!-- Direct LLM query about Quantum Framework -->
        <q:llm name="ragAnswer" model="phi3" timeout="120" maxTokens="200">
            <q:message role="system">You answer questions about Quantum Framework in 2-3 sentences max. Quantum is an XML web framework using .q files. Key tags: q:set, q:if, q:loop, q:query, q:function, q:action, q:file, q:mail, q:llm, q:knowledge. Databinding uses curly braces like {variable}. Be extremely concise.</q:message>
            <q:message role="user">{userQuestion}</q:message>
        </q:llm>

        <q:set name="answerText" value="{ragAnswer}" />
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
        .suggestions { margin-bottom: 24px; }
        .suggestions p { font-size: 13px; color: #888; margin-bottom: 8px; }
        .suggestion-chips { display: flex; flex-wrap: wrap; gap: 8px; }
        .suggestion-chip { padding: 6px 14px; background: white; border: 1px solid #e0e0e0; border-radius: 20px; font-size: 13px; color: #555; cursor: pointer; text-decoration: none; font-family: inherit; }
        .suggestion-chip:hover { border-color: #667eea; color: #667eea; background: #f8f7ff; }
        .answer-card { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 24px; }
        .answer-card h2 { font-size: 18px; color: #1a1a2e; margin-bottom: 12px; }
        .answer-text { font-size: 15px; line-height: 1.7; color: #333; white-space: pre-wrap; }
        .question-echo { color: #667eea; font-weight: 600; margin-bottom: 16px; font-size: 16px; }
        .loading-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.8); z-index: 1000; justify-content: center; align-items: center; }
        .loading-overlay.active { display: flex; }
        .loading-spinner { text-align: center; }
        .loading-spinner .dots { font-size: 32px; color: #667eea; }
        .loading-spinner p { margin-top: 12px; color: #666; font-size: 15px; }
    </style>

    <!-- Loading overlay -->
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-spinner">
            <div class="dots">...</div>
            <p>Thinking...</p>
        </div>
    </div>

    <div class="rag-container">

        <div class="rag-header">
            <h1>Quantum RAG Demo</h1>
            <p>Ask anything about the Quantum Framework - features, tags, syntax, and more</p>
        </div>

        <!-- Search form -->
        <div class="search-card">
            <form method="POST" action="./" id="ragForm">
                <input type="text" name="question" id="questionInput" placeholder="Ask a question..." value="{userQuestion}" />
                <button type="submit" class="btn-ask">Ask</button>
            </form>
        </div>

        <!-- Suggestion chips (only on GET, before any question) -->
        <q:if condition="{hasQuestion} == 0">
            <div class="suggestions">
                <p>Try asking:</p>
                <div class="suggestion-chips">
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="What features does Quantum have?" /><button type="submit" class="suggestion-chip">What features does Quantum have?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How do I query a database?" /><button type="submit" class="suggestion-chip">How do I query a database?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How does authentication work?" /><button type="submit" class="suggestion-chip">How does authentication work?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How do I use LLM in Quantum?" /><button type="submit" class="suggestion-chip">How do I use LLM in Quantum?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="What loop types are available?" /><button type="submit" class="suggestion-chip">What loop types are available?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How do I deploy a Quantum app?" /><button type="submit" class="suggestion-chip">How do I deploy a Quantum app?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How do I create variables with q:set?" /><button type="submit" class="suggestion-chip">How do I create variables with q:set?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How do conditionals work?" /><button type="submit" class="suggestion-chip">How do conditionals work?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How do I define functions?" /><button type="submit" class="suggestion-chip">How do I define functions?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How do I handle file uploads?" /><button type="submit" class="suggestion-chip">How do I handle file uploads?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How does session management work?" /><button type="submit" class="suggestion-chip">How does session management work?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How do I send emails with q:mail?" /><button type="submit" class="suggestion-chip">How do I send emails with q:mail?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How do I call external APIs?" /><button type="submit" class="suggestion-chip">How do I call external APIs?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How do I build a game with Quantum?" /><button type="submit" class="suggestion-chip">How do I build a game with Quantum?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="What is a RAG knowledge base?" /><button type="submit" class="suggestion-chip">What is a RAG knowledge base?</button></form>
                    <form method="POST" action="./" style="display:inline"><input type="hidden" name="question" value="How does databinding work?" /><button type="submit" class="suggestion-chip">How does databinding work?</button></form>
                </div>
            </div>
        </q:if>

        <!-- Results -->
        <q:if condition="{hasQuestion} == 1">

            <div class="answer-card">
                <h2>Answer</h2>
                <div class="question-echo">{userQuestion}</div>
                <div class="answer-text">{answerText}</div>
            </div>

        </q:if>

    </div>

    <script>
        // Ensure trailing slash in URL to prevent 301 redirect on POST
        if (!window.location.pathname.endsWith('/')) {
            window.history.replaceState(null, '', window.location.pathname + '/' + window.location.search);
        }
        // Show loading overlay on form submit
        document.querySelectorAll('form').forEach(function(f) {
            f.addEventListener('submit', function() {
                document.getElementById('loadingOverlay').classList.add('active');
            });
        });
    </script>

</q:component>
