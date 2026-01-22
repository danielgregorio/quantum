# Quantum Language

::: tip 🧠 Codename: FF / FireFusion
⚡ **Status:** Core features + AI/RAG implemented - Production ready!
:::

## What is Quantum?

Quantum is an experimental declarative language that allows you to write components, web applications, and jobs using clean XML syntax. Think of it as a bridge between configuration and programming - write once, deploy anywhere!

## ✨ Key Features

- 🔄 **Loop Structures** - Range, Array, and List loops with full databinding
- 🔗 **Variable Databinding** - Dynamic `{variable}` substitution with expressions
- 🧩 **Component System** - Reusable, modular components
- 🌐 **Web Applications** - HTML and API applications
- 🤖 **AI Integration** - Built-in LLM support (Ollama, OpenAI, Claude)
- 📚 **RAG (Retrieval-Augmented Generation)** - Semantic search + AI answers
- 🎯 **Unified Query Syntax** - One syntax for SQL, LLM, RAG, and more
- ⚡ **Simple Syntax** - XML-based, easy to learn

## 🚀 Quick Example

```xml
<!-- AI-powered documentation search with RAG -->
<q:component name="DocSearch">
  <!-- 1. Search knowledge base (semantic search) -->
  <q:query name="docs" datasource="knowledge_base" top_k="3">
    {query.q}
  </q:query>

  <!-- 2. Ask AI with context -->
  <q:query name="answer" datasource="ai">
    Based on: {docs.results}
    Question: {query.q}
  </q:query>

  <!-- 3. Display results -->
  <div class="answer">{answer}</div>
</q:component>
```

**What's happening?**
- Same `<q:query>` syntax for both semantic search and AI
- RAG pipeline in just 3 queries
- Everything is a datasource: SQL, LLM, Knowledge Bases, APIs!

## 🎯 Philosophy

**Simplicity over configuration** - Quantum prioritizes readability and ease of use while maintaining powerful capabilities for complex scenarios.

## 📚 Get Started

<div class="vp-feature-grid">
  <div class="vp-feature">
    <div class="vp-feature-icon">📖</div>
    <h3><a href="/guide/getting-started">Getting Started</a></h3>
    <p>Learn the basics and run your first Quantum component</p>
  </div>

  <div class="vp-feature">
    <div class="vp-feature-icon">🎯</div>
    <h3><a href="/UNIFIED_QUERY_GUIDE">Unified Query Syntax</a></h3>
    <p>Master the new unified syntax for SQL, LLM, RAG, and APIs</p>
  </div>

  <div class="vp-feature">
    <div class="vp-feature-icon">🤖</div>
    <h3><a href="/guide/ai-integration">AI & RAG</a></h3>
    <p>Build AI-powered apps with LLM and semantic search</p>
  </div>

  <div class="vp-feature">
    <div class="vp-feature-icon">🔄</div>
    <h3><a href="/guide/loops">Loops</a></h3>
    <p>Master Range, Array, and List loops with databinding</p>
  </div>

  <div class="vp-feature">
    <div class="vp-feature-icon">🌐</div>
    <h3><a href="/examples/web-applications">Web Apps</a></h3>
    <p>Build HTML and API applications with ease</p>
  </div>
</div>

## 🏆 Current Status

- ✅ **Component System** - Fully functional
- ✅ **Loop Structures** - Range, Array, List loops implemented
- ✅ **Variable Databinding** - `{variable}` and expressions working
- ✅ **Conditional Logic** - `q:if`, `q:else`, `q:elseif` supported
- ✅ **Web & API Servers** - Basic HTTP applications
- ✅ **State Management** - `q:set` with operations (add, subtract, multiply, divide)
- ✅ **Unified Query Syntax** - SQL, LLM, RAG, APIs with same syntax
- ✅ **LLM Integration** - Ollama, OpenAI, Anthropic support
- ✅ **RAG System** - Semantic search with ChromaDB + embeddings
- ✅ **AI Agents** - Goal-based agents with tools
- ✅ **Functions** - Reusable functions with params, caching, REST API (`q:function`)
- ✅ **Function Calls** - Invoke functions with `q:call`
- ✅ **REST API Auto-Gen** - Auto-generate Flask/FastAPI + OpenAPI from functions
- ✅ **Event System** - Event handlers and dispatch (`q:on`, `q:dispatch`)
- 🚧 **Advanced Agent Tools** - Coming next
- 🚧 **Real-time Features** - WebSocket support planned

---

*Built with ❤️ using Python and powered by a clean AST-based architecture.*