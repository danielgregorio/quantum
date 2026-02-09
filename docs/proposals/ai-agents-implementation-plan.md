# Plano de Implementação: q:agent - AI Agents

**Data:** 2026-02-08
**Status:** Proposta
**Prioridade:** HIGH
**Esforço Estimado:** 2-3 semanas (Phase 1)

---

## 1. Resumo Executivo

### O que já existe (pronto para usar):

| Componente | Status | Localização |
|------------|--------|-------------|
| **q:llm** | ✅ Completo | `llm_service.py` (287 linhas) |
| **q:knowledge (RAG)** | ✅ Completo | `knowledge_service.py` (497 linhas) |
| **ChromaDB (Vector DB)** | ✅ Integrado | Via q:knowledge |
| **Ollama API** | ✅ Integrado | Chat, Completions, Embeddings |
| **Design do Agent** | ✅ Documentado | `features/agents/docs/README.md` |

### O que precisa ser implementado:

| Componente | Esforço | Prioridade |
|------------|---------|------------|
| AST Nodes (Agent, Tool, Execute) | 2 dias | CRÍTICO |
| Parser para q:agent | 2 dias | CRÍTICO |
| AgentService (reasoning loop) | 3 dias | CRÍTICO |
| Tool Registry & Invocation | 2 dias | CRÍTICO |
| Executor no component.py | 1 dia | CRÍTICO |
| Testes | 2 dias | ALTO |
| Documentação | 1 dia | MÉDIO |

---

## 2. Arquitetura Proposta

### 2.1 Fluxo de Execução do Agent

```
┌─────────────────────────────────────────────────────────────────┐
│                     AGENT EXECUTION FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   <q:agent>                                                      │
│       │                                                          │
│       ▼                                                          │
│   ┌──────────────┐                                              │
│   │ Parse Agent  │ → AgentNode + Tools + Instructions           │
│   └──────────────┘                                              │
│       │                                                          │
│       ▼                                                          │
│   ┌──────────────┐                                              │
│   │ Build Tool   │ → {"name": "...", "description": "...",      │
│   │   Schema     │    "parameters": {...}}                       │
│   └──────────────┘                                              │
│       │                                                          │
│       ▼                                                          │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              REASONING LOOP (ReAct Pattern)               │  │
│   │                                                           │  │
│   │   ┌─────────┐    ┌─────────┐    ┌─────────┐              │  │
│   │   │  THINK  │───▶│   ACT   │───▶│ OBSERVE │───┐          │  │
│   │   │  (LLM)  │    │ (Tool)  │    │(Result) │   │          │  │
│   │   └─────────┘    └─────────┘    └─────────┘   │          │  │
│   │        ▲                                       │          │  │
│   │        └───────────────────────────────────────┘          │  │
│   │                    (until done or max_iterations)         │  │
│   └──────────────────────────────────────────────────────────┘  │
│       │                                                          │
│       ▼                                                          │
│   ┌──────────────┐                                              │
│   │  Synthesize  │ → Final response + action log                │
│   │   Response   │                                              │
│   └──────────────┘                                              │
│       │                                                          │
│       ▼                                                          │
│   {agent_result}                                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Estrutura de Arquivos

```
src/
├── core/
│   ├── ast_nodes.py              # + AgentNode, AgentToolNode, etc.
│   ├── parser.py                 # + _parse_agent_statement()
│   └── features/agents/
│       ├── manifest.yaml         # ✅ Existe
│       ├── docs/README.md        # ✅ Existe
│       └── src/
│           ├── __init__.py       # NOVO
│           └── ast_node.py       # NOVO (classes AST)
│
├── runtime/
│   ├── component.py              # + _execute_agent()
│   └── agent_service.py          # NOVO (reasoning loop)
│
└── tests/
    └── test_agent.py             # NOVO (testes)
```

---

## 3. Implementação Detalhada

### 3.1 Phase 1: AST Nodes

**Arquivo:** `src/core/features/agents/src/ast_node.py`

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from core.ast_nodes import QuantumNode

@dataclass
class AgentToolParamNode(QuantumNode):
    """Parameter definition for an agent tool."""
    name: str
    type: str = "string"
    required: bool = False
    default: Optional[Any] = None
    description: str = ""

@dataclass
class AgentToolNode(QuantumNode):
    """Tool available to the agent."""
    name: str
    description: str
    params: List[AgentToolParamNode] = field(default_factory=list)
    body: List[QuantumNode] = field(default_factory=list)  # q:function content

@dataclass
class AgentInstructionNode(QuantumNode):
    """System instruction for the agent."""
    content: str = ""

@dataclass
class AgentExecuteNode(QuantumNode):
    """Execute the agent with a task."""
    task: str = ""
    context: str = ""  # Optional additional context

@dataclass
class AgentNode(QuantumNode):
    """AI Agent that can use tools to complete tasks."""
    name: str
    model: str = "phi3"
    endpoint: str = ""
    max_iterations: int = 10
    timeout: int = 60000  # ms

    instruction: Optional[AgentInstructionNode] = None
    tools: List[AgentToolNode] = field(default_factory=list)
    execute: Optional[AgentExecuteNode] = None
```

### 3.2 Phase 1: Parser

**Arquivo:** `src/core/parser.py` (adicionar método)

```python
def _parse_agent_statement(self, element: ET.Element) -> AgentNode:
    """Parse <q:agent> element."""
    name = element.get('name', '')
    if not name:
        raise ParseError("<q:agent> requires 'name' attribute")

    model = element.get('model', 'phi3')
    endpoint = element.get('endpoint', '')
    max_iterations = int(element.get('max_iterations', '10'))
    timeout = int(element.get('timeout', '60000'))

    instruction = None
    tools = []
    execute = None

    for child in element:
        tag = self._get_local_tag(child)

        if tag == 'instruction':
            instruction = AgentInstructionNode(
                content=self._get_text_content(child)
            )

        elif tag == 'tool':
            tool = self._parse_agent_tool(child)
            tools.append(tool)

        elif tag == 'execute':
            execute = AgentExecuteNode(
                task=child.get('task', self._get_text_content(child)),
                context=child.get('context', '')
            )

    return AgentNode(
        name=name,
        model=model,
        endpoint=endpoint,
        max_iterations=max_iterations,
        timeout=timeout,
        instruction=instruction,
        tools=tools,
        execute=execute
    )

def _parse_agent_tool(self, element: ET.Element) -> AgentToolNode:
    """Parse <q:tool> element."""
    name = element.get('name', '')
    description = element.get('description', '')

    params = []
    body = []

    for child in element:
        tag = self._get_local_tag(child)

        if tag == 'param':
            params.append(AgentToolParamNode(
                name=child.get('name', ''),
                type=child.get('type', 'string'),
                required=child.get('required', 'false').lower() == 'true',
                default=child.get('default'),
                description=child.get('description', '')
            ))
        else:
            # Parse body content (q:function, q:query, etc.)
            body.append(self._parse_element(child))

    return AgentToolNode(
        name=name,
        description=description,
        params=params,
        body=body
    )
```

### 3.3 Phase 1: Agent Service

**Arquivo:** `src/runtime/agent_service.py` (NOVO - ~400 linhas)

```python
"""
Agent Service - Reasoning loop and tool execution for AI agents.

Implements the ReAct (Reason + Act) pattern:
1. THINK: LLM analyzes task and decides next action
2. ACT: Execute the chosen tool
3. OBSERVE: Process tool result
4. REPEAT: Until task complete or max_iterations

Uses existing LLMService for LLM calls.
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Error during agent execution."""
    pass


@dataclass
class ToolCall:
    """Represents a tool invocation."""
    tool: str
    args: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class AgentResult:
    """Result of agent execution."""
    success: bool = False
    result: str = ""
    error: Optional[Dict[str, str]] = None
    execution_time_ms: float = 0
    iterations: int = 0
    action_count: int = 0
    actions: List[ToolCall] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "executionTime": self.execution_time_ms,
            "iterations": self.iterations,
            "actionCount": self.action_count,
            "actions": [
                {"tool": a.tool, "args": a.args, "result": a.result}
                for a in self.actions
            ],
            "tokenUsage": self.token_usage
        }


class AgentService:
    """
    Executes AI agents with tool use capabilities.

    Uses LLM to reason about which tools to use and when,
    then executes those tools and observes results.
    """

    # System prompt template for tool-using agents
    SYSTEM_PROMPT_TEMPLATE = '''You are an AI agent that completes tasks by using tools.

AVAILABLE TOOLS:
{tools_description}

INSTRUCTIONS:
{instruction}

RESPONSE FORMAT:
When you need to use a tool, respond with EXACTLY this JSON format:
```json
{{"action": "tool_name", "args": {{"param1": "value1"}}}}
```

When you have completed the task, respond with EXACTLY:
```json
{{"action": "finish", "result": "Your final response to the user"}}
```

IMPORTANT:
- Only use the tools provided above
- Use tools one at a time
- After each tool call, you'll see the result
- When done, use the "finish" action with your complete response
'''

    def __init__(self, llm_service, component_executor=None):
        """
        Initialize agent service.

        Args:
            llm_service: LLMService instance for LLM calls
            component_executor: Component instance for tool execution
        """
        self.llm_service = llm_service
        self.component_executor = component_executor

    def execute(
        self,
        instruction: str,
        tools: List[Dict[str, Any]],
        task: str,
        context: str = "",
        model: str = "phi3",
        endpoint: str = "",
        max_iterations: int = 10,
        timeout_ms: int = 60000
    ) -> AgentResult:
        """
        Execute an agent with the given task.

        Args:
            instruction: System instruction for the agent
            tools: List of tool definitions with name, description, params
            task: The task to complete
            context: Additional context
            model: LLM model to use
            endpoint: LLM endpoint (optional)
            max_iterations: Maximum tool calls
            timeout_ms: Total timeout in milliseconds

        Returns:
            AgentResult with success, result, actions, etc.
        """
        start_time = time.time()
        result = AgentResult()

        try:
            # Build tools description for system prompt
            tools_desc = self._build_tools_description(tools)

            # Build system prompt
            system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
                tools_description=tools_desc,
                instruction=instruction or "Complete the user's task."
            )

            # Build initial user message
            user_message = task
            if context:
                user_message = f"{task}\n\nContext: {context}"

            # Conversation history
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            # Reasoning loop
            iteration = 0
            total_tokens = {"prompt": 0, "completion": 0, "total": 0}

            while iteration < max_iterations:
                # Check timeout
                elapsed = (time.time() - start_time) * 1000
                if elapsed > timeout_ms:
                    raise AgentError(f"Agent timed out after {elapsed:.0f}ms")

                iteration += 1
                result.iterations = iteration

                # Call LLM
                llm_response = self._call_llm(
                    messages=messages,
                    model=model,
                    endpoint=endpoint
                )

                # Update token usage
                if "usage" in llm_response:
                    for key in total_tokens:
                        total_tokens[key] += llm_response["usage"].get(key, 0)

                # Parse LLM response
                assistant_message = llm_response.get("content", "")
                messages.append({"role": "assistant", "content": assistant_message})

                # Extract action from response
                action = self._extract_action(assistant_message)

                if action is None:
                    # LLM didn't produce valid action, treat as finish
                    result.success = True
                    result.result = assistant_message
                    break

                if action.get("action") == "finish":
                    # Agent is done
                    result.success = True
                    result.result = action.get("result", assistant_message)
                    break

                # Execute tool
                tool_name = action.get("action", "")
                tool_args = action.get("args", {})

                tool_call = self._execute_tool(tool_name, tool_args, tools)
                result.actions.append(tool_call)
                result.action_count += 1

                # Add tool result to conversation
                if tool_call.error:
                    tool_result = f"Error: {tool_call.error}"
                else:
                    tool_result = json.dumps(tool_call.result) if not isinstance(tool_call.result, str) else tool_call.result

                messages.append({
                    "role": "user",
                    "content": f"Tool '{tool_name}' returned: {tool_result}"
                })

            if not result.success and iteration >= max_iterations:
                result.error = {"message": f"Max iterations ({max_iterations}) reached"}

            result.token_usage = total_tokens

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            result.success = False
            result.error = {"message": str(e)}

        result.execution_time_ms = (time.time() - start_time) * 1000
        return result

    def _build_tools_description(self, tools: List[Dict[str, Any]]) -> str:
        """Build human-readable tools description for system prompt."""
        lines = []
        for tool in tools:
            name = tool.get("name", "")
            desc = tool.get("description", "")
            params = tool.get("params", [])

            params_desc = ", ".join([
                f"{p['name']}: {p.get('type', 'string')}"
                + (" (required)" if p.get('required') else "")
                for p in params
            ])

            lines.append(f"- {name}({params_desc}): {desc}")

        return "\n".join(lines)

    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        model: str,
        endpoint: str
    ) -> Dict[str, Any]:
        """Call LLM with messages."""
        return self.llm_service.chat(
            messages=messages,
            model=model,
            endpoint=endpoint if endpoint else None,
            temperature=0.1,  # Low temperature for more deterministic tool use
            response_format="text"
        )

    def _extract_action(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract action JSON from LLM response."""
        import re

        # Try to find JSON in code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return None

    def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tools: List[Dict[str, Any]]
    ) -> ToolCall:
        """Execute a tool and return result."""
        start = time.time()
        call = ToolCall(tool=tool_name, args=tool_args)

        try:
            # Find tool definition
            tool_def = next((t for t in tools if t["name"] == tool_name), None)
            if not tool_def:
                call.error = f"Unknown tool: {tool_name}"
                return call

            # Execute tool body (q:function, q:query, etc.)
            if self.component_executor and "body" in tool_def:
                # Set tool args in context
                for arg_name, arg_value in tool_args.items():
                    self.component_executor.context.set_variable(arg_name, arg_value)

                # Execute tool body
                for node in tool_def["body"]:
                    self.component_executor._execute_node(node)

                # Get return value (if any)
                call.result = self.component_executor.context.get_variable("_return", "OK")
            else:
                call.result = f"Tool {tool_name} executed (no body)"

        except Exception as e:
            call.error = str(e)
            logger.error(f"Tool {tool_name} failed: {e}")

        call.duration_ms = (time.time() - start) * 1000
        return call


# Singleton instance
_agent_service = None

def get_agent_service(llm_service=None, component_executor=None):
    """Get or create the global agent service instance."""
    global _agent_service
    if _agent_service is None:
        from runtime.llm_service import get_llm_service
        llm = llm_service or get_llm_service()
        _agent_service = AgentService(llm, component_executor)
    return _agent_service
```

### 3.4 Phase 1: Executor Integration

**Arquivo:** `src/runtime/component.py` (adicionar método)

```python
def _execute_agent(self, node: AgentNode):
    """Execute an AI agent with tool use."""
    from runtime.agent_service import get_agent_service, AgentResult

    # Resolve databinding in task
    task = ""
    context = ""
    if node.execute:
        task = self._resolve_databinding(node.execute.task)
        context = self._resolve_databinding(node.execute.context)

    # Get instruction
    instruction = ""
    if node.instruction:
        instruction = self._resolve_databinding(node.instruction.content)

    # Build tool definitions
    tools = []
    for tool_node in node.tools:
        tool_def = {
            "name": tool_node.name,
            "description": tool_node.description,
            "params": [
                {
                    "name": p.name,
                    "type": p.type,
                    "required": p.required,
                    "default": p.default,
                    "description": p.description
                }
                for p in tool_node.params
            ],
            "body": tool_node.body  # AST nodes for execution
        }
        tools.append(tool_def)

    # Get agent service
    agent_service = get_agent_service(component_executor=self)

    # Execute agent
    result = agent_service.execute(
        instruction=instruction,
        tools=tools,
        task=task,
        context=context,
        model=node.model,
        endpoint=node.endpoint,
        max_iterations=node.max_iterations,
        timeout_ms=node.timeout
    )

    # Store result
    self.context.set_variable(node.name, result.result)
    self.context.set_variable(f"{node.name}_result", result.to_dict())
```

---

## 4. Cronograma de Implementação

### Semana 1: Fundação

| Dia | Tarefa | Entregável |
|-----|--------|------------|
| 1 | AST Nodes | `features/agents/src/ast_node.py` |
| 2 | Parser | `_parse_agent_statement()` em parser.py |
| 3 | AgentService (estrutura) | `agent_service.py` básico |
| 4 | AgentService (reasoning loop) | Loop ReAct completo |
| 5 | Integração component.py | `_execute_agent()` funcionando |

### Semana 2: Qualidade

| Dia | Tarefa | Entregável |
|-----|--------|------------|
| 1 | Testes unitários | `tests/test_agent_service.py` |
| 2 | Testes de integração | `tests/test_agent.py` |
| 3 | Exemplos | `examples/agent_*.q` |
| 4 | Documentação | Update docs |
| 5 | Code review & fixes | Refinamentos |

---

## 5. Dependências e Integrações

### 5.1 Usa LLMService existente

```python
# O AgentService usa o LLMService já implementado
from runtime.llm_service import get_llm_service

llm = get_llm_service()
response = llm.chat(messages=[...], model="phi3")
```

### 5.2 Usa KnowledgeService para RAG Tools

```python
# Agents podem usar RAG como ferramenta
<q:tool name="searchDocs" description="Search knowledge base">
    <q:param name="query" type="string" required="true" />
    <q:function name="search">
        <q:query name="results" datasource="knowledge:docs" mode="search">
            SELECT content FROM chunks WHERE content SIMILAR TO :query
            <q:param name="query" value="{query}" />
        </q:query>
        <q:return value="{results}" />
    </q:function>
</q:tool>
```

### 5.3 Integração com Features Existentes

| Feature | Como o Agent Usa |
|---------|------------------|
| `q:function` | Corpo dos tools |
| `q:query` | Tools de banco de dados |
| `q:invoke` | Tools de API externa |
| `q:llm` | Tools que chamam outros LLMs |
| `q:data` | Tools de processamento de dados |
| `q:knowledge` | Tools de RAG/busca semântica |

---

## 6. Exemplo de Uso Completo

```xml
<?xml version="1.0" encoding="UTF-8"?>
<q:component name="SupportAgent">
    <q:param name="userQuestion" type="string" required="true" />

    <!-- Carregar knowledge base -->
    <q:knowledge name="faq" model="phi3" embedModel="nomic-embed-text">
        <q:source type="file" path="data/faq.md" />
        <q:source type="file" path="data/policies.md" />
    </q:knowledge>

    <!-- Agent de suporte -->
    <q:agent name="support" model="phi3" max_iterations="5">
        <q:instruction>
            You are a helpful customer support agent.
            Use the available tools to find information and help users.
            Be concise and friendly.
        </q:instruction>

        <!-- Tool: Buscar na FAQ -->
        <q:tool name="searchFAQ" description="Search FAQ and policies">
            <q:param name="query" type="string" required="true" />
            <q:function name="doSearch">
                <q:query name="results" datasource="knowledge:faq" mode="search">
                    SELECT content, relevance FROM chunks
                    WHERE content SIMILAR TO :query
                    LIMIT 3
                    <q:param name="query" value="{query}" />
                </q:query>
                <q:return value="{results}" />
            </q:function>
        </q:tool>

        <!-- Tool: Consultar pedido -->
        <q:tool name="getOrder" description="Get order details by ID">
            <q:param name="orderId" type="integer" required="true" />
            <q:function name="fetchOrder">
                <q:query name="order" datasource="db">
                    SELECT * FROM orders WHERE id = :orderId
                    <q:param name="orderId" value="{orderId}" type="integer" />
                </q:query>
                <q:return value="{order[0]}" />
            </q:function>
        </q:tool>

        <!-- Executar -->
        <q:execute task="{userQuestion}" />
    </q:agent>

    <!-- Exibir resultado -->
    <div class="chat-response">
        <p>{support}</p>

        <q:if condition="{support_result.actionCount > 0}">
            <details>
                <summary>Actions taken ({support_result.actionCount})</summary>
                <q:loop items="{support_result.actions}" var="action">
                    <p><strong>{action.tool}</strong>: {action.result}</p>
                </q:loop>
            </details>
        </q:if>
    </div>
</q:component>
```

---

## 7. Métricas de Sucesso

| Métrica | Target |
|---------|--------|
| Testes passando | 100% |
| Cobertura de código | >80% |
| Tempo médio de execução | <5s para tarefas simples |
| Taxa de sucesso (tool calling) | >90% |
| Documentação | 100% das APIs documentadas |

---

## 8. Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| LLM não segue formato JSON | Retry com prompt mais explícito |
| Tools falham | Retry com backoff + error handling |
| Loops infinitos | max_iterations + timeout |
| Custo de tokens alto | Cache de respostas + early stopping |
| Modelo local lento | Otimizar prompts + streaming futuro |

---

## 9. Fases Futuras (Não neste escopo)

### Phase 2: Advanced Tools
- Tool approval flow (confirmação do usuário)
- Parallel tool execution
- Tool retry com backoff
- Tool caching

### Phase 3: Multi-Agent
- Agent-to-agent communication
- Hierarchical agents (supervisor + workers)
- Agent memory (persistence entre requests)
- Agent chaining (output → input)

---

## 10. Conclusão

A implementação do `q:agent` é viável e bem fundamentada:

1. **LLM está pronto** - O `LLMService` já funciona com Ollama
2. **RAG está pronto** - O `KnowledgeService` já suporta ChromaDB
3. **Design está completo** - Documentação detalhada existe
4. **Esforço é moderado** - 2-3 semanas para Phase 1

**Recomendação:** Iniciar implementação imediatamente, começando pelos AST nodes e parser.
