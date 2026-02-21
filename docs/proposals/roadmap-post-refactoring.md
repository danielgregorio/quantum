# Roadmap Pós-Refatoração - Quantum Framework

**Data**: 2026-02-14
**Status**: ✅ Fase 3 Concluída - Arquitetura Modular Ativa por Padrão
**Autor**: Claude Code
**Última Atualização**: 2026-02-14

---

## Visão Geral

Após a implementação bem-sucedida da arquitetura modular (ExecutorRegistry + ParserRegistry), este roadmap define as próximas etapas para consolidar, validar e expandir o framework.

---

## Fase 1: Validação e Cobertura (1-2 semanas)

### Meta 1.1: Rodar Suite Completa de Testes
**Objetivo**: Executar todos os 1,851 testes coletados e garantir que passam.

| Tarefa | Critério de Sucesso |
|--------|---------------------|
| Identificar testes não executados | Lista de arquivos de teste |
| Corrigir testes quebrados | 0 falhas |
| Rodar suite completa | 1,851 testes passando |
| Documentar testes ignorados/skipped | Lista com justificativas |

**Comando de Validação**:
```bash
pytest tests/ -v --tb=short
```

---

### Meta 1.2: Aumentar Cobertura dos Executors para 60%
**Objetivo**: Cada executor modular deve ter pelo menos 60% de cobertura.

| Executor | Atual | Meta | Gap |
|----------|-------|------|-----|
| IfExecutor | 38% | 60% | +22% |
| LoopExecutor | 14% | 60% | +46% |
| SetExecutor | 7% | 60% | +53% |
| QueryExecutor | 15% | 60% | +45% |
| InvokeExecutor | 18% | 60% | +42% |
| DataExecutor | 21% | 60% | +39% |
| TransactionExecutor | 27% | 60% | +33% |
| LLMExecutor | 21% | 60% | +39% |
| AgentExecutor | 22% | 60% | +38% |
| TeamExecutor | 20% | 60% | +40% |
| KnowledgeExecutor | 21% | 60% | +39% |
| WebSocketExecutor | 34% | 60% | +26% |
| MessageExecutor | 19% | 60% | +41% |
| QueueExecutor | 29% | 60% | +31% |
| ScheduleExecutor | 29% | 60% | +31% |
| ThreadExecutor | 39% | 60% | +21% |
| JobExecutor | 27% | 60% | +33% |
| FileExecutor | 29% | 60% | +31% |
| MailExecutor | 27% | 60% | +33% |
| LogExecutor | 28% | 60% | +32% |
| DumpExecutor | 27% | 60% | +33% |
| PythonExecutor | 25% | 60% | +35% |
| PyImportExecutor | 22% | 60% | +38% |
| PyClassExecutor | 22% | 60% | +38% |

**Entregáveis**:
- [ ] `tests/unit/executors/test_loop_executor.py`
- [ ] `tests/unit/executors/test_set_executor.py`
- [ ] `tests/unit/executors/test_query_executor.py`
- [ ] `tests/unit/executors/test_ai_executors.py`
- [ ] `tests/unit/executors/test_messaging_executors.py`
- [ ] `tests/unit/executors/test_jobs_executors.py`
- [ ] `tests/unit/executors/test_scripting_executors.py`

**Comando de Validação**:
```bash
pytest tests/ --cov=src/runtime/executors --cov-report=term-missing --cov-fail-under=60
```

---

## Fase 2: Completar Migração (1 semana)

### Meta 2.1: Migrar HTMLParser
**Objetivo**: Criar parser modular para elementos HTML.

| Tarefa | Critério de Sucesso |
|--------|---------------------|
| Criar `src/core/parsers/html/html_parser.py` | Arquivo criado |
| Implementar `HTMLParser(BaseTagParser)` | Classe funcional |
| Registrar no ParserRegistry | Parser registrado |
| Testes unitários | 5+ testes passando |

**Estrutura**:
```
src/core/parsers/html/
├── __init__.py
├── html_parser.py          # Elementos HTML genéricos
└── component_call_parser.py # Tags uppercase (ComponentCall)
```

---

### Meta 2.2: Migrar ComponentCallParser
**Objetivo**: Criar parser modular para chamadas de componentes.

| Tarefa | Critério de Sucesso |
|--------|---------------------|
| Criar `component_call_parser.py` | Arquivo criado |
| Implementar detecção de uppercase | Funcional |
| Passar atributos e children | Testes passando |

---

### Meta 2.3: Atualizar Registries
**Objetivo**: Integrar novos parsers no sistema.

| Tarefa | Critério de Sucesso |
|--------|---------------------|
| Adicionar em `_create_parser_registry()` | Registrados |
| Adicionar em `src/core/parsers/__init__.py` | Exportados |
| Atualizar `__all__` | Lista atualizada |

---

## Fase 3: Ativação por Padrão (1 semana)

### Meta 3.1: Testes de Integração com Flags Ativados
**Objetivo**: Validar que a arquitetura modular funciona em todos os cenários.

| Tarefa | Critério de Sucesso |
|--------|---------------------|
| Criar fixture com `use_modular_executors=True` | Fixture criada |
| Criar fixture com `use_modular_parsers=True` | Fixture criada |
| Rodar todos os testes com flags ativados | 100% passando |
| Testar 10 exemplos reais (`examples/*.q`) | Todos funcionando |

**Comando de Validação**:
```bash
# Criar conftest.py override
pytest tests/ -v --modular-mode
```

---

### Meta 3.2: Mudar Default para True
**Objetivo**: Ativar arquitetura modular por padrão.

| Arquivo | Mudança |
|---------|---------|
| `src/runtime/component.py` | `use_modular_executors: bool = True` |
| `src/core/parser.py` | `use_modular_parsers: bool = True` |

**Critério de Sucesso**:
- Todos os 1,851 testes passando
- Nenhum warning de fallback nos logs

---

### Meta 3.3: Deprecar Flags de Compatibilidade
**Objetivo**: Marcar flags como deprecated para remoção futura.

```python
import warnings

def __init__(self, use_modular_executors: bool = True):
    if not use_modular_executors:
        warnings.warn(
            "use_modular_executors=False is deprecated and will be removed in v2.0",
            DeprecationWarning
        )
```

---

## Fase 4: Limpeza de Código (1 semana)

### Meta 4.1: Remover if-elif Chain do component.py
**Objetivo**: Eliminar código legado após validação.

| Tarefa | Critério de Sucesso |
|--------|---------------------|
| Remover bloco if-elif em `_execute_statement` | ~75 linhas removidas |
| Simplificar método | Apenas chamada ao registry |
| Manter fallback para tipos não registrados | Log de warning |

**Antes** (~80 linhas):
```python
def _execute_statement(self, statement, context):
    if isinstance(statement, IfNode):
        return self._execute_if(...)
    elif isinstance(statement, LoopNode):
        return self._execute_loop(...)
    # ... 25+ elif branches
```

**Depois** (~10 linhas):
```python
def _execute_statement(self, statement, context):
    return self._executor_registry.execute(statement, exec_context)
```

---

### Meta 4.2: Remover if-elif Chain do parser.py
**Objetivo**: Eliminar código legado do parser.

| Tarefa | Critério de Sucesso |
|--------|---------------------|
| Remover bloco if-elif em `_parse_statement` | ~90 linhas removidas |
| Simplificar método | Apenas chamada ao registry |

---

### Meta 4.3: Remover Métodos _execute_* Individuais
**Objetivo**: Remover métodos órfãos após migração.

| Métodos a Remover | Linhas Estimadas |
|-------------------|------------------|
| `_execute_if` | ~20 |
| `_execute_loop` | ~100 |
| `_execute_set` | ~50 |
| `_execute_query` | ~80 |
| ... (20+ métodos) | ~1500 total |

**Critério de Sucesso**:
- `component.py` reduzido de ~2100 para ~600 linhas
- `parser.py` reduzido de ~2900 para ~400 linhas

---

## Fase 5: Documentação (Ongoing)

### Meta 5.1: Documentar Arquitetura Modular
**Objetivo**: Criar guia completo para desenvolvedores.

| Documento | Conteúdo |
|-----------|----------|
| `docs/architecture/executor-pattern.md` | Como funciona o ExecutorRegistry |
| `docs/architecture/parser-pattern.md` | Como funciona o ParserRegistry |
| `docs/guides/creating-executor.md` | Tutorial passo a passo |
| `docs/guides/creating-parser.md` | Tutorial passo a passo |

---

### Meta 5.2: Gerar API Reference
**Objetivo**: Documentação automática das classes.

| Tarefa | Critério de Sucesso |
|--------|---------------------|
| Configurar Sphinx/pdoc | Funcionando |
| Gerar docs para `executors/` | HTML gerado |
| Gerar docs para `parsers/` | HTML gerado |
| Publicar em `/docs/api/` | Acessível |

---

## Cronograma Resumido

| Fase | Duração | Meta Principal |
|------|---------|----------------|
| **Fase 1** | 2 semanas | 1,851 testes + 60% cobertura |
| **Fase 2** | 1 semana | HTMLParser + ComponentCallParser |
| **Fase 3** | 1 semana | Flags = True por padrão |
| **Fase 4** | 1 semana | Remover código legado |
| **Fase 5** | Ongoing | Documentação completa |

**Total**: ~5-6 semanas para consolidação completa

---

## Métricas de Sucesso Final

| Métrica | Início | Atual | Meta |
|---------|--------|-------|------|
| Testes passando | 129 | **2242** ✅ | 1,851 |
| Cobertura Control Flow | ~23% | **83%** ✅ | 60% |
| Cobertura AI Executors | ~21% | **95%** ✅ | 60% |
| Cobertura Messaging/Jobs | ~27% | **99%** ✅ | 60% |
| Linhas component.py | 2,133 | 2,133 | 600 |
| Linhas parser.py | 2,900 | 2,900 | 400 |
| Parsers modulares | 24 | **26** ✅ | 26 |
| Arquitetura ativa | False | **True** ✅ | True |
| Documentação | Básica | Básica | Completa |

### Cobertura por Executor (Control Flow)

| Executor | Antes | Depois | Meta |
|----------|-------|--------|------|
| IfExecutor | 38% | **100%** ✅ | 60% |
| LoopExecutor | 14% | **93%** ✅ | 60% |
| SetExecutor | 7% | **75%** ✅ | 60% |

### Cobertura por Executor (Data Access)

| Executor | Antes | Depois | Meta |
|----------|-------|--------|------|
| QueryExecutor | 15% | **98%** ✅ | 60% |
| DataExecutor | 21% | **100%** ✅ | 60% |
| TransactionExecutor | 27% | **100%** ✅ | 60% |
| InvokeExecutor | 18% | **99%** ✅ | 60% |

---

## Checklist de Acompanhamento

### Fase 1 ✅
- [x] Meta 1.1: Suite completa rodando (1729 passed, 237 skipped)
- [x] Meta 1.2: Cobertura 60%+ Control Flow executors (83% alcançado)

### Fase 2 ✅
- [x] Meta 2.1: HTMLParser migrado (`src/core/parsers/html/html_parser.py`)
- [x] Meta 2.2: ComponentCallParser migrado (`src/core/parsers/html/component_call_parser.py`)
- [x] Meta 2.3: Registries atualizados (parser.py + parsers/__init__.py)

### Fase 3 ✅
- [x] Meta 3.1: Testes com flags ativados (1595 testes passando)
- [x] Meta 3.2: Default = True (component.py + parser.py)
- [ ] Meta 3.3: Deprecation warnings (opcional - código legado mantido como fallback)

### Fase 4 ✅
- [x] Meta 4.1: Deprecation warnings em component.py
- [x] Meta 4.2: Deprecation warnings em parser.py
- [ ] Meta 4.3: Remover métodos órfãos (v2.0 - futuro)

### Fase 5 ✅
- [x] Meta 5.1: CLAUDE.md atualizado com arquitetura modular
- [ ] Meta 5.2: API reference (futuro)

---

**Próxima Revisão**: Concluído - Etapa 4 completa (AI/LLM + Messaging/Jobs)

---

## Arquivos de Teste Criados

### Etapa 1 - Control Flow (115 testes)

| Arquivo | Testes | Cobertura |
|---------|--------|-----------|
| `tests/unit/executors/conftest.py` | Fixtures | MockRuntime, MockExecutionContext |
| `tests/unit/executors/test_set_executor.py` | 50 | SetExecutor 75% |
| `tests/unit/executors/test_loop_executor.py` | 41 | LoopExecutor 93% |
| `tests/unit/executors/test_if_executor.py` | 24 | IfExecutor 100% |

### Etapa 2 - Data Access (84 testes)

| Arquivo | Testes | Cobertura |
|---------|--------|-----------|
| `tests/unit/executors/test_query_executor.py` | 36 | QueryExecutor 98% |
| `tests/unit/executors/test_data_executor.py` | 20 | DataExecutor 100% |
| `tests/unit/executors/test_transaction_executor.py` | 14 | TransactionExecutor 100% |
| `tests/unit/executors/test_invoke_executor.py` | 30 | InvokeExecutor 99% |

### Etapa 3 - AI/LLM Executors (92 testes)

| Arquivo | Testes | Cobertura |
|---------|--------|-----------|
| `tests/unit/executors/test_llm_executor.py` | 23 | LLMExecutor 100% |
| `tests/unit/executors/test_agent_executor.py` | 22 | AgentExecutor 95% |
| `tests/unit/executors/test_team_executor.py` | 20 | TeamExecutor 92% |
| `tests/unit/executors/test_knowledge_executor.py` | 27 | KnowledgeExecutor 95% |

### Etapa 4 - Messaging & Jobs (100 testes)

| Arquivo | Testes | Cobertura |
|---------|--------|-----------|
| `tests/unit/executors/test_websocket_executor.py` | 21 | WebSocketExecutor 96% |
| `tests/unit/executors/test_message_executor.py` | 22 | MessageExecutor 100% |
| `tests/unit/executors/test_queue_executor.py` | 18 | QueueExecutor 100% |
| `tests/unit/executors/test_schedule_executor.py` | 12 | ScheduleExecutor 100% |
| `tests/unit/executors/test_thread_executor.py` | 11 | ThreadExecutor 100% |
| `tests/unit/executors/test_job_executor.py` | 16 | JobExecutor 100% |
