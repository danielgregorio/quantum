<q:application id="quantum_app" type="html" xmlns:q="https://quantum.lang/ns">
  <!--
    QUANTUM APPLICATION CONFIGURATION

    This file defines global datasources that can be used across all components.

    NEW FEATURE: Unified Datasource System
    All data sources (SQL, LLM, RAG, Cache, APIs) are defined here with same pattern!
  -->

  <!-- ============================================ -->
  <!-- SQL DATABASES -->
  <!-- ============================================ -->

  <!-- PostgreSQL Database -->
  <datasource id="db" type="postgres"
    host="localhost"
    port="5432"
    database="quantum_db"
    username="quantum_user"
    password="${DB_PASSWORD}" />

  <!-- MySQL Database -->
  <datasource id="mysql" type="mysql"
    host="localhost"
    database="myapp"
    username="root"
    password="${MYSQL_PASSWORD}" />

  <!-- SQLite (file-based) -->
  <datasource id="sqlite" type="sqlite"
    database="./data/app.db" />

  <!-- ============================================ -->
  <!-- CACHE / KEY-VALUE STORES -->
  <!-- ============================================ -->

  <!-- Redis Cache -->
  <datasource id="cache" type="redis"
    host="localhost"
    port="6379" />

  <!-- ============================================ -->
  <!-- AI / LLM DATASOURCES -->
  <!-- ============================================ -->

  <!-- Ollama (Local LLM) -->
  <datasource id="ai" type="llm"
    provider="ollama"
    model="llama3"
    temperature="0.7"
    max_tokens="500">
    <system-prompt>You are a helpful AI assistant for the Quantum framework. Provide clear, concise answers.</system-prompt>
  </datasource>

  <!-- Code Generation LLM -->
  <datasource id="codegen" type="llm"
    provider="ollama"
    model="codellama:13b"
    temperature="0.3">
    <system-prompt>You are a code generation assistant. Write clean, efficient code with comments.</system-prompt>
  </datasource>

  <!-- OpenAI GPT-4 (if api_key provided) -->
  <datasource id="gpt4" type="llm"
    provider="openai"
    model="gpt-4"
    temperature="0.8"
    api_key="${OPENAI_API_KEY}">
    <system-prompt>You are an expert software architect.</system-prompt>
  </datasource>

  <!-- ============================================ -->
  <!-- KNOWLEDGE BASES / RAG -->
  <!-- ============================================ -->

  <!-- Documentation Knowledge Base -->
  <datasource id="knowledge_base" type="knowledge"
    source="./docs/**/*.md"
    embedding="ollama"
    embedding_model="nomic-embed-text"
    chunk_size="500"
    chunk_overlap="100"
    vector_db="chromadb"
    collection="quantum_docs" />

  <!-- API Documentation -->
  <datasource id="api_docs" type="knowledge"
    source="./docs/api/**/*.md"
    embedding="ollama"
    chunk_size="600"
    vector_db="chromadb" />

  <!-- Code Examples Knowledge Base -->
  <datasource id="code_examples" type="knowledge"
    source="./examples/**/*.q"
    embedding="ollama"
    chunk_size="800"
    vector_db="chromadb" />

  <!-- ============================================ -->
  <!-- EXTERNAL APIs (future) -->
  <!-- ============================================ -->

  <!-- REST API Example -->
  <datasource id="github" type="rest"
    base_url="https://api.github.com"
    auth_type="token"
    auth_token="${GITHUB_TOKEN}" />

  <!-- GraphQL API Example -->
  <datasource id="graphql_api" type="graphql"
    base_url="https://api.example.com/graphql" />

  <!-- ============================================ -->
  <!-- ROUTES -->
  <!-- ============================================ -->

  <q:route path="/" method="GET">
    <q:return name="index" type="component" value="Home" />
  </q:route>

  <q:route path="/demo" method="GET">
    <q:return name="demo" type="component" value="UnifiedQueryDemo" />
  </q:route>

  <q:route path="/ai-chat" method="GET">
    <q:return name="chat" type="component" value="ai_chat" />
  </q:route>

  <q:route path="/rag-demo" method="GET">
    <q:return name="rag" type="component" value="rag_demo" />
  </q:route>

  <q:route path="/agent-demo" method="GET">
    <q:return name="agent" type="component" value="agent_demo" />
  </q:route>
</q:application>
