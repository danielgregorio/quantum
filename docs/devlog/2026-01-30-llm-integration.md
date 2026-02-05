# Devlog: Implementacao q:llm com Ollama Backend

**Data:** 2026-01-30
**Feature:** Tag `<q:llm>` - Integracao com LLM via Ollama API

---

## Resumo

Implementacao completa da tag `<q:llm>` no Quantum Framework, permitindo invocar modelos LLM (Large Language Models) diretamente de componentes `.q`. Backend utiliza Ollama rodando no forge (10.10.1.40:11434) com modelo phi3.

---

## Arquivos Criados

| Arquivo | Descricao |
|---------|-----------|
| `src/runtime/llm_service.py` | Client HTTP para Ollama API (generate, chat, list_models, pull_model) |
| `projects/llm-demo/components/index.q` | Chat interativo com LLM usando sessao |
| `projects/llm-demo/quantum.config.yaml` | Config completa do projeto para deploy |
| `examples/llm_demo.q` | 4 exemplos de teste (completion, chat, JSON, databinding) |

## Arquivos Modificados

| Arquivo | Mudanca |
|---------|---------|
| `src/core/ast_nodes.py` | Adicionado `LLMNode` e `LLMMessageNode` |
| `src/core/parser.py` | Adicionado `_parse_llm_statement`, registrado nos switches de parsing |
| `src/runtime/component.py` | Adicionado `_execute_llm`, init do LLMService |
| `src/runtime/web_server.py` | Fix `.get()` para config keys, deep merge de configs |
| `src/runtime/execution_context.py` | Fix prefixo `session.` no `update_variable` |
| `quantum.config.yaml` | Adicionada secao `llm` |
| `.env.example` | Adicionadas variaveis LLM |

---

## Detalhes Tecnicos

### AST Nodes

```python
class LLMNode(QuantumNode):
    name: str           # Nome da variavel de resultado
    model: str          # ex: "phi3", "mistral"
    endpoint: str       # Override do endpoint Ollama
    prompt: str         # Texto do prompt (completion mode)
    system: str         # System prompt
    messages: List[LLMMessageNode]  # Chat mode
    temperature: float
    max_tokens: int
    response_format: str  # "text" ou "json"
    cache: bool
    timeout: int

class LLMMessageNode(QuantumNode):
    role: str       # "system", "user", "assistant"
    content: str
```

### Sintaxe q:llm

**Completion mode:**
```xml
<q:llm name="result" model="phi3" endpoint="http://host:11434">
    <q:prompt>Texto do prompt aqui</q:prompt>
</q:llm>
<!-- Resultado acessivel como {result} -->
```

**Chat mode:**
```xml
<q:llm name="reply" model="phi3" endpoint="http://host:11434" maxTokens="300">
    <q:message role="system">System prompt</q:message>
    <q:message role="user">{form.userInput}</q:message>
</q:llm>
<!-- Resultado acessivel como {reply} -->
```

### LLM Service

- Client HTTP sincrono usando `requests`
- Endpoints Ollama: `/api/generate`, `/api/chat`, `/api/tags`, `/api/pull`
- Config via env vars: `QUANTUM_LLM_BASE_URL`, `QUANTUM_LLM_DEFAULT_MODEL`, `QUANTUM_LLM_TIMEOUT`
- Suporte a JSON response format com auto-parse

### Chat Interativo

O componente `projects/llm-demo/components/index.q` implementa:
- Historico de conversa via `session.chatHistory` (array no session scope)
- Formulario POST para enviar mensagens
- Botao "Clear Chat" para limpar historico
- UI dark theme com mensagens estilizadas via JS pos-render
- Auto-scroll para ultima mensagem

---

## Bugs Encontrados e Corrigidos

### 1. KeyError: 'reload' no web_server.py

**Causa:** Config minima do projeto nao tinha todas as chaves esperadas. `self.config['server']['reload']` falhava quando o YAML so tinha `port` e `host`.

**Fix:** Trocado para `.get('reload', False)` em 3 locais. Tambem corrigido `_load_config` para fazer deep merge ao inves de `dict.update()` shallow.

### 2. LLM nao executando no forge (variaveis mostrando como `{greeting}`)

**Causa:** O deploy service no forge (`/home/abathur/quantum-deploy/`) tinha codigo-fonte antigo sem suporte a `LLMNode`. Os 5 arquivos core nunca tinham sido atualizados no servidor.

**Fix:** Upload via SFTP (paramiko) dos 5 arquivos atualizados para o forge.

### 3. XML parse error na tag `<script>` (linha 133, coluna 25)

**Causa:** O operador `<` no loop JS `for (var i = 0; i < msgs.length; i++)` e interpretado como inicio de tag XML pelo parser.

**Fix:** Substituido `for` loop por `Array.prototype.slice.call().forEach()` que nao usa `<`.

### 4. Cannot perform array operation on non-array: `<class 'str'>` (BUG CRITICO)

**Causa raiz:** O `execution_context.py` no container Docker estava desatualizado. O metodo `update_variable()` NAO tinha tratamento de prefixo `session.`:

```python
# VERSAO ANTIGA (bugada) - update_variable:
def update_variable(self, name, value):
    if name in self.local_vars:      # "session.chatHistory" nao esta aqui
        self.local_vars[name] = value
    elif name in self.session_vars:  # Busca "session.chatHistory" literal, nao "chatHistory"
        self.session_vars[name] = value
    else:
        self.local_vars[name] = value  # Salva como "session.chatHistory" em local_vars!
```

Enquanto `get_variable()` JA tinha o tratamento correto:

```python
# get_variable (correto):
if '.' in name:
    prefix, var_name = name.split('.', 1)
    if prefix == 'session':
        return self.session_vars.get(var_name, '')  # Busca "chatHistory" em session_vars
```

**Assimetria:** `set` salvava como chave literal `"session.chatHistory"` em `local_vars`, mas `get` buscava `"chatHistory"` em `session_vars` -> retornava `''` (string) -> append falhava porque esperava lista.

**Fix:** Upload do `execution_context.py` atualizado que tem tratamento de prefixo `session.` no `update_variable()`:

```python
# VERSAO CORRIGIDA:
def update_variable(self, name, value):
    if '.' in name:
        prefix, var_name = name.split('.', 1)
        if prefix == 'session':
            self.session_vars[var_name] = value
            return
    # ... resto da logica
```

**Arquivos atualizados no forge:**
- `/home/abathur/quantum-deploy/src/runtime/execution_context.py` (deploy service base)
- Container `quantum-llm-demo:/app/src/runtime/execution_context.py`

---

## Deploy

### Infraestrutura no Forge

- Ollama: `http://10.10.1.40:11434` com modelo `phi3:latest`
- Deploy service: `/home/abathur/quantum-deploy/` (uvicorn)
- Container: `quantum-llm-demo` (Docker, porta 8080, proxy via nginx)
- URL publica: `http://10.10.1.40/llm-demo/`

### Arquivos atualizados no forge via SFTP

1. `src/runtime/llm_service.py` (novo)
2. `src/runtime/component.py`
3. `src/runtime/web_server.py`
4. `src/runtime/execution_context.py`
5. `src/core/ast_nodes.py`
6. `src/core/parser.py`

---

## Testes

- 4 exemplos LLM (`examples/llm_demo.q`) executados localmente com sucesso
- Chat interativo testado no forge com multi-turn conversation
- Suite de testes existente: 335 passed, 80 skipped, 3 pre-existing failures (nenhum relacionado a LLM)

---

## Pendencias

- [ ] Admin panel para configuracao LLM (endpoints, UI, models list)
- [ ] Passar config LLM do `quantum.config.yaml` para o `LLMService` (atualmente usa env vars ou atributo `endpoint` na tag)
- [ ] Enviar historico completo ao LLM para respostas com contexto de conversa
- [ ] Suporte a streaming de respostas (SSE)
