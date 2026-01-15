# 🤖 AI Features in Quantum

Quantum provides three powerful AI features that work together to create intelligent applications.

## Overview

| Feature | Status | Description |
|---------|--------|-------------|
| `q:llm` | ✅ 100% | LLM integration (Ollama local) |
| `q:knowledge` | ✅ 100% | RAG (Retrieval-Augmented Generation) |
| `q:agent` | ✅ 100% | Goal-based AI agents with tools |

---

## 🧠 q:llm - LLM Integration

Connect to local LLMs via Ollama (free & private) or cloud APIs.

### Quick Start

```xml
<!-- Define LLM -->
<q:llm id="assistant" model="llama3" temperature="0.7">
  <default-prompt>You are a helpful AI assistant.</default-prompt>
</q:llm>

<!-- Generate text -->
<q:llm-generate
  llm="assistant"
  prompt="Explain {topic}"
  result="explanation" />

<p>{explanation}</p>
```

### Features
- ✅ Ollama local support (llama3, codellama, mistral)
- ✅ OpenAI/Anthropic optional
- ✅ Response caching
- ✅ Temperature control
- ✅ Databinding in prompts

### Installation

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama3
ollama pull codellama

# Install Python package
pip install ollama
```

### Examples

See: `components/ai_chat.q`, `components/llm_demo.q`

---

## 📚 q:knowledge - RAG System

Create searchable knowledge bases with semantic search.

### Quick Start

```xml
<!-- Define knowledge base -->
<q:knowledge
  id="docs"
  source="./docs/**/*.md"
  embedding="ollama"
  chunk_size="1000" />

<!-- Search -->
<q:search
  knowledge="docs"
  query="{userQuery}"
  result="results"
  top_k="5" />

<!-- Display results -->
<q:loop type="array" array="{results}" item="result">
  <div>
    <p>{result.content}</p>
    <small>Score: {result.score}</small>
  </div>
</q:loop>
```

### Features
- ✅ Document loading (files, URLs, databases)
- ✅ Automatic text chunking
- ✅ Ollama embeddings (nomic-embed-text)
- ✅ ChromaDB vector store
- ✅ Semantic search
- ✅ Metadata filtering

### Installation

```bash
# Pull embedding model
ollama pull nomic-embed-text

# Install dependencies
pip install chromadb
```

### How It Works

1. **Load Documents**: Read from files/URLs/DB
2. **Chunk Text**: Split into smaller pieces with overlap
3. **Generate Embeddings**: Convert text to vectors using Ollama
4. **Store Vectors**: Save in ChromaDB
5. **Semantic Search**: Find similar content by vector similarity

### Examples

See: `components/rag_demo.q`

---

## 🤖 q:agent - AI Agents

Goal-based agents that can reason and use tools.

### Quick Start

```xml
<!-- Define knowledge base -->
<q:knowledge id="docs" source="./docs/*.md" />

<!-- Define LLM -->
<q:llm id="assistant" model="llama3">
  <default-prompt>You are helpful.</default-prompt>
</q:llm>

<!-- Define Agent with tools -->
<q:agent id="helper" llm="assistant" knowledge="docs">
  <goal>Help users find information in documentation</goal>

  <tools>
    <tool name="search" knowledge="docs" top_k="3" />
  </tools>

  <personality>Be friendly and concise</personality>
</q:agent>

<!-- Ask agent -->
<q:agent-ask
  agent="helper"
  question="{userQuestion}"
  result="answer"
  sources="sources"
  show_thinking="true" />

<!-- Display answer -->
<div>
  <h3>Answer:</h3>
  <p>{answer.answer}</p>

  <h3>Sources:</h3>
  <q:loop type="array" array="{answer.sources}" item="source">
    <p>Tool: {source.tool}</p>
    <pre>{source.output}</pre>
  </q:loop>
</div>
```

### Features
- ✅ Goal-based reasoning
- ✅ Tool system (search, function, custom)
- ✅ RAG integration
- ✅ Multi-step reasoning (max 5 iterations)
- ✅ Thinking process tracking
- ✅ Source attribution
- ✅ Memory management

### Architecture

Agents use **ReAct** pattern (Reasoning + Acting):

1. **Understand** the user's question
2. **Reason** about what information is needed
3. **Act** by using tools (search, functions)
4. **Synthesize** final answer from tool outputs

### Agent Flow

```
User Question
     ↓
   Agent Reasoning (LLM)
     ↓
   Decide: Use tool or answer?
     ↓
   ┌─ Use Tool ──────────┐
   │  (RAG search, etc)  │
   │  Get tool output    │
   └──────↓──────────────┘
     Add to context
     ↓
   Reason again
     ↓
   Final Answer
```

### Examples

See: `components/agent_demo.q`

---

## 🎯 Complete Example: Smart Documentation Assistant

Combines all three features:

```xml
<q:component name="SmartDocs">
  <!-- 1. Knowledge Base (RAG) -->
  <q:knowledge
    id="docs"
    source="./docs/**/*.md"
    embedding="ollama"
    chunk_size="500" />

  <!-- 2. LLM -->
  <q:llm id="assistant" model="llama3" temperature="0.7">
    <default-prompt>
      You are a documentation assistant.
      Be accurate and cite sources.
    </default-prompt>
  </q:llm>

  <!-- 3. Agent with RAG Tools -->
  <q:agent id="docs_agent" llm="assistant" knowledge="docs">
    <goal>
      Help users understand documentation by:
      1. Searching relevant docs
      2. Synthesizing clear answers
      3. Providing source citations
    </goal>

    <tools>
      <tool name="search" knowledge="docs" top_k="3" />
    </tools>
  </q:agent>

  <!-- 4. User Interface -->
  <form method="GET">
    <input type="text" name="q" placeholder="Ask anything..." />
    <button type="submit">Ask</button>
  </form>

  <q:if condition="{query.q}">
    <q:agent-ask
      agent="docs_agent"
      question="{query.q}"
      result="answer"
      show_thinking="true" />

    <div class="answer">
      {answer.answer}
    </div>

    <div class="sources">
      <h4>Sources:</h4>
      <q:loop type="array" array="{answer.sources}" item="src">
        <p>{src.output}</p>
      </q:loop>
    </div>
  </q:if>
</q:component>
```

**Result**: A ChatGPT-like interface for your own documentation! 🎉

---

## 🔧 Setup Guide

### 1. Install Ollama

```bash
# macOS / Linux
curl https://ollama.ai/install.sh | sh

# Or visit https://ollama.ai
```

### 2. Pull Models

```bash
# LLM models
ollama pull llama3          # General purpose
ollama pull codellama       # Code generation
ollama pull mistral         # Alternative

# Embedding model (for RAG)
ollama pull nomic-embed-text
```

### 3. Install Python Dependencies

```bash
pip install ollama chromadb
```

### 4. Start Quantum

```bash
python quantum.py start
```

### 5. Test

Visit:
- `http://localhost:8080/ai_chat` - LLM chat
- `http://localhost:8080/rag_demo` - RAG search
- `http://localhost:8080/agent_demo` - AI agent

---

## 📊 Performance

| Operation | Time | Notes |
|-----------|------|-------|
| LLM Generation (llama3) | ~2-5s | Local, depends on hardware |
| Embedding (nomic-embed) | ~100ms | Per chunk |
| Vector Search | ~50ms | ChromaDB lookup |
| Agent Reasoning | ~3-10s | Multiple LLM calls + tools |

**Tip**: Use caching to speed up repeated queries!

---

## 🎨 Use Cases

### Documentation Assistant
- Knowledge: Your docs
- Agent: Answers questions with citations
- Example: `agent_demo.q`

### Customer Support Bot
- Knowledge: FAQs + past tickets
- Agent: Resolves issues, creates tickets
- Tools: Search FAQs, create ticket, check order

### Code Review Agent
- Knowledge: Style guide, best practices
- Agent: Reviews code for issues
- Tools: Check style, analyze security

### Research Assistant
- Knowledge: Research papers
- Agent: Summarizes papers, finds connections
- Tools: Search papers, summarize, compare

---

## 💡 Best Practices

### LLM
1. **Use local models** (Ollama) for privacy
2. **Cache responses** for repeated queries
3. **Set temperature** - lower for facts, higher for creativity
4. **Limit tokens** to control response length

### RAG
1. **Chunk wisely** - 500-1000 chars usually works
2. **Use overlap** - 100-200 chars overlap helps
3. **Update regularly** - Set `auto_update="true"`
4. **Filter metadata** - Add metadata for better filtering

### Agents
1. **Clear goals** - Specific goals work better
2. **Limit iterations** - Prevent infinite loops (max 5)
3. **Good tools** - Provide necessary tools only
4. **Show thinking** - Debug with `show_thinking="true"`

---

## 🚀 Next Steps

1. **Try the demos**:
   - `http://localhost:8080/llm_demo`
   - `http://localhost:8080/rag_demo`
   - `http://localhost:8080/agent_demo`

2. **Create your own**:
   - Add your documents to `docs/`
   - Define knowledge base
   - Create agent with tools
   - Build UI

3. **Customize**:
   - Try different models (mistral, codellama)
   - Adjust chunk size/temperature
   - Add custom tools (functions, APIs)

---

## 📚 Documentation

- [q:llm README](src/core/features/llm/README.md)
- [q:knowledge README](src/core/features/rag/README.md)
- [Example Components](components/)

---

## ✨ Why This Is Unique

### vs LangChain
- **Simpler**: 3 XML tags vs 50+ Python lines
- **Local**: No API costs, complete privacy
- **Integrated**: Works with Quantum's existing features

### vs Custom RAG
- **Zero config**: Automatic chunking, embeddings, vector DB
- **Declarative**: XML-based, not imperative code
- **Batteries included**: LLM + RAG + Agents in one framework

### vs ChatGPT
- **Your data**: Use your own documents
- **Customizable**: Full control over prompts, models, tools
- **Free**: No API costs, runs locally

---

**Status**: ✅ All three features fully implemented and ready to use!

**Powered by**: Ollama (LLM + Embeddings) + ChromaDB (Vector Store)
