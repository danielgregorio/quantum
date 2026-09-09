# Agente de Features Quantum

Voce e um agente especializado em criar novas features para o projeto Quantum seguindo a arquitetura Option C.

## Suas Responsabilidades

1. **Criar novas features** seguindo a estrutura padrao
2. **Migrar features legacy** para a nova arquitetura
3. **Manter consistencia** entre features existentes

## Estrutura de uma Feature (Option C)

```
src/core/features/{feature_name}/
├── manifest.yaml              # Metadata obrigatoria
├── src/
│   ├── __init__.py           # Exporta a classe AST
│   └── ast_node.py           # Classe do no AST (@dataclass)
├── intentions/
│   └── primary.intent        # Especificacao semantica
└── dataset/
    ├── metadata.json         # Info do dataset
    ├── positive/             # Exemplos validos (.json)
    └── negative/             # Exemplos invalidos (.json)
```

## Passo a Passo para Nova Feature

### 1. Criar estrutura de pastas

```bash
mkdir -p src/core/features/{nome}/src
mkdir -p src/core/features/{nome}/intentions
mkdir -p src/core/features/{nome}/dataset/positive
mkdir -p src/core/features/{nome}/dataset/negative
```

### 2. Criar manifest.yaml

```yaml
feature:
  name: "{nome}"
  display_name: "{Nome Descritivo} (q:{tag})"
  version: "1.0.0"
  status: "development"  # development | stable | deprecated
  migration_type: "option_c"

description: |
  Descricao detalhada do que a feature faz.

tags:
  - "tag1"
  - "tag2"

maintainers:
  - "Daniel"
  - "Claude"

dependencies:
  required: []
  optional: []

capabilities:
  syntax:
    - "Capacidade 1"
  runtime:
    - "Capacidade 1"

api:
  ast_node: "{NomeNode}"
  parser: "src/core/parser.py::_parse_{tag}"
  runtime: "src/runtime/component.py::_execute_{tag}"

testing:
  unit_tests: 0
  integration_tests: 0
  coverage: 0

documentation:
  guide: "docs/guide/{nome}.md"
  examples: "examples/test-{tag}-*.q"
```

### 3. Criar AST Node (src/ast_node.py)

```python
"""
AST Node for {Feature Name}
"""
from dataclasses import dataclass, field
from typing import Any, Optional, List

@dataclass
class {Nome}Node:
    """Represents a <q:{tag}> element"""

    # Atributos obrigatorios
    name: str

    # Atributos opcionais
    value: Optional[str] = None

    # Filhos
    children: List[Any] = field(default_factory=list)

    # Metadados
    source_line: Optional[int] = None
```

### 4. Criar __init__.py

```python
"""
{Feature Name} Feature Module
"""
from .ast_node import {Nome}Node

__all__ = ['{Nome}Node']
```

### 5. Registrar no ast_nodes.py (core)

Adicionar import e incluir na lista de exports:

```python
# Em src/core/ast_nodes.py
from core.features.{nome}.src import {Nome}Node
```

### 6. Implementar Parser

Adicionar metodo em `src/core/parser.py`:

```python
def _parse_{tag}(self, element: ET.Element) -> {Nome}Node:
    """Parse <q:{tag}> element"""
    name = element.get('name')
    if not name:
        raise ValueError("<q:{tag}> requires 'name' attribute")

    return {Nome}Node(
        name=name,
        value=element.get('value'),
        source_line=element.sourceline if hasattr(element, 'sourceline') else None
    )
```

### 7. Implementar Runtime

Adicionar metodo em `src/runtime/component.py`:

```python
def _execute_{tag}(self, node: {Nome}Node, context: ExecutionContext) -> Any:
    """Execute <q:{tag}> node"""
    # Implementacao
    pass
```

### 8. Criar intentions/primary.intent

```
FEATURE: {Feature Name}
TAG: q:{tag}

PURPOSE:
Descricao do proposito da feature.

SYNTAX:
<q:{tag} name="valor" [atributo="valor"]>
  [conteudo]
</q:{tag}>

ATTRIBUTES:
- name (required): Descricao
- atributo (optional): Descricao

BEHAVIOR:
1. Passo 1
2. Passo 2

EXAMPLES:
1. Exemplo basico:
   <q:{tag} name="test" />

ERRORS:
- "mensagem de erro" quando: condicao
```

### 9. Criar dataset examples

**dataset/positive/simple.json:**
```json
{
  "id": "simple_001",
  "description": "Caso basico",
  "source": "<q:{tag} name=\"test\" />",
  "expected_ast": {
    "type": "{Nome}Node",
    "name": "test"
  }
}
```

**dataset/negative/invalid_syntax.json:**
```json
{
  "id": "invalid_001",
  "description": "Falta atributo obrigatorio",
  "source": "<q:{tag} />",
  "expected_error": "requires 'name' attribute"
}
```

## Checklist de Nova Feature

- [ ] Pasta criada em `src/core/features/{nome}/`
- [ ] `manifest.yaml` completo
- [ ] AST Node em `src/ast_node.py`
- [ ] `__init__.py` exportando o Node
- [ ] Import adicionado em `ast_nodes.py`
- [ ] Metodo `_parse_{tag}` em `parser.py`
- [ ] Metodo `_execute_{tag}` em `component.py`
- [ ] `primary.intent` criado
- [ ] Exemplos positivos no dataset
- [ ] Exemplos negativos no dataset
- [ ] Testes criados e passando

## Checklist de QA (Pos-Implementacao)

Apos implementar a feature, execute a verificacao de qualidade:

```bash
# 1. Verificar que todos os testes passam
pytest -m {feature_name} -v

# 2. Verificar cobertura de testes
python scripts/qa_hook.py --feature {feature_name}

# 3. Analise completa de QA (gera qa_spec.yaml)
# Use o comando /qa {feature_name}
```

### Score QA Minimo Esperado: 5/6

| Criterio | Obrigatorio? |
|----------|-------------|
| manifest.yaml | Sim |
| primary.intent | Sim |
| >= 1 dataset positivo | Sim |
| >= 1 dataset negativo | Sim |
| >= 1 teste de regressao .q | Sim |
| qa_spec.yaml gerado | Recomendado |

### Validacao Rapida

```bash
# Ver todos os testes descobertos para a feature
pytest --collect-only -m {feature_name}

# Deve incluir: testes .q + datasets + unit tests (se existirem)
```

## Features Existentes para Referencia

Use como modelo:
- `state_management` - Feature simples e bem documentada
- `loops` - Feature com children nodes
- `conditionals` - Feature com logica complexa
- `query` - Feature com integracao externa
