# Proposta de Refatoracao: component.py e parser.py

**Data**: 2026-02-14
**Status**: ✅ IMPLEMENTADO
**Autor**: Claude Code
**Implementado em**: 2026-02-14

---

## Resumo Executivo

Proposta para quebrar os dois maiores arquivos monoliticos do projeto:
- `component.py` (4077 linhas) -> ~400 linhas + modulos executores
- `parser.py` (2861 linhas) -> ~300 linhas + modulos parsers

**Beneficios esperados**:
- Melhor manutenibilidade
- Testes unitarios mais focados
- Onboarding mais facil
- Reducao de conflitos de merge
- Melhor IDE support (autocomplete, go to definition)

---

## PARTE 1: Refatoracao do component.py

### Problema Atual

```
component.py (4077 linhas)
├── 50+ metodos _execute_*
├── Grande bloco if-elif para dispatch (75 linhas)
├── Multiplos servicos injetados no __init__
├── Logica de databinding misturada com execucao
└── Dificil testar metodos isoladamente
```

### Arquitetura Proposta: Executor Pattern

```
src/runtime/
├── component.py              # Orquestrador (400 linhas)
├── execution_context.py      # (existente)
├── executor_registry.py      # Registry de executores (NOVO)
│
├── executors/                # Modulos de execucao (NOVO)
│   ├── __init__.py
│   ├── base.py               # BaseExecutor abstract class
│   │
│   ├── control_flow/         # Controle de fluxo
│   │   ├── __init__.py
│   │   ├── if_executor.py
│   │   ├── loop_executor.py
│   │   └── set_executor.py
│   │
│   ├── data/                 # Operacoes de dados
│   │   ├── __init__.py
│   │   ├── query_executor.py
│   │   ├── invoke_executor.py
│   │   ├── data_executor.py
│   │   └── transaction_executor.py
│   │
│   ├── ai/                   # IA e LLM
│   │   ├── __init__.py
│   │   ├── llm_executor.py
│   │   ├── agent_executor.py
│   │   ├── team_executor.py
│   │   └── knowledge_executor.py
│   │
│   ├── messaging/            # Comunicacao
│   │   ├── __init__.py
│   │   ├── websocket_executor.py
│   │   ├── message_executor.py
│   │   └── queue_executor.py
│   │
│   ├── jobs/                 # Execucao assincrona
│   │   ├── __init__.py
│   │   ├── schedule_executor.py
│   │   ├── thread_executor.py
│   │   └── job_executor.py
│   │
│   ├── services/             # Servicos externos
│   │   ├── __init__.py
│   │   ├── file_executor.py
│   │   ├── mail_executor.py
│   │   ├── log_executor.py
│   │   └── dump_executor.py
│   │
│   └── scripting/            # Python scripting
│       ├── __init__.py
│       ├── python_executor.py
│       ├── pyimport_executor.py
│       └── pyclass_executor.py
│
└── databinding/              # Separar logica de databinding (NOVO)
    ├── __init__.py
    ├── expression_evaluator.py
    └── condition_evaluator.py
```

### Implementacao: Base Executor

```python
# src/runtime/executors/base.py
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.execution_context import ExecutionContext
    from runtime.component import ComponentRuntime

class BaseExecutor(ABC):
    """Base class for all node executors"""

    def __init__(self, runtime: 'ComponentRuntime'):
        self.runtime = runtime
        self.context = runtime.execution_context

    @property
    @abstractmethod
    def handles(self) -> list[type]:
        """List of AST node types this executor handles"""
        pass

    @abstractmethod
    def execute(self, node: Any, exec_context: 'ExecutionContext') -> Any:
        """Execute the node and return result"""
        pass

    # Helper methods (moved from ComponentRuntime)
    def apply_databinding(self, value: str, context: dict) -> Any:
        return self.runtime._apply_databinding(value, context)

    def evaluate_condition(self, condition: str, context: dict) -> bool:
        return self.runtime._evaluate_condition(condition, context)

    def get_all_variables(self) -> dict:
        return self.context.get_all_variables()
```

### Implementacao: Executor Registry

```python
# src/runtime/executor_registry.py
from typing import Dict, Type, Any
from runtime.executors.base import BaseExecutor

class ExecutorRegistry:
    """Registry for node executors - replaces if-elif chain"""

    def __init__(self):
        self._executors: Dict[Type, BaseExecutor] = {}

    def register(self, executor: BaseExecutor):
        """Register executor for its handled node types"""
        for node_type in executor.handles:
            self._executors[node_type] = executor

    def get_executor(self, node: Any) -> BaseExecutor:
        """Get executor for a node type"""
        node_type = type(node)
        if node_type in self._executors:
            return self._executors[node_type]
        raise ValueError(f"No executor registered for {node_type.__name__}")

    def execute(self, node: Any, exec_context) -> Any:
        """Execute node using registered executor"""
        executor = self.get_executor(node)
        return executor.execute(node, exec_context)
```

### Exemplo: LoopExecutor

```python
# src/runtime/executors/control_flow/loop_executor.py
from typing import Any, Dict, List
from runtime.executors.base import BaseExecutor
from core.features.loops.src.ast_node import LoopNode

class LoopExecutor(BaseExecutor):
    """Executor for q:loop statements"""

    @property
    def handles(self) -> list[type]:
        return [LoopNode]

    def execute(self, node: LoopNode, exec_context) -> Any:
        """Execute loop based on type"""
        if node.loop_type == 'range':
            return self._execute_range(node, exec_context)
        elif node.loop_type == 'array':
            return self._execute_array(node, exec_context)
        elif node.loop_type == 'list':
            return self._execute_list(node, exec_context)
        elif node.loop_type == 'query':
            return self._execute_query(node, exec_context)
        else:
            raise ValueError(f"Unknown loop type: {node.loop_type}")

    def _execute_range(self, node: LoopNode, exec_context) -> List:
        results = []
        context = self.get_all_variables()

        start = int(self._evaluate_value(node.from_value, context))
        end = int(self._evaluate_value(node.to_value, context))
        step = node.step_value

        for i in range(start, end + 1, step):
            exec_context.set_variable(node.var_name, i, scope="local")

            for statement in node.body:
                result = self.runtime.executor_registry.execute(
                    statement, exec_context
                )
                if result is not None:
                    results.append(result)

        return results

    # ... outros metodos de loop
```

### Novo component.py (Simplificado)

```python
# src/runtime/component.py (~400 linhas)
"""Quantum Component Runtime - Orchestrator"""

from typing import Any, Dict
from runtime.execution_context import ExecutionContext
from runtime.executor_registry import ExecutorRegistry
from runtime.executors import (
    # Control flow
    IfExecutor, LoopExecutor, SetExecutor,
    # Data
    QueryExecutor, InvokeExecutor, DataExecutor, TransactionExecutor,
    # AI
    LLMExecutor, AgentExecutor, TeamExecutor, KnowledgeExecutor,
    # Messaging
    WebSocketExecutor, MessageExecutor, QueueExecutor,
    # Jobs
    ScheduleExecutor, ThreadExecutor, JobExecutor,
    # Services
    FileExecutor, MailExecutor, LogExecutor, DumpExecutor,
    # Scripting
    PythonExecutor, PyImportExecutor, PyClassExecutor,
)

class ComponentRuntime:
    """Runtime orchestrator for Quantum components"""

    def __init__(self, config: Dict[str, Any] = None):
        self.execution_context = ExecutionContext()
        self.config = config or {}

        # Initialize services (moved to ServiceContainer)
        self.services = ServiceContainer(config)

        # Initialize executor registry
        self.executor_registry = ExecutorRegistry()
        self._register_executors()

    def _register_executors(self):
        """Register all node executors"""
        executors = [
            IfExecutor(self),
            LoopExecutor(self),
            SetExecutor(self),
            QueryExecutor(self),
            InvokeExecutor(self),
            # ... all other executors
        ]
        for executor in executors:
            self.executor_registry.register(executor)

    def execute_component(self, component: ComponentNode, params: Dict = None):
        """Execute a component"""
        # Setup (validation, scopes)
        self._setup_execution(component, params)

        # Execute statements using registry
        for statement in component.statements:
            result = self.executor_registry.execute(statement, self.execution_context)
            if self._should_return(statement, result):
                return result

        # Process returns
        return self._process_returns(component)

    # Databinding methods (shared by all executors)
    def _apply_databinding(self, value: str, context: dict) -> Any:
        # ... existing databinding logic
        pass

    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        # ... existing condition logic
        pass
```

### Migracao Incremental

**Fase 1** (1 semana): Infraestrutura
1. Criar `executors/base.py` com `BaseExecutor`
2. Criar `executor_registry.py`
3. Criar `ServiceContainer` para injecao de dependencias
4. Todos os testes continuam passando

**Fase 2** (2 semanas): Migracao por Categoria
1. Migrar `control_flow/` (if, loop, set)
2. Migrar `data/` (query, invoke, data)
3. Migrar `ai/` (llm, agent, team)
4. Migrar `messaging/` (websocket, message, queue)
5. Migrar `jobs/` (schedule, thread, job)
6. Migrar `services/` (file, mail, log, dump)
7. Migrar `scripting/` (python, pyimport, pyclass)

**Fase 3** (1 semana): Cleanup
1. Remover metodos antigos de `component.py`
2. Atualizar imports
3. Adicionar type hints completos
4. Atualizar documentacao

---

## PARTE 2: Refatoracao do parser.py

### Problema Atual

```
parser.py (2861 linhas)
├── 60+ metodos _parse_*
├── Grande bloco elif em _parse_control_flow_statements
├── Imports de todas as features no topo
├── Mistura de parsing generico e especifico
└── Dificil adicionar novas tags
```

### Arquitetura Proposta: Parser Modular

```
src/core/
├── parser.py                 # Parser principal (300 linhas)
├── parser_registry.py        # Registry de tag parsers (NOVO)
│
├── parsers/                  # Modulos de parsing (NOVO)
│   ├── __init__.py
│   ├── base.py               # BaseTagParser abstract class
│   │
│   ├── core/                 # Tags core
│   │   ├── __init__.py
│   │   ├── component_parser.py
│   │   ├── application_parser.py
│   │   └── job_parser.py
│   │
│   ├── control_flow/         # Controle de fluxo
│   │   ├── __init__.py
│   │   ├── if_parser.py
│   │   ├── loop_parser.py
│   │   └── set_parser.py
│   │
│   ├── data/                 # Operacoes de dados
│   │   ├── __init__.py
│   │   ├── query_parser.py
│   │   ├── invoke_parser.py
│   │   ├── data_parser.py
│   │   └── transaction_parser.py
│   │
│   ├── ai/                   # IA e LLM
│   │   ├── __init__.py
│   │   ├── llm_parser.py
│   │   ├── agent_parser.py
│   │   ├── team_parser.py
│   │   └── knowledge_parser.py
│   │
│   ├── messaging/            # Comunicacao
│   │   ├── __init__.py
│   │   ├── websocket_parser.py
│   │   ├── message_parser.py
│   │   └── queue_parser.py
│   │
│   ├── jobs/                 # Jobs
│   │   ├── __init__.py
│   │   ├── schedule_parser.py
│   │   ├── thread_parser.py
│   │   └── job_inline_parser.py
│   │
│   ├── services/             # Servicos
│   │   ├── __init__.py
│   │   ├── file_parser.py
│   │   ├── mail_parser.py
│   │   ├── log_parser.py
│   │   └── dump_parser.py
│   │
│   ├── scripting/            # Python
│   │   ├── __init__.py
│   │   ├── python_parser.py
│   │   └── pyimport_parser.py
│   │
│   └── html/                 # HTML rendering
│       ├── __init__.py
│       └── html_parser.py
│
└── features/                 # (existente - manter estrutura atual)
    └── {feature}/src/
        ├── ast_node.py
        └── parser.py         # Parser especifico da feature (opcional)
```

### Implementacao: Base Tag Parser

```python
# src/core/parsers/base.py
from abc import ABC, abstractmethod
from typing import Optional, List, TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from core.ast_nodes import QuantumNode

class BaseTagParser(ABC):
    """Base class for tag-specific parsers"""

    def __init__(self, main_parser: 'QuantumParser'):
        self.parser = main_parser

    @property
    @abstractmethod
    def tag_names(self) -> List[str]:
        """List of tag names this parser handles (without q: prefix)"""
        pass

    @abstractmethod
    def parse(self, element: ET.Element) -> 'QuantumNode':
        """Parse the element and return AST node"""
        pass

    # Helper methods (delegated to main parser)
    def get_element_name(self, element: ET.Element) -> str:
        return self.parser._get_element_name(element)

    def find_element(self, parent: ET.Element, tag: str) -> Optional[ET.Element]:
        return self.parser._find_element(parent, tag)

    def find_all_elements(self, parent: ET.Element, tag: str) -> List[ET.Element]:
        return self.parser._find_all_elements(parent, tag)

    def parse_statement(self, element: ET.Element) -> Optional['QuantumNode']:
        """Parse a child statement using the registry"""
        return self.parser.parse_statement(element)

    def parse_statements(self, parent: ET.Element) -> List['QuantumNode']:
        """Parse all child statements"""
        statements = []
        for child in parent:
            node = self.parse_statement(child)
            if node:
                statements.append(node)
        return statements
```

### Implementacao: Parser Registry

```python
# src/core/parser_registry.py
from typing import Dict, List, Optional, TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from core.parsers.base import BaseTagParser
    from core.ast_nodes import QuantumNode

class ParserRegistry:
    """Registry for tag parsers - replaces if-elif chain"""

    def __init__(self):
        self._parsers: Dict[str, 'BaseTagParser'] = {}
        self._html_parser: Optional['BaseTagParser'] = None

    def register(self, parser: 'BaseTagParser'):
        """Register parser for its handled tags"""
        for tag_name in parser.tag_names:
            self._parsers[tag_name] = parser

    def register_html_parser(self, parser: 'BaseTagParser'):
        """Register fallback HTML parser"""
        self._html_parser = parser

    def get_parser(self, tag_name: str) -> Optional['BaseTagParser']:
        """Get parser for a tag name"""
        return self._parsers.get(tag_name)

    def parse(self, element: ET.Element, tag_name: str) -> Optional['QuantumNode']:
        """Parse element using registered parser"""
        parser = self._parsers.get(tag_name)
        if parser:
            return parser.parse(element)
        return None

    def can_parse(self, tag_name: str) -> bool:
        """Check if we have a parser for this tag"""
        return tag_name in self._parsers

    def is_uppercase(self, tag_name: str) -> bool:
        """Check if tag is a component call (uppercase)"""
        return tag_name and tag_name[0].isupper()
```

### Exemplo: LoopParser

```python
# src/core/parsers/control_flow/loop_parser.py
from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser
from core.features.loops.src.ast_node import LoopNode

class LoopParser(BaseTagParser):
    """Parser for q:loop statements"""

    @property
    def tag_names(self) -> List[str]:
        return ['loop']

    def parse(self, element: ET.Element) -> LoopNode:
        """Parse q:loop element"""
        # Check for query shorthand
        query_attr = element.get('query')

        if query_attr:
            loop_node = LoopNode('query', query_attr)
            loop_node.query_name = query_attr
        else:
            loop_type = element.get('type', 'range')
            var_name = element.get('var')

            if not var_name:
                raise QuantumParseError("Loop requires 'var' attribute")

            loop_node = LoopNode(loop_type, var_name)

            # Parse type-specific attributes
            if loop_type == 'range':
                self._parse_range_attrs(element, loop_node)
            elif loop_type in ('array', 'list'):
                self._parse_collection_attrs(element, loop_node)

        # Parse body statements
        loop_node.body = self.parse_statements(element)

        return loop_node

    def _parse_range_attrs(self, element: ET.Element, node: LoopNode):
        node.from_value = element.get('from', '1')
        node.to_value = element.get('to', '10')
        node.step_value = int(element.get('step', '1'))

    def _parse_collection_attrs(self, element: ET.Element, node: LoopNode):
        node.items = element.get('items', '')
        node.index_name = element.get('index')
```

### Novo parser.py (Simplificado)

```python
# src/core/parser.py (~300 linhas)
"""Quantum Parser - Main entry point"""

from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

from core.parser_registry import ParserRegistry
from core.ast_nodes import QuantumNode, ComponentNode, ApplicationNode
from core.parsers import (
    # Core
    ComponentParser, ApplicationParser, JobParser,
    # Control flow
    IfParser, LoopParser, SetParser,
    # Data
    QueryParser, InvokeParser, DataParser, TransactionParser,
    # AI
    LLMParser, AgentParser, TeamParser, KnowledgeParser,
    # Messaging
    WebSocketParser, MessageParser, QueueParser,
    # Jobs
    ScheduleParser, ThreadParser, JobInlineParser,
    # Services
    FileParser, MailParser, LogParser, DumpParser,
    # Scripting
    PythonParser, PyImportParser,
    # HTML
    HTMLParser, ComponentCallParser,
)

class QuantumParser:
    """Main parser for .q files"""

    def __init__(self, use_cache: bool = True):
        self.quantum_ns = {'q': 'https://quantum.lang/ns'}
        self._use_cache = use_cache
        self._init_cache()

        # Initialize parser registry
        self.registry = ParserRegistry()
        self._register_parsers()

    def _register_parsers(self):
        """Register all tag parsers"""
        parsers = [
            # Core
            ComponentParser(self),
            ApplicationParser(self),
            JobParser(self),
            # Control flow
            IfParser(self),
            LoopParser(self),
            SetParser(self),
            # ... all other parsers
        ]
        for parser in parsers:
            self.registry.register(parser)

        # Register special parsers
        self.registry.register_html_parser(HTMLParser(self))

    def parse(self, source: str) -> QuantumNode:
        """Parse Quantum XML from string"""
        content = self._inject_namespace(source)
        root = ET.fromstring(content)
        return self._parse_root(root)

    def parse_file(self, file_path: str) -> QuantumNode:
        """Parse .q file"""
        # Cache logic...
        source = Path(file_path).read_text(encoding="utf-8")
        return self.parse(source)

    def _parse_root(self, root: ET.Element) -> QuantumNode:
        """Parse root element"""
        tag = self._get_element_name(root)
        parser = self.registry.get_parser(tag)
        if parser:
            return parser.parse(root)
        raise QuantumParseError(f"Unknown root element: {tag}")

    def parse_statement(self, element: ET.Element) -> Optional[QuantumNode]:
        """Parse a statement element (used by tag parsers)"""
        tag = self._get_element_name(element)

        # Try registered parsers first
        if self.registry.can_parse(tag):
            return self.registry.parse(element, tag)

        # Component calls (uppercase)
        if self.registry.is_uppercase(tag):
            return self.registry.parse_component_call(element)

        # HTML fallback
        if self._is_html_element(element):
            return self.registry.parse_html(element)

        return None

    # Helper methods (used by all parsers)
    def _get_element_name(self, element: ET.Element) -> str:
        return element.tag.split('}')[-1] if '}' in element.tag else element.tag.split(':')[-1]

    def _find_element(self, parent: ET.Element, tag: str) -> Optional[ET.Element]:
        return parent.find(f"q:{tag}", self.quantum_ns) or parent.find(tag)

    def _find_all_elements(self, parent: ET.Element, tag: str) -> list:
        return self.registry._find_all(parent, tag, self.quantum_ns)

    def _inject_namespace(self, content: str) -> str:
        # ... existing namespace injection
        pass

    def _is_html_element(self, element: ET.Element) -> bool:
        # ... existing HTML detection
        pass
```

### Migracao Incremental

**Fase 1** (3 dias): Infraestrutura
1. Criar `parsers/base.py`
2. Criar `parser_registry.py`
3. Testes passando

**Fase 2** (1 semana): Migracao
1. Migrar `control_flow/` (if, loop, set)
2. Migrar `data/` (query, invoke, data)
3. Migrar `ai/` (llm, agent, team, knowledge)
4. Migrar `messaging/` (websocket, message, queue)
5. Migrar `jobs/` (schedule, thread, job)
6. Migrar `services/` (file, mail, log, dump)
7. Migrar `scripting/` (python, pyimport)
8. Migrar `html/` (html, component_call)

**Fase 3** (2 dias): Cleanup
1. Remover metodos antigos
2. Atualizar imports
3. Documentar

---

## PARTE 3: Alternativa - Feature-Centric Architecture

### Conceito

Ao inves de separar por tipo (parser vs executor), organizar por **feature**:

```
src/core/features/{feature_name}/
├── manifest.yaml          # Metadata
├── src/
│   ├── __init__.py
│   ├── ast_node.py        # Node classes
│   ├── parser.py          # Tag parsing     <- NOVO
│   └── executor.py        # Node execution  <- NOVO
├── intentions/
│   └── primary.intent
└── dataset/
    ├── positive/
    └── negative/
```

### Exemplo: loops/

```
src/core/features/loops/
├── manifest.yaml
├── src/
│   ├── __init__.py
│   ├── ast_node.py        # LoopNode class (existente)
│   ├── parser.py          # LoopParser (NOVO)
│   └── executor.py        # LoopExecutor (NOVO)
├── intentions/
│   └── primary.intent
└── dataset/
    ├── positive/
    └── negative/
```

### Vantagens Feature-Centric

1. **Coesao**: Tudo sobre loops esta junto
2. **Plugin-like**: Facil adicionar/remover features
3. **Testing**: Testar feature inteira isoladamente
4. **Documentation**: Docs junto com codigo

### Desvantagens

1. **Mais complexidade inicial**
2. **Precisa refatorar estrutura existente**
3. **Imports mais profundos**

---

## PARTE 4: Recomendacao

### Opcao Recomendada: Executor Pattern + Parser Modular

**Por que?**
1. Menor impacto na estrutura existente de features
2. Separacao clara de responsabilidades
3. Registry pattern ja e comum em Python
4. Permite migracao incremental
5. Mantem compatibilidade com Option C existente

### Cronograma Sugerido

```
Semana 1: Infraestrutura
├── Criar BaseExecutor + ExecutorRegistry
├── Criar BaseTagParser + ParserRegistry
├── Criar ServiceContainer
└── Testes de integracao

Semana 2-3: Migracao Executors
├── control_flow/ (if, loop, set)
├── data/ (query, invoke, data, transaction)
├── ai/ (llm, agent, team, knowledge)
├── messaging/ (websocket, message, queue)
├── jobs/ (schedule, thread, job)
├── services/ (file, mail, log, dump)
└── scripting/ (python, pyimport, pyclass)

Semana 4: Migracao Parsers
├── control_flow/
├── data/
├── ai/
├── messaging/
├── jobs/
├── services/
└── scripting/

Semana 5: Cleanup
├── Remover codigo antigo
├── Type hints 100%
├── Documentacao
└── Code review
```

### Metricas de Sucesso

| Metrica | Antes | Depois |
|---------|-------|--------|
| component.py | 4077 linhas | ~400 linhas |
| parser.py | 2861 linhas | ~300 linhas |
| Maior arquivo | 4077 linhas | ~200 linhas |
| Testes unitarios | Por feature | Por executor |
| Cyclomatic complexity | Alta | Baixa |

---

## Apendice A: Diagrama de Dependencias

```
┌─────────────────────────────────────────────────────────┐
│                    QuantumParser                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │              ParserRegistry                      │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐           │   │
│  │  │IfParser │ │LoopPars │ │QueryPar │ ...       │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘           │   │
│  └───────┼───────────┼───────────┼─────────────────┘   │
└──────────┼───────────┼───────────┼─────────────────────┘
           │           │           │
           ▼           ▼           ▼
     ┌─────────┐ ┌─────────┐ ┌─────────┐
     │ IfNode  │ │LoopNode │ │QueryNode│  (AST)
     └────┬────┘ └────┬────┘ └────┬────┘
          │           │           │
          ▼           ▼           ▼
┌─────────────────────────────────────────────────────────┐
│                  ComponentRuntime                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │              ExecutorRegistry                    │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐           │   │
│  │  │IfExec   │ │LoopExec │ │QueryExe │ ...       │   │
│  │  └─────────┘ └─────────┘ └─────────┘           │   │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │              ServiceContainer                    │   │
│  │  DatabaseService, LLMService, EmailService...   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Apendice B: Checklist de Implementacao

### Infraestrutura
- [x] Criar `src/runtime/executors/__init__.py`
- [x] Criar `src/runtime/executors/base.py`
- [x] Criar `src/runtime/executor_registry.py`
- [x] Criar `src/runtime/service_container.py`
- [x] Criar `src/core/parsers/__init__.py`
- [x] Criar `src/core/parsers/base.py`
- [x] Criar `src/core/parser_registry.py`
- [x] Atualizar `tests/conftest.py` com novas fixtures

### Migracao Executors
- [x] IfExecutor
- [x] LoopExecutor
- [x] SetExecutor
- [x] QueryExecutor
- [x] InvokeExecutor
- [x] DataExecutor
- [x] TransactionExecutor
- [x] LLMExecutor
- [x] AgentExecutor
- [x] TeamExecutor
- [x] KnowledgeExecutor
- [x] WebSocketExecutor (+ WebSocketSendExecutor, WebSocketCloseExecutor)
- [x] MessageExecutor
- [x] QueueExecutor (+ SubscribeExecutor)
- [x] ScheduleExecutor
- [x] ThreadExecutor
- [x] JobExecutor
- [x] FileExecutor
- [x] MailExecutor
- [x] LogExecutor
- [x] DumpExecutor
- [x] PythonExecutor
- [x] PyImportExecutor
- [x] PyClassExecutor

### Migracao Parsers
- [x] IfParser
- [x] LoopParser
- [x] SetParser
- [x] QueryParser
- [x] InvokeParser
- [x] DataParser
- [x] TransactionParser
- [x] LLMParser
- [x] AgentParser
- [x] TeamParser
- [x] KnowledgeParser
- [x] WebSocketParser (+ WebSocketSendParser, WebSocketCloseParser)
- [x] MessageParser
- [x] QueueParser (+ SubscribeParser)
- [x] ScheduleParser
- [x] ThreadParser
- [x] JobParser
- [x] FileParser
- [x] MailParser
- [x] LogParser
- [x] DumpParser
- [x] PythonParser
- [x] PyImportParser
- [x] PyClassParser
- [ ] HTMLParser (pendente - usando legado)
- [ ] ComponentCallParser (pendente - usando legado)

### Cleanup
- [x] Integrar ExecutorRegistry em component.py (use_modular_executors flag)
- [x] Integrar ParserRegistry em parser.py (use_modular_parsers flag)
- [x] Manter compatibilidade retroativa (fallback para if-elif legado)
- [x] Atualizar CLAUDE.md
- [x] 98 testes para nova arquitetura
- [x] 129 testes de regressao passando

---

**Proposta criada em**: 2026-02-14
**Proxima revisao**: Apos aprovacao
