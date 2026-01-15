<q:component name="LLMDemo">
  <!-- Define LLM configurations -->
  <q:llm id="assistant" model="llama3" provider="ollama" temperature="0.7">
    <default-prompt>You are a helpful AI assistant. Be concise and friendly.</default-prompt>
  </q:llm>

  <q:llm id="coder" model="codellama:7b" provider="ollama" temperature="0.2">
    <default-prompt>You are an expert programmer. Provide clean, well-commented code.</default-prompt>
  </q:llm>

  <!-- Example 1: Simple text generation -->
  <h2>🤖 AI Text Generation</h2>

  <q:set name="topic" value="quantum computing" />

  <q:llm-generate
    llm="assistant"
    prompt="Explain {topic} in one sentence."
    result="explanation"
    cache="true" />

  <div class="result">
    <strong>Question:</strong> Explain {topic}<br/>
    <strong>Answer:</strong> {explanation}
  </div>

  <hr/>

  <!-- Example 2: Code generation -->
  <h2>💻 Code Generation</h2>

  <q:set name="task" value="calculate factorial" />

  <q:llm-generate
    llm="coder"
    prompt="Write a Python function to {task}. Include docstring and example."
    result="code" />

  <div class="code-result">
    <strong>Task:</strong> {task}<br/>
    <pre><code>{code}</code></pre>
  </div>

  <hr/>

  <!-- Example 3: Multiple generations -->
  <h2>📝 Story Generator</h2>

  <q:loop type="range" start="1" end="3" item="i">
    <q:llm-generate
      llm="assistant"
      prompt="Write a one-sentence story about a robot. Make it unique."
      result="story_{i}" />

    <p><strong>Story {i}:</strong> {story_{i}}</p>
  </q:loop>

  <style>
    body {
      font-family: Arial, sans-serif;
      max-width: 800px;
      margin: 50px auto;
      padding: 20px;
      background: #f5f5f5;
    }

    h2 {
      color: #2c3e50;
      border-bottom: 2px solid #3498db;
      padding-bottom: 10px;
    }

    .result, .code-result {
      background: white;
      padding: 20px;
      border-radius: 8px;
      margin: 20px 0;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    pre {
      background: #2c3e50;
      color: #ecf0f1;
      padding: 15px;
      border-radius: 5px;
      overflow-x: auto;
    }

    code {
      font-family: 'Courier New', monospace;
    }

    hr {
      border: none;
      border-top: 1px solid #ddd;
      margin: 40px 0;
    }
  </style>
</q:component>
