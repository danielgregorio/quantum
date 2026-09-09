<?xml version="1.0" encoding="UTF-8"?>
<!--
  Agent Demo - AI Agent with Tool Use

  This example demonstrates q:agent with:
  - System instruction
  - Multiple tools
  - Task execution

  Requires: Ollama running locally with phi3 model
  Run: python src/cli/runner.py run examples/agent_demo.q
-->
<q:component name="AgentDemo">
    <!-- Input parameter -->
    <q:param name="userQuestion" type="string" default="What is 2 + 2?" />

    <!-- Define an AI agent with tools -->
    <q:agent name="calculator" model="phi3" max_iterations="5">
        <q:instruction>
            You are a helpful calculator assistant.
            Use the provided tools to perform calculations.
            Be concise in your responses.
        </q:instruction>

        <!-- Tool: Add two numbers -->
        <q:tool name="add" description="Add two numbers together">
            <q:param name="a" type="number" required="true" description="First number" />
            <q:param name="b" type="number" required="true" description="Second number" />
            <q:function name="doAdd">
                <q:set name="result" value="{a + b}" type="number" />
                <q:return value="{result}" />
            </q:function>
        </q:tool>

        <!-- Tool: Multiply two numbers -->
        <q:tool name="multiply" description="Multiply two numbers">
            <q:param name="a" type="number" required="true" description="First number" />
            <q:param name="b" type="number" required="true" description="Second number" />
            <q:function name="doMultiply">
                <q:set name="result" value="{a * b}" type="number" />
                <q:return value="{result}" />
            </q:function>
        </q:tool>

        <!-- Tool: Get current date -->
        <q:tool name="getDate" description="Get the current date and time">
            <q:function name="fetchDate">
                <q:set name="now" value="{datetime.now()}" />
                <q:return value="{now}" />
            </q:function>
        </q:tool>

        <!-- Execute the agent -->
        <q:execute task="{userQuestion}" />
    </q:agent>

    <!-- Display results -->
    <div class="agent-demo">
        <h1>Calculator Agent Demo</h1>

        <div class="question">
            <strong>Question:</strong> {userQuestion}
        </div>

        <div class="answer">
            <strong>Answer:</strong> {calculator}
        </div>

        <q:if condition="{calculator_result.success}">
            <div class="stats">
                <p>Execution time: {calculator_result.executionTime}ms</p>
                <p>Iterations: {calculator_result.iterations}</p>
                <p>Actions: {calculator_result.actionCount}</p>
            </div>

            <q:if condition="{calculator_result.actionCount > 0}">
                <div class="actions">
                    <h3>Tool Calls:</h3>
                    <ul>
                        <q:loop items="{calculator_result.actions}" var="action">
                            <li>
                                <strong>{action.tool}</strong>({action.args})
                                → {action.result}
                            </li>
                        </q:loop>
                    </ul>
                </div>
            </q:if>
        </q:if>

        <q:if condition="{!calculator_result.success}">
            <div class="error">
                <p>Error: {calculator_result.error.message}</p>
            </div>
        </q:if>
    </div>
</q:component>
