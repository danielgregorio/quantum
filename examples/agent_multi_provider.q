<?xml version="1.0" encoding="UTF-8"?>
<!--
  Agent Multi-Provider Demo - AI Agent with Multiple LLM Providers

  This example demonstrates q:agent with different LLM providers:
  - Ollama (local, default)
  - LM Studio (local, OpenAI-compatible)
  - OpenAI (cloud)
  - Anthropic/Claude (cloud)

  Provider Detection:
  - endpoint="http://localhost:11434" -> Ollama
  - endpoint="http://localhost:1234/v1" -> LM Studio (OpenAI-compatible)
  - provider="openai" -> OpenAI API
  - provider="anthropic" -> Anthropic Claude API

  Environment Variables:
  - OPENAI_API_KEY: For OpenAI provider
  - ANTHROPIC_API_KEY: For Anthropic provider

  Run:
    # Using Ollama (requires: ollama serve)
    python src/cli/runner.py run examples/agent_multi_provider.q

    # Using OpenAI (requires: OPENAI_API_KEY env var)
    export OPENAI_API_KEY="sk-..."
    python src/cli/runner.py run examples/agent_multi_provider.q --param provider=openai

    # Using Anthropic (requires: ANTHROPIC_API_KEY env var)
    export ANTHROPIC_API_KEY="sk-ant-..."
    python src/cli/runner.py run examples/agent_multi_provider.q --param provider=anthropic
-->
<q:component name="AgentMultiProvider">
    <!-- Provider selection (default: ollama) -->
    <q:param name="llmProvider" type="string" default="ollama" />
    <q:param name="llmModel" type="string" default="phi3" />
    <q:param name="userQuestion" type="string" default="What is the capital of France?" />

    <!--
      Example 1: Ollama (Local LLM)
      Default provider - auto-detects from endpoint
    -->
    <q:agent name="ollamaAgent"
             model="{llmModel}"
             provider="ollama"
             max_iterations="5">
        <q:instruction>
            You are a helpful assistant. Answer questions concisely.
        </q:instruction>

        <q:tool name="search" description="Search for information">
            <q:param name="query" type="string" required="true" />
            <q:function name="doSearch">
                <q:set name="result" value="Paris is the capital of France." />
                <q:return value="{result}" />
            </q:function>
        </q:tool>

        <q:execute task="{userQuestion}" />
    </q:agent>

    <!--
      Example 2: LM Studio (OpenAI-compatible Local)
      Uses OpenAI API format at localhost:1234
    -->
    <!--
    <q:agent name="lmStudioAgent"
             model="mistral-7b-instruct"
             endpoint="http://localhost:1234/v1"
             max_iterations="5">
        ...
    </q:agent>
    -->

    <!--
      Example 3: OpenAI (Cloud)
      Requires OPENAI_API_KEY environment variable
    -->
    <!--
    <q:agent name="openaiAgent"
             model="gpt-4"
             provider="openai"
             api_key="{env.OPENAI_API_KEY}"
             max_iterations="5">
        ...
    </q:agent>
    -->

    <!--
      Example 4: Anthropic/Claude (Cloud)
      Requires ANTHROPIC_API_KEY environment variable
    -->
    <!--
    <q:agent name="claudeAgent"
             model="claude-3-haiku-20240307"
             provider="anthropic"
             api_key="{env.ANTHROPIC_API_KEY}"
             max_iterations="5">
        ...
    </q:agent>
    -->

    <!-- Display results -->
    <div class="agent-demo">
        <h1>Multi-Provider Agent Demo</h1>

        <div class="config">
            <p><strong>Provider:</strong> {llmProvider}</p>
            <p><strong>Model:</strong> {llmModel}</p>
        </div>

        <div class="question">
            <strong>Question:</strong> {userQuestion}
        </div>

        <div class="answer">
            <strong>Answer:</strong> {ollamaAgent}
        </div>

        <q:if condition="{ollamaAgent_result.success}">
            <div class="stats">
                <p>Execution time: {ollamaAgent_result.executionTime}ms</p>
                <p>Iterations: {ollamaAgent_result.iterations}</p>
                <p>Actions: {ollamaAgent_result.actionCount}</p>
            </div>
        </q:if>

        <q:if condition="{!ollamaAgent_result.success}">
            <div class="error">
                <p>Error: {ollamaAgent_result.error.message}</p>
            </div>
        </q:if>
    </div>
</q:component>
