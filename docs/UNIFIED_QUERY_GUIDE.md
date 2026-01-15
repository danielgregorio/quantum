# Unified Query Syntax Guide

## Overview

Quantum's **Unified Query Syntax** treats all data sources uniformly. Whether you're querying a SQL database, an LLM, a knowledge base, or an external API, you use the same `<q:query>` tag.

**Philosophy**: Everything is a datasource!

## Table of Contents

- [Quick Start](#quick-start)
- [Defining Datasources](#defining-datasources)
- [Using Queries](#using-queries)
- [Datasource Types](#datasource-types)
- [Migration Guide](#migration-guide)
- [Best Practices](#best-practices)
- [Examples](#examples)

## Quick Start

### 1. Define datasources in `Application.q`

```xml
<q:application id="myapp" type="html">
  <!-- SQL Database -->
  <datasource id="db" type="postgres"
    host="localhost"
    database="mydb" />

  <!-- LLM (AI) -->
  <datasource id="ai" type="llm"
    provider="ollama"
    model="llama3">
    <system-prompt>You are helpful</system-prompt>
  </datasource>

  <!-- Knowledge Base (RAG) -->
  <datasource id="docs" type="knowledge"
    source="./docs/**/*.md"
    embedding="ollama" />
</q:application>
```

### 2. Use queries in components

```xml
<q:component name="MyComponent">
  <!-- Query SQL database -->
  <q:query name="users" datasource="db">
    SELECT * FROM users WHERE active = true
  </q:query>

  <!-- Query LLM -->
  <q:query name="answer" datasource="ai">
    Explain quantum computing
  </q:query>

  <!-- Query knowledge base -->
  <q:query name="results" datasource="docs">
    authentication
  </q:query>
</q:component>
```

## Defining Datasources

All datasources are defined in `Application.q` using the `<datasource>` tag.

### Common Attributes

All datasources require:
- `id` - Unique identifier
- `type` - Datasource type (postgres, mysql, llm, knowledge, redis, rest, etc.)

### SQL Databases

#### PostgreSQL

```xml
<datasource id="db" type="postgres"
  host="localhost"
  port="5432"
  database="quantum_db"
  username="quantum_user"
  password="${DB_PASSWORD}" />
```

#### MySQL

```xml
<datasource id="mysql" type="mysql"
  host="localhost"
  port="3306"
  database="myapp"
  username="root"
  password="${MYSQL_PASSWORD}" />
```

#### SQLite

```xml
<datasource id="sqlite" type="sqlite"
  database="./data/app.db" />
```

### LLM (Language Models)

#### Ollama (Local)

```xml
<datasource id="ai" type="llm"
  provider="ollama"
  model="llama3"
  temperature="0.7"
  max_tokens="500">
  <system-prompt>
    You are a helpful AI assistant for the Quantum framework.
    Provide clear, concise answers.
  </system-prompt>
</datasource>
```

**Available Ollama Models**:
- `llama3` - General purpose
- `codellama:13b` - Code generation
- `mistral` - Fast responses
- `mixtral` - High quality
- `phi3` - Lightweight

#### OpenAI

```xml
<datasource id="gpt4" type="llm"
  provider="openai"
  model="gpt-4"
  temperature="0.8"
  api_key="${OPENAI_API_KEY}">
  <system-prompt>You are an expert software architect.</system-prompt>
</datasource>
```

#### Anthropic Claude

```xml
<datasource id="claude" type="llm"
  provider="anthropic"
  model="claude-3-opus-20240229"
  temperature="0.7"
  api_key="${ANTHROPIC_API_KEY}">
  <system-prompt>You are a helpful assistant.</system-prompt>
</datasource>
```

### Knowledge Bases (RAG)

```xml
<datasource id="knowledge_base" type="knowledge"
  source="./docs/**/*.md"
  embedding="ollama"
  embedding_model="nomic-embed-text"
  chunk_size="500"
  chunk_overlap="100"
  vector_db="chromadb"
  collection="quantum_docs" />
```

**Attributes**:
- `source` - File pattern or directory (supports globs)
- `embedding` - Embedding provider (ollama, openai)
- `embedding_model` - Model for embeddings (default: nomic-embed-text)
- `chunk_size` - Text chunk size (default: 500)
- `chunk_overlap` - Overlap between chunks (default: 100)
- `vector_db` - Vector database (chromadb, pinecone, weaviate)
- `collection` - Collection name in vector DB

**Source Types**:
- Files: `./docs/**/*.md`, `./docs/*.pdf`
- URLs: `https://example.com/docs`
- Databases: `db://docs_table`
- APIs: `api://confluence/spaces/DOCS`

### Cache Stores

#### Redis

```xml
<datasource id="cache" type="redis"
  host="localhost"
  port="6379"
  password="${REDIS_PASSWORD}" />
```

### External APIs

#### REST API

```xml
<datasource id="github" type="rest"
  base_url="https://api.github.com"
  auth_type="token"
  auth_token="${GITHUB_TOKEN}" />
```

#### GraphQL API

```xml
<datasource id="graphql_api" type="graphql"
  base_url="https://api.example.com/graphql"
  auth_type="bearer"
  auth_token="${API_TOKEN}" />
```

## Using Queries

The `<q:query>` tag works with any datasource type. The parser automatically detects the datasource type and generates the appropriate code.

### Basic Query

```xml
<q:query name="result_variable" datasource="datasource_id">
  query content
</q:query>
```

### SQL Database Queries

```xml
<q:query name="users" datasource="db">
  SELECT id, name, email FROM users WHERE active = true
</q:query>

<q:loop type="query" query="users" item="user">
  <p>{user.name} - {user.email}</p>
</q:loop>
```

**Access results**:
- `{users.recordCount}` - Number of records
- `{users.records}` - Array of records

### LLM Queries

```xml
<q:query name="answer" datasource="ai">
  Explain {topic} in simple terms for beginners
</q:query>

<div class="answer">
  {answer}
</div>
```

**LLM-specific attributes**:
- `cache="true"` - Cache LLM responses
- `stream="true"` - Stream responses (for real-time display)

```xml
<q:query name="explanation" datasource="ai" cache="true" stream="true">
  Write a detailed explanation of {concept}
</q:query>
```

### Knowledge Base Queries (RAG)

```xml
<q:query name="results" datasource="knowledge_base" top_k="5">
  {search_term}
</q:query>

<div>
  <h3>Found {results.count} relevant documents</h3>
  <q:loop type="array" array="{results.results}" item="doc">
    <div class="result">
      <span class="score">Score: {doc.score}</span>
      <p>{doc.content}</p>
      <small>Source: {doc.metadata.source}</small>
    </div>
  </q:loop>
</div>
```

**RAG-specific attributes**:
- `top_k="5"` - Number of results to return (default: 5)
- `min_score="0.7"` - Minimum similarity score (0.0-1.0)

**Result format**:
```javascript
{
  count: 5,
  results: [
    {
      score: 0.92,
      content: "Text chunk content...",
      metadata: {
        source: "./docs/auth.md",
        chunk_id: "auth-001",
        created_at: "2024-01-15"
      }
    }
  ]
}
```

### Cache Queries

```xml
<!-- Get from cache -->
<q:query name="cached_data" datasource="cache">
  GET user:{user_id}:profile
</q:query>

<!-- Set in cache -->
<q:query name="cache_result" datasource="cache">
  SET user:{user_id}:profile "{profile_json}" EX 3600
</q:query>
```

## Datasource Types

### Summary Table

| Type | Use Case | Query Content | Returns |
|------|----------|---------------|---------|
| `postgres`, `mysql`, `sqlite` | SQL databases | SQL statements | Records array |
| `llm` | AI text generation | Natural language prompt | Generated text |
| `knowledge` | RAG semantic search | Search query | Relevant chunks |
| `redis` | Cache operations | Redis commands | Cache values |
| `rest` | HTTP APIs | REST endpoint | API response |
| `graphql` | GraphQL APIs | GraphQL query | Query result |

## Migration Guide

### Old Syntax → New Syntax

#### LLM Migration

**Old**:
```xml
<!-- Define LLM -->
<q:llm id="ai" model="llama3" provider="ollama" temperature="0.7">
  <default-prompt>You are helpful</default-prompt>
</q:llm>

<!-- Generate -->
<q:llm-generate llm="ai" prompt="Explain {topic}" result="answer" />
```

**New**:
```xml
<!-- Define in Application.q -->
<datasource id="ai" type="llm"
  provider="ollama"
  model="llama3"
  temperature="0.7">
  <system-prompt>You are helpful</system-prompt>
</datasource>

<!-- Use in component -->
<q:query name="answer" datasource="ai">
  Explain {topic}
</q:query>
```

#### RAG Migration

**Old**:
```xml
<!-- Define knowledge base -->
<q:knowledge id="docs" source="./docs/*.md" embedding="ollama" />

<!-- Search -->
<q:search knowledge="docs" query="{term}" result="results" top_k="5" />
```

**New**:
```xml
<!-- Define in Application.q -->
<datasource id="docs" type="knowledge"
  source="./docs/*.md"
  embedding="ollama" />

<!-- Use in component -->
<q:query name="results" datasource="docs" top_k="5">
  {term}
</q:query>
```

#### Agent Migration

**Old**:
```xml
<!-- Define agent -->
<q:agent id="helper" llm="ai">
  <goal>Help users with Quantum</goal>
  <tool name="search_docs" knowledge="docs" />
</q:agent>

<!-- Ask -->
<q:agent-ask agent="helper" query="{question}" result="response" />
```

**New**:
```xml
<!-- Define in Application.q -->
<datasource id="helper" type="agent"
  llm="ai">
  <goal>Help users with Quantum</goal>
  <tool name="search_docs" knowledge="docs" />
</datasource>

<!-- Use in component -->
<q:query name="response" datasource="helper">
  {question}
</q:query>
```

### Backward Compatibility

Both syntaxes work! You can mix old and new syntax in the same application:

```xml
<q:component name="MixedSyntax">
  <!-- Old syntax still works -->
  <q:llm id="local" model="codellama" />
  <q:llm-generate llm="local" prompt="Write code" result="code" />

  <!-- New unified syntax -->
  <q:query name="explanation" datasource="ai">
    Explain this code
  </q:query>
</q:component>
```

## Best Practices

### 1. Define Datasources Globally

Define all datasources in `Application.q`, not in individual components. This makes them reusable and easier to configure.

**Good**:
```xml
<!-- Application.q -->
<datasource id="ai" type="llm" model="llama3" />

<!-- component1.q -->
<q:query name="answer1" datasource="ai">prompt 1</q:query>

<!-- component2.q -->
<q:query name="answer2" datasource="ai">prompt 2</q:query>
```

**Bad**:
```xml
<!-- component.q -->
<q:llm id="ai" model="llama3" />
<q:llm-generate llm="ai" prompt="..." result="answer" />
```

### 2. Use Environment Variables for Secrets

```xml
<datasource id="db" type="postgres"
  password="${DB_PASSWORD}" />

<datasource id="gpt4" type="llm"
  api_key="${OPENAI_API_KEY}" />
```

### 3. Descriptive Datasource IDs

Use clear, descriptive IDs:

**Good**: `ai`, `db`, `knowledge_base`, `cache`, `github_api`

**Bad**: `ds1`, `x`, `temp`, `thing`

### 4. Separate Concerns

Create different datasources for different purposes:

```xml
<datasource id="ai" type="llm" model="llama3">
  <system-prompt>You are a helpful assistant</system-prompt>
</datasource>

<datasource id="codegen" type="llm" model="codellama">
  <system-prompt>You are a code generation expert</system-prompt>
</datasource>

<datasource id="translator" type="llm" model="llama3">
  <system-prompt>You are a translator</system-prompt>
</datasource>
```

### 5. Cache LLM Responses When Appropriate

For static content or frequently asked questions:

```xml
<q:query name="faq_answer" datasource="ai" cache="true">
  What is Quantum?
</q:query>
```

### 6. Set Appropriate top_k for RAG

- Small `top_k` (1-3): Precise, focused results
- Medium `top_k` (5-10): Balanced coverage
- Large `top_k` (20+): Comprehensive context

### 7. Use min_score to Filter Low-Quality Results

```xml
<q:query name="high_quality" datasource="docs" top_k="10" min_score="0.7">
  authentication best practices
</q:query>
```

## Examples

### Example 1: Simple AI Chat

```xml
<q:component name="SimpleChat">
  <q:if condition="{query.message}">
    <q:query name="response" datasource="ai">
      {query.message}
    </q:query>

    <div class="chat">
      <div class="user-message">{query.message}</div>
      <div class="ai-message">{response}</div>
    </div>
  </q:if>

  <form method="GET">
    <input type="text" name="message" placeholder="Ask anything..." />
    <button type="submit">Send</button>
  </form>
</q:component>
```

### Example 2: RAG-Powered Documentation Search

```xml
<q:component name="DocSearch">
  <q:if condition="{query.q}">
    <!-- Search docs -->
    <q:query name="docs" datasource="knowledge_base" top_k="3">
      {query.q}
    </q:query>

    <!-- Build context -->
    <q:set name="context" value="" />
    <q:loop type="array" array="{docs.results}" item="doc">
      <q:set name="context" operation="add" value="{context}\n\n{doc.content}" />
    </q:loop>

    <!-- Ask AI with context -->
    <q:query name="answer" datasource="ai">
      Context from documentation:
      {context}

      User question: {query.q}

      Based ONLY on the context, provide a helpful answer.
    </q:query>

    <div class="answer">
      <h3>Answer:</h3>
      <p>{answer}</p>

      <details>
        <summary>Sources ({docs.count})</summary>
        <q:loop type="array" array="{docs.results}" item="src">
          <div class="source">
            <span>Score: {src.score}</span>
            <p>{src.content}</p>
          </div>
        </q:loop>
      </details>
    </div>
  </q:if>
</q:component>
```

### Example 3: Multi-Datasource Dashboard

```xml
<q:component name="Dashboard">
  <!-- SQL: Get user stats -->
  <q:query name="stats" datasource="db">
    SELECT COUNT(*) as total,
           COUNT(CASE WHEN active THEN 1 END) as active
    FROM users
  </q:query>

  <!-- Cache: Get cached metrics -->
  <q:query name="metrics" datasource="cache">
    GET dashboard:metrics
  </q:query>

  <!-- AI: Generate insights -->
  <q:query name="insights" datasource="ai" cache="true">
    Based on these metrics:
    - Total users: {stats.records[0].total}
    - Active users: {stats.records[0].active}

    Provide 3 key insights about user engagement.
  </q:query>

  <div class="dashboard">
    <div class="stats">
      <h2>User Stats</h2>
      <p>Total: {stats.records[0].total}</p>
      <p>Active: {stats.records[0].active}</p>
    </div>

    <div class="insights">
      <h2>AI Insights</h2>
      <p>{insights}</p>
    </div>
  </div>
</q:component>
```

### Example 4: Code Generation with Context

```xml
<q:component name="CodeGen">
  <q:if condition="{query.task}">
    <!-- Search code examples -->
    <q:query name="examples" datasource="code_examples" top_k="2">
      {query.task}
    </q:query>

    <!-- Generate code with examples as context -->
    <q:query name="code" datasource="codegen">
      Here are similar examples:
      <q:loop type="array" array="{examples.results}" item="ex">

      Example:
      {ex.content}
      </q:loop>

      Now generate code for: {query.task}
    </q:query>

    <div class="code-result">
      <h3>Generated Code:</h3>
      <pre><code>{code}</code></pre>
    </div>
  </q:if>
</q:component>
```

## Advanced Features

### Streaming LLM Responses

```xml
<q:query name="story" datasource="ai" stream="true">
  Write a short story about a quantum computer
</q:query>

<div class="streaming-content" data-stream="{story.stream_id}">
  {story}
</div>
```

### Reactive Queries

Automatically re-run queries when dependencies change:

```xml
<q:query name="search_results" datasource="docs"
         reactive="true" depends="{searchTerm}">
  {searchTerm}
</q:query>
```

### Query Composition

Build complex queries by composing results:

```xml
<!-- Step 1: Search -->
<q:query name="relevant_docs" datasource="knowledge_base">
  {topic}
</q:query>

<!-- Step 2: Analyze with AI -->
<q:query name="summary" datasource="ai">
  Summarize these documents:
  <q:loop type="array" array="{relevant_docs.results}" item="doc">
  - {doc.content}
  </q:loop>
</q:query>

<!-- Step 3: Translate -->
<q:query name="translated" datasource="translator">
  Translate to {target_lang}:
  {summary}
</q:query>
```

## Troubleshooting

### Query Returns Empty Results

**Check**:
1. Datasource is defined in `Application.q`
2. Datasource ID matches exactly
3. For RAG: Knowledge base has been indexed
4. For LLM: Model is running (Ollama) or API key is valid

### LLM Not Responding

**Check**:
1. Ollama is running: `ollama list`
2. Model is pulled: `ollama pull llama3`
3. Temperature/max_tokens are reasonable
4. System prompt is not too restrictive

### RAG Returns Low-Quality Results

**Solutions**:
1. Increase `chunk_size` for more context
2. Adjust `chunk_overlap` for better continuity
3. Use `min_score` to filter low-confidence results
4. Ensure embedding model matches (nomic-embed-text recommended)
5. Re-index knowledge base if documents changed

## Next Steps

- [Complete API Reference](./API_REFERENCE.md)
- [LLM Feature Guide](./LLM_GUIDE.md)
- [RAG Feature Guide](./RAG_GUIDE.md)
- [Agent Feature Guide](./AGENT_GUIDE.md)
- [Example Gallery](../examples/)

---

**Questions?** Open an issue or check the [FAQ](./FAQ.md)
