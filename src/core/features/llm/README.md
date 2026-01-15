# LLM Feature - AI Integration with Ollama

## Overview

The LLM feature provides native AI integration in Quantum using local LLMs via Ollama. No API keys, no costs, complete privacy.

## Features

- **Local AI** - Runs on your machine with Ollama
- **Multiple Models** - Support for Llama 3, CodeLlama, Mistral, and more
- **Zero Cost** - Completely free, no API fees
- **Privacy First** - Your data never leaves your machine
- **Caching** - Built-in response caching for performance
- **Streaming** - Real-time response streaming for chat interfaces

## Installation

### 1. Install Ollama

```bash
# macOS / Linux
curl https://ollama.ai/install.sh | sh

# Or visit https://ollama.ai for other platforms
```

### 2. Pull Models

```bash
# General purpose
ollama pull llama3

# Code generation
ollama pull codellama:7b

# Other models
ollama pull mistral
ollama pull mixtral
```

### 3. Verify Installation

```bash
ollama list
```

## Usage

### 1. Define LLM Configuration

```xml
<q:llm id="assistant" model="llama3" provider="ollama" temperature="0.7">
  <default-prompt>You are a helpful AI assistant.</default-prompt>
</q:llm>

<q:llm id="coder" model="codellama:7b" temperature="0.2">
  <default-prompt>You are an expert programmer.</default-prompt>
</q:llm>
```

**Attributes:**
- `id` - Unique identifier (required)
- `model` - Model name (required)
- `provider` - Provider name ("ollama", "openai", "anthropic") - default: "ollama"
- `temperature` - Creativity (0.0-1.0) - default: 0.7
- `max_tokens` - Max tokens to generate (optional)

### 2. Generate Text

```xml
<q:llm-generate
  llm="assistant"
  prompt="Explain quantum computing in one sentence"
  result="explanation" />

<p>{explanation}</p>
```

**With Databinding:**

```xml
<q:set name="topic" value="machine learning" />

<q:llm-generate
  llm="assistant"
  prompt="Explain {topic} simply"
  result="answer" />

<p>{answer}</p>
```

**With Caching:**

```xml
<q:llm-generate
  llm="assistant"
  prompt="What is AI?"
  result="answer"
  cache="true" />
```

### 3. Code Generation

```xml
<q:llm-generate
  llm="coder"
  prompt="Write a Python function to calculate fibonacci"
  result="code" />

<pre><code>{code}</code></pre>
```

### 4. Chat Interface

```xml
<q:component name="Chat">
  <q:llm id="assistant" model="llama3">
    <default-prompt>You are a friendly chatbot.</default-prompt>
  </q:llm>

  <q:if condition="{query.message}">
    <q:llm-generate
      llm="assistant"
      prompt="{query.message}"
      result="response" />

    <div class="chat">
      <p><strong>You:</strong> {query.message}</p>
      <p><strong>AI:</strong> {response}</p>
    </div>
  </q:if>

  <form method="GET">
    <input type="text" name="message" placeholder="Ask anything..." />
    <button type="submit">Send</button>
  </form>
</q:component>
```

## Examples

### Summarizer

```xml
<q:component name="Summarizer">
  <q:llm id="summarizer" model="llama3" temperature="0.5">
    <default-prompt>Summarize text concisely.</default-prompt>
  </q:llm>

  <q:set name="article" value="{query.text}" />

  <q:if condition="{article}">
    <q:llm-generate
      llm="summarizer"
      prompt="Summarize in 3 sentences: {article}"
      result="summary"
      cache="true" />

    <div class="result">
      <h3>Summary:</h3>
      <p>{summary}</p>
    </div>
  </q:if>

  <form method="GET">
    <textarea name="text" rows="10" placeholder="Paste text to summarize..."></textarea>
    <button type="submit">Summarize</button>
  </form>
</q:component>
```

### Code Assistant

```xml
<q:component name="CodeAssistant">
  <q:llm id="coder" model="codellama:13b" temperature="0.2">
    <default-prompt>Expert programmer. Provide clean code with comments.</default-prompt>
  </q:llm>

  <q:set name="task" value="{query.task}" />

  <q:if condition="{task}">
    <q:llm-generate
      llm="coder"
      prompt="Write Python code for: {task}. Include docstring."
      result="code" />

    <pre><code>{code}</code></pre>
  </q:if>

  <form method="GET">
    <input type="text" name="task" placeholder="E.g., 'sort array'" />
    <button type="submit">Generate Code</button>
  </form>
</q:component>
```

## Available Models

### General Purpose
- `llama3` - Meta's Llama 3 (recommended)
- `mistral` - Mistral AI 7B
- `mixtral` - Mistral AI Mixtral 8x7B

### Code Generation
- `codellama:7b` - Code Llama 7B
- `codellama:13b` - Code Llama 13B (better quality)
- `codellama:34b` - Code Llama 34B (best quality)

### Specialized
- `phi` - Microsoft Phi-2 (fast, small)
- `vicuna` - Vicuna (chat optimized)
- `orca-mini` - Orca Mini (reasoning)

Pull any model:
```bash
ollama pull <model-name>
```

## Configuration

### Temperature

Controls creativity (0.0 = deterministic, 1.0 = creative):

```xml
<!-- Factual tasks -->
<q:llm id="facts" model="llama3" temperature="0.2" />

<!-- Creative tasks -->
<q:llm id="writer" model="llama3" temperature="0.9" />
```

### Max Tokens

Limit response length:

```xml
<q:llm id="concise" model="llama3" max_tokens="100" />
```

### Caching

Cache expensive LLM calls:

```xml
<q:llm-generate
  llm="assistant"
  prompt="Expensive query"
  result="answer"
  cache="true"
  cache_key="unique-key" />
```

## Provider Support

### Ollama (Default)

Local, free, private:

```xml
<q:llm id="local" model="llama3" provider="ollama" />
```

### OpenAI (Optional)

Requires API key:

```xml
<q:llm id="gpt" model="gpt-4" provider="openai" api_key="{env.OPENAI_KEY}" />
```

### Anthropic (Optional)

Requires API key:

```xml
<q:llm id="claude" model="claude-3" provider="anthropic" api_key="{env.ANTHROPIC_KEY}" />
```

## Best Practices

1. **Use Caching** - Cache expensive queries
2. **Choose Right Model** - Balance speed vs quality
3. **Set Temperature** - Lower for facts, higher for creativity
4. **Limit Tokens** - Set max_tokens to control length
5. **Local First** - Use Ollama for privacy & cost

## Troubleshooting

### Error: Model not found

```bash
ollama pull <model-name>
```

### Error: Cannot connect to Ollama

```bash
# Start Ollama
ollama serve
```

### Model too slow

Use smaller models:
- `llama3` → `phi` (faster)
- `codellama:13b` → `codellama:7b`

## Performance Tips

1. **Model Size** - Smaller = faster (but less accurate)
2. **Caching** - Always cache repeated queries
3. **Temperature** - Lower = faster generation
4. **Max Tokens** - Limit to what you need

## Roadmap

- [ ] Streaming support for real-time chat
- [ ] Chat history management
- [ ] RAG (Retrieval-Augmented Generation)
- [ ] Fine-tuning support
- [ ] Multi-turn conversations
- [ ] Function calling

## See Also

- [Ollama Documentation](https://ollama.ai/docs)
- [Model Library](https://ollama.ai/library)
- [Example Components](../../../components/llm_demo.q)

---

**Status:** ✅ Implemented (Q1 2025)
**Priority:** HIGH
**Effort:** 3-4 weeks
