# LLM Features in Quantum

Quantum provides native AI integration through the `q:llm` tag, powered by Ollama for local, free AI.

## Defining an LLM

```xml
<q:llm id="assistant" model="llama3" provider="ollama" temperature="0.7">
  <default-prompt>You are a helpful AI assistant.</default-prompt>
</q:llm>
```

## Generating Text

```xml
<q:llm-generate
  llm="assistant"
  prompt="Explain {topic}"
  result="explanation" />

<p>{explanation}</p>
```

## Chat Interface

```xml
<q:llm-chat llm="assistant" session="chat_history" />
```

## Supported Models

- **llama3**: General purpose (recommended)
- **codellama**: Code generation
- **mistral**: Fast and accurate
- **mixtral**: Advanced reasoning

## Advantages

- **Free**: No API costs
- **Local**: Complete privacy
- **Fast**: Low latency
- **Offline**: Works without internet
