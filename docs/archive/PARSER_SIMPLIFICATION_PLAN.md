# Quantum — Operacao Guilhotina: Parser.py

## Contexto

O arquivo `src/core/parser.py` e o segundo monolito do Quantum, com **2.906 linhas** de codigo. A arquitetura modular ja existe (`src/core/parsers/`), mas o codigo legado ainda esta presente como fallback.

A Fase 3 da Operacao Guilhotina no `component.py` reduziu o arquivo de 4.207 para 948 linhas (-77%). Este documento planeja a mesma operacao para o `parser.py`.

## Estado Atual

### Linhas de Codigo
- **parser.py**: 2.906 linhas
- **Meta**: ~400-600 linhas (-80%)

### Arquitetura Modular Existente

```
src/core/parsers/
├── base.py                    # BaseTagParser abstract class
├── __init__.py                # Exports
├── control_flow/
│   ├── if_parser.py           # tag: if
│   ├── loop_parser.py         # tag: loop
│   └── set_parser.py          # tag: set
├── data/
│   ├── query_parser.py        # tag: query
│   ├── invoke_parser.py       # tag: invoke
│   ├── data_parser.py         # tag: data
│   └── transaction_parser.py  # tag: transaction
├── services/
│   ├── log_parser.py          # tag: log
│   ├── dump_parser.py         # tag: dump
│   ├── file_parser.py         # tag: file
│   └── mail_parser.py         # tag: mail
├── ai/
│   ├── llm_parser.py          # tag: llm
│   ├── agent_parser.py        # tag: agent
│   ├── team_parser.py         # tag: team
│   └── knowledge_parser.py    # tag: knowledge
├── messaging/
│   ├── websocket_parser.py    # tags: websocket, websocket-send, websocket-close
│   ├── message_parser.py      # tags: message, subscribe
│   └── queue_parser.py        # tag: queue
├── jobs/
│   ├── schedule_parser.py     # tag: schedule
│   ├── thread_parser.py       # tag: thread
│   └── job_parser.py          # tag: job
├── scripting/
│   ├── python_parser.py       # tag: python
│   ├── pyimport_parser.py     # tag: pyimport
│   └── pyclass_parser.py      # tags: class, pyclass
└── html/
    ├── html_parser.py         # HTML elements
    └── component_call_parser.py # Uppercase component calls
```

## Analise de Gaps

### Tags Cobertas por Parsers Modulares (26 tags)

| Categoria | Tags |
|-----------|------|
| control_flow | `if`, `loop`, `set` |
| data | `query`, `invoke`, `data`, `transaction` |
| services | `log`, `dump`, `file`, `mail` |
| ai | `llm`, `agent`, `team`, `knowledge` |
| messaging | `websocket`, `websocket-send`, `websocket-close`, `message`, `subscribe`, `queue` |
| jobs | `schedule`, `thread`, `job` |
| scripting | `python`, `pyimport`, `class`/`pyclass` |
| html | HTML elements, Component calls (uppercase) |

### Tags NAO Cobertas - Requerem Novos Parsers (14 tags)

| Categoria | Tags | Prioridade | Complexidade |
|-----------|------|------------|--------------|
| forms_actions | `action`, `redirect`, `flash` | Alta | Media |
| component_composition | `import`, `slot` | Alta | Baixa |
| persistence | `persist` | Media | Baixa |
| events | `dispatchEvent` | Media | Baixa |
| messaging_extra | `messageAck`, `messageNack` | Media | Baixa |
| scripting_extra | `decorator`/`pydecorator` | Baixa | Media |
| functions | `function`, `return` | Alta | Media |
| routing | `route` | Media | Baixa |
| params | `param` | Alta | Baixa |

## Plano de Execucao

### Fase 1: Criar Parsers Modulares Faltantes

**Objetivo:** Criar os 14 parsers modulares que faltam para cobrir todas as tags.

#### 1.1 Forms & Actions (Prioridade Alta)
Criar `src/core/parsers/forms/`:
- `action_parser.py` - tag: `action`
- `redirect_parser.py` - tag: `redirect`
- `flash_parser.py` - tag: `flash`

```python
# Exemplo: action_parser.py
class ActionParser(BaseTagParser):
    @property
    def tag_names(self) -> List[str]:
        return ['action']

    def parse(self, element: ET.Element) -> ActionNode:
        # Copiar logica de _parse_action_statement()
        pass
```

#### 1.2 Component Composition (Prioridade Alta)
Criar `src/core/parsers/composition/`:
- `import_parser.py` - tag: `import`
- `slot_parser.py` - tag: `slot`

#### 1.3 Functions (Prioridade Alta)
Criar `src/core/parsers/functions/`:
- `function_parser.py` - tag: `function`
- `return_parser.py` - tag: `return`
- `param_parser.py` - tag: `param`

#### 1.4 Events (Prioridade Media)
Criar `src/core/parsers/events/`:
- `dispatch_event_parser.py` - tag: `dispatchEvent`
- `on_event_parser.py` - tag: `onEvent` (se necessario)

#### 1.5 Persistence (Prioridade Media)
Criar `src/core/parsers/persistence/`:
- `persist_parser.py` - tag: `persist`

#### 1.6 Routing (Prioridade Media)
Criar `src/core/parsers/routing/`:
- `route_parser.py` - tag: `route`

#### 1.7 Messaging Extra (Prioridade Media)
Adicionar ao `src/core/parsers/messaging/message_parser.py`:
- `MessageAckParser` - tag: `messageAck`
- `MessageNackParser` - tag: `messageNack`

#### 1.8 Scripting Extra (Prioridade Baixa)
Criar `src/core/parsers/scripting/pydecorator_parser.py`:
- tag: `decorator`, `pydecorator`

### Fase 2: Registrar Novos Parsers

**Objetivo:** Registrar todos os novos parsers no ParserRegistry.

Atualizar `src/core/parser_registry.py`:

```python
def _register_parsers(self):
    # Existentes...

    # Novos parsers
    from core.parsers.forms import ActionParser, RedirectParser, FlashParser
    from core.parsers.composition import ImportParser, SlotParser
    from core.parsers.functions import FunctionParser, ReturnParser, ParamParser
    from core.parsers.events import DispatchEventParser
    from core.parsers.persistence import PersistParser
    from core.parsers.routing import RouteParser

    self.register(ActionParser(self))
    self.register(RedirectParser(self))
    # ... etc
```

### Fase 3: Validar Cobertura

**Objetivo:** Confirmar que todos os testes passam com os novos parsers.

```bash
# Desabilitar fallback legado (ja feito)
python -m pytest tests/ --tb=short -q

# Esperado: 2025 passed, 4 failed (pre-existentes), 237 skipped
```

### Fase 4: Remover Codigo Legado

**Objetivo:** Remover todos os metodos `_parse_*_statement` legados.

#### 4.1 Metodos a Remover (~2000 linhas)

| Metodo | Linha | Substituido Por |
|--------|-------|-----------------|
| `_parse_if_statement` | 554 | IfParser |
| `_parse_loop_statement` | 595 | LoopParser |
| `_parse_set_statement` | 654 | SetParser |
| `_parse_query_statement` | 1273 | QueryParser |
| `_parse_query_param` | 1383 | QueryParser |
| `_parse_invoke_statement` | 1418 | InvokeParser |
| `_parse_invoke_header` | 1496 | InvokeParser |
| `_parse_data_statement` | 1508 | DataParser |
| `_parse_column` | 1567 | DataParser |
| `_parse_field` | 1616 | DataParser |
| `_parse_transform` | 1629 | DataParser |
| `_parse_filter` | 1651 | DataParser |
| `_parse_sort` | 1660 | DataParser |
| `_parse_limit` | 1670 | DataParser |
| `_parse_compute` | 1684 | DataParser |
| `_parse_data_header` | 1697 | DataParser |
| `_parse_html_element` | 1759 | HTMLParser |
| `_parse_import_statement` | 1802 | ImportParser |
| `_parse_slot_statement` | 1835 | SlotParser |
| `_parse_component_call` | 1867 | ComponentCallParser |
| `_parse_action_statement` | 1907 | ActionParser |
| `_parse_redirect_statement` | 1948 | RedirectParser |
| `_parse_flash_statement` | 1964 | FlashParser |
| `_parse_file_statement` | 1982 | FileParser |
| `_parse_mail_statement` | 2006 | MailParser |
| `_parse_transaction_statement` | 2053 | TransactionParser |
| `_parse_llm_statement` | 2090 | LLMParser |
| `_parse_agent_statement` | 2162 | AgentParser |
| `_parse_agent_tool` | 2230 | AgentParser |
| `_parse_team_statement` | 2262 | TeamParser |
| `_parse_websocket_statement` | 2351 | WebSocketParser |
| `_parse_websocket_handler` | 2428 | WebSocketParser |
| `_parse_websocket_send` | 2440 | WebSocketSendParser |
| `_parse_websocket_close` | 2464 | WebSocketCloseParser |
| `_parse_persist_statement` | 2495 | PersistParser |
| `_parse_message_statement` | 2547 | MessageParser |
| `_parse_subscribe_statement` | 2604 | SubscribeParser |
| `_parse_queue_statement` | 2664 | QueueParser |
| `_parse_message_ack_statement` | 2703 | MessageAckParser |
| `_parse_message_nack_statement` | 2717 | MessageNackParser |
| `_parse_python_statement` | 2735 | PythonParser |
| `_parse_pyimport_statement` | 2782 | PyImportParser |
| `_parse_pyclass_statement` | 2809 | PyClassParser |
| `_parse_pydecorator_statement` | 2855 | PyDecoratorParser |

#### 4.2 Metodos a Manter

| Metodo | Linha | Razao |
|--------|-------|-------|
| `_parse_root_element` | 319 | Dispatcher principal |
| `_parse_component` | 356 | Parse de componente |
| `_parse_control_flow_statements` | 410 | Orquestrador (sera simplificado) |
| `_parse_statement` | 711 | Dispatcher para registry |
| `_parse_application` | 738 | Parse de aplicacao |
| `_parse_*_application_children` | 778+ | Especificos de tipo |
| `_parse_job` | 906 | Parse de job file |
| `_parse_param` | 1042 | Usado por multiplos parsers |
| `_parse_return` | 1085 | Parse de return |
| `_parse_route` | 1094 | Parse de route |
| `_parse_function` | 1108 | Parse de funcao |
| `_parse_dispatch_event` | 1205 | Parse de evento |
| `_parse_on_event` | 1226 | Parse de handler |
| `_get_element_name` | - | Helper |
| `_is_html_element` | - | Helper |

#### 4.3 Simplificar `_parse_control_flow_statements`

De ~140 linhas para ~15 linhas:

```python
def _parse_control_flow_statements(self, parent: ET.Element, component: ComponentNode):
    """Parse control flow statements - delegates to modular parser registry"""
    for child in parent:
        node = self._parse_statement(child)
        if node is not None:
            component.add_statement(node)
            # Check if this produces HTML
            child_type = self._get_element_name(child)
            if self._is_html_element(child) or (child_type and child_type[0].isupper()):
                component.has_html = True
```

### Fase 5: Validacao Final

```bash
# Rodar suite completa
python -m pytest tests/ --tb=short -q

# Verificar metricas
wc -l src/core/parser.py  # Meta: <600 linhas

# Verificar warnings
python -c "from core.parser import QuantumParser; p = QuantumParser()"
# Nenhum warning de fallback
```

## Cronograma Sugerido

| Fase | Descricao | Estimativa |
|------|-----------|------------|
| 1.1-1.3 | Parsers Alta Prioridade | Sessao 1 |
| 1.4-1.8 | Parsers Media/Baixa Prioridade | Sessao 2 |
| 2 | Registrar Parsers | Sessao 2 |
| 3 | Validar Cobertura | Sessao 2 |
| 4 | Remover Codigo Legado | Sessao 3 |
| 5 | Validacao Final | Sessao 3 |

## Metricas de Sucesso

- [ ] `parser.py` reduzido de 2.906 para <600 linhas
- [ ] 2.025+ testes passando (mesmos 4 failures pre-existentes)
- [ ] Zero warnings de fallback legado nos logs
- [ ] Nenhum metodo `_parse_*_statement` legado remanescente
- [ ] Todos os 14 novos parsers modulares criados e testados

## Riscos e Mitigacoes

| Risco | Probabilidade | Impacto | Mitigacao |
|-------|---------------|---------|-----------|
| Parser modular com comportamento diferente do legado | Media | Alto | Copiar logica exata do metodo legado; testes unitarios |
| Tags especiais nao cobertas | Baixa | Medio | Manter metodos legados para casos edge |
| Regressao em parsing complexo (team, agent) | Media | Alto | Testes E2E antes de remover legado |
| Conflito de imports circulares | Baixa | Baixo | Imports dentro das funcoes |

## Arquivos a Criar

```
src/core/parsers/
├── forms/
│   ├── __init__.py
│   ├── action_parser.py
│   ├── redirect_parser.py
│   └── flash_parser.py
├── composition/
│   ├── __init__.py
│   ├── import_parser.py
│   └── slot_parser.py
├── functions/
│   ├── __init__.py
│   ├── function_parser.py
│   ├── return_parser.py
│   └── param_parser.py
├── events/
│   ├── __init__.py
│   └── dispatch_event_parser.py
├── persistence/
│   ├── __init__.py
│   └── persist_parser.py
└── routing/
    ├── __init__.py
    └── route_parser.py
```

## Dependencias Entre Parsers

Alguns parsers dependem de metodos auxiliares que precisam ser mantidos ou movidos:

```
FunctionParser
└── depende de: _parse_param (manter em parser.py ou mover para ParamParser)

TeamParser
└── depende de: _parse_set_statement (agora usa SetParser via registry)

AgentParser
└── depende de: _parse_agent_tool (mover para dentro de AgentParser)

QueryParser
└── depende de: _parse_query_param (mover para dentro de QueryParser)

DataParser
└── depende de: _parse_column, _parse_field, etc. (mover para dentro de DataParser)
```

## Checklist de Execucao

### Pre-Requisitos
- [ ] Commit do estado atual do parser.py
- [ ] Branch separada para a operacao

### Fase 1: Criar Parsers
- [ ] forms/action_parser.py
- [ ] forms/redirect_parser.py
- [ ] forms/flash_parser.py
- [ ] composition/import_parser.py
- [ ] composition/slot_parser.py
- [ ] functions/function_parser.py
- [ ] functions/return_parser.py
- [ ] events/dispatch_event_parser.py
- [ ] persistence/persist_parser.py
- [ ] routing/route_parser.py
- [ ] messaging/message_ack_parser.py (ou adicionar ao message_parser.py)
- [ ] messaging/message_nack_parser.py (ou adicionar ao message_parser.py)
- [ ] scripting/pydecorator_parser.py

### Fase 2: Registrar
- [ ] Atualizar parser_registry.py
- [ ] Atualizar __init__.py de cada modulo

### Fase 3: Validar
- [ ] pytest tests/ passa com 2025+ testes

### Fase 4: Remover Legado
- [ ] Remover metodos _parse_*_statement
- [ ] Simplificar _parse_control_flow_statements
- [ ] Remover imports nao utilizados

### Fase 5: Validar
- [ ] pytest tests/ passa com 2025+ testes
- [ ] wc -l parser.py mostra <600 linhas
- [ ] Nenhum warning de fallback

---

*Documento criado como parte da Operacao Guilhotina para o Quantum Framework.*
