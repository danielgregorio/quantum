# FEATURE_STATUS — gerado, não escrito

> **Não edite este arquivo.** Ele é produzido por
> `python scripts/generate-feature-status.py`, medindo o motor.
> Tabelas de status escritas à mão apodrecem.

**40 tags `q:` registradas · 29 executores · 157 exemplos executados · IA ao vivo: não.**

Colunas: **tier** vem de `quantum/core/tiers.py`. **exemplos**: arquivos em
`examples/` e `components/` que usam a tag. **parseia**: pelo menos um deles
passa no parser. **executa**: dos exemplos executáveis, quantos o
`quantum run` executa sem erro, numa cópia temporária do repositório (só
Core e IA; alvos interativos e tags experimentais não são executados).
**testes** e **docs**: arquivos que mencionam a tag.

## Core (12 tags)

| Tag | Exemplos | Parseia | Executa | Testes | Docs |
|---|---|---|---|---|---|
| `q:action` | 29 | sim | 12/12 (17 não executados) | 10 | 5 |
| `q:data` | 7 | sim | 7/7 | 3 | 3 |
| `q:flash` | 6 | sim | 3/3 (3 não executados) | 0 | 3 |
| `q:function` | 66 | sim | **24/48** (18 não executados) | 12 | 27 |
| `q:if` | 54 | sim | **26/27** (27 não executados) | 14 | 31 |
| `q:import` | 2 | sim | 2/2 | 1 | 3 |
| `q:invoke` | 9 | sim | **4/5** (4 não executados) | 5 | 3 |
| `q:loop` | 55 | sim | **30/31** (24 não executados) | 8 | 27 |
| `q:query` | 22 | sim | **9/10** (12 não executados) | 9 | 17 |
| `q:redirect` | 17 | sim | 7/7 (10 não executados) | 3 | 5 |
| `q:set` | 145 | sim | **83/109** (36 não executados) | 29 | 34 |
| `q:slot` | 2 | sim | — (2 não executados) | 1 | 2 |

## Diferencial (4 tags)

| Tag | Exemplos | Parseia | Executa | Testes | Docs |
|---|---|---|---|---|---|
| `q:agent` | 4 | sim | — (4 não executados) | 8 | 3 |
| `q:knowledge` | 2 | sim | — (2 não executados) | 2 | 2 |
| `q:llm` | 1 | sim | — (1 não executados) | 4 | 2 |
| `q:team` | 2 | sim | — (2 não executados) | 4 | 1 |

## Experimental (24 tags)

| Tag | Exemplos | Parseia | Testes | Docs |
|---|---|---|---|---|
| `q:class` | 2 | sim | 2 | 0 |
| `q:decorator` | 1 | sim | 1 | 0 |
| `q:dispatchEvent` | 0 | — sem exemplo | 0 | 2 |
| `q:dump` | 6 | sim | 1 | 1 |
| `q:file` | 4 | sim | 4 | 2 |
| `q:job` | 2 | sim | 6 | 3 |
| `q:log` | 13 | sim | 4 | 3 |
| `q:mail` | 10 | sim | 1 | 3 |
| `q:message` | 4 | sim | 3 | 1 |
| `q:messageAck` | 2 | sim | 2 | 0 |
| `q:messageNack` | 2 | sim | 2 | 0 |
| `q:persist` | 1 | sim | 1 | 2 |
| `q:pyclass` | 0 | — sem exemplo | 1 | 0 |
| `q:pydecorator` | 0 | — sem exemplo | 0 | 0 |
| `q:pyimport` | 2 | sim | 2 | 0 |
| `q:python` | 15 | sim | 7 | 1 |
| `q:queue` | 3 | sim | 3 | 0 |
| `q:schedule` | 2 | sim | 3 | 1 |
| `q:subscribe` | 3 | sim | 3 | 0 |
| `q:thread` | 2 | sim | 3 | 0 |
| `q:transaction` | 4 | sim | 2 | 4 |
| `q:websocket` | 1 | sim | 5 | 2 |
| `q:websocket-close` | 1 | sim | 1 | 0 |
| `q:websocket-send` | 1 | sim | 1 | 0 |

## Exemplos Core/IA que não executam

| Arquivo | Resultado | Primeira linha de erro |
|---|---|---|
| `components/products.q` | erro | [ERROR] Execution error: Execution error: Set execution error for 'products': Type conversion error to 'array': Expecting property name enclosed in double quote |
| `components/smw_polished.q` | erro | [ERROR] Validation errors: - Invalid type: float. Must be one of ['string', 'number', 'integer', 'decimal', 'boolean', 'date', 'datetime', 'array', 'object', 'j |
| `components/snake.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/mario.q` | erro | [ERROR] Validation errors: - Invalid type: float. Must be one of ['string', 'number', 'integer', 'decimal', 'boolean', 'date', 'datetime', 'array', 'object', 'j |
| `examples/platformer.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/10_hud_score.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/11_enemies.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/14_multi_scene.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/15_question_blocks.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/16_stomp_detection.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/17_powerups.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/18_enemies.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/18_enemy_ai.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/19_checkpoints.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/20_full_level.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/mario/05_coins.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/mario/06_blocks.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/mario/07_enemies.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/mario/08_hud.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/mario/09_death.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/progressive/mario/10_complete.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/smw_polished.q` | erro | [ERROR] Validation errors: - Invalid type: float. Must be one of ['string', 'number', 'integer', 'decimal', 'boolean', 'date', 'datetime', 'array', 'object', 'j |
| `examples/smw_world1.q` | erro | [ERROR] Validation errors: - Invalid type: float. Must be one of ['string', 'number', 'integer', 'decimal', 'boolean', 'date', 'datetime', 'array', 'object', 'j |
| `examples/snake.q` | erro | [ERROR] Validation errors: - Sprite id is required |
| `examples/test-invoke-function.q` | erro | 2026-09-10 14:11:15 [ERROR] q:invoke function='calculateSum' failed |
| `examples/test-query-insert.q` | erro | [ERROR] Execution error: Execution error: Query execution error in 'insertResult': Query execution failed: UNIQUE constraint failed: users.email |

## Não executados, e por quê

- 49 arquivo(s): usa tag experimental
- 5 arquivo(s): usa IA (rode com --live-ai)
- 5 arquivo(s): alvo interativo (ui)
- 5 arquivo(s): fragmento, não é arquivo raiz (q:behavior)
- 4 arquivo(s): componente exige parâmetros
- 3 arquivo(s): alvo interativo (terminal)
- 2 arquivo(s): precisa do banco do admin
- 1 arquivo(s): alvo interativo (microservices)
- 1 arquivo(s): alvo interativo (html)
- 1 arquivo(s): fragmento, não é arquivo raiz (qg:scene)

## Cobertura dos módulos do núcleo

Linhas cobertas pela suíte (`pytest --cov=quantum --cov-report=json`).

| Módulo | Cobertura | Linhas |
|---|---|---|
| `quantum/runtime/component.py` | 65% | 277/428 |
| `quantum/core/expressions.py` | 92% | 262/285 |
| `quantum/runtime/execution_context.py` | 75% | 116/155 |
| `quantum/runtime/renderer.py` | 84% | 215/257 |
| `quantum/core/parser.py` | 84% | 549/656 |
| `quantum/runtime/executors/control_flow/` | 92% | 424/461 |
| `quantum/runtime/executors/data/` | 99% | 277/281 |
| `quantum/runtime/executors/ai/` | 89% | 228/257 |
| `quantum/core/parsers/control_flow/` | 98% | 121/123 |
| `quantum/core/parsers/data/` | 95% | 301/318 |
| `quantum/core/parsers/ai/` | 92% | 137/149 |
| `quantum/runtime/llm_service.py` | 16% | 18/113 |
| `quantum/runtime/knowledge_service.py` | 11% | 24/225 |
| `quantum/runtime/agent_service.py` | 80% | 341/428 |
| **núcleo inteiro** | **80%** | 3290/4136 |

**Meta para o 1.0: 90%.** Módulos abaixo dela: `quantum/runtime/component.py`, `quantum/runtime/execution_context.py`, `quantum/runtime/renderer.py`, `quantum/core/parser.py`, `quantum/runtime/executors/ai/`, `quantum/runtime/llm_service.py`, `quantum/runtime/knowledge_service.py`, `quantum/runtime/agent_service.py`.

## Lacunas que esta medição expõe

- **3 tags sem nenhum exemplo**: `q:dispatchEvent`, `q:pyclass`, `q:pydecorator`.
- **0 tags cujos exemplos não parseiam**: nenhuma.
- **26 exemplos Core/IA que não executam** (tabela acima).
