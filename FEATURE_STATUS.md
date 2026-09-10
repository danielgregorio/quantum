# FEATURE_STATUS — gerado, não escrito

> **Não edite este arquivo.** Ele é produzido por
> `python scripts/generate-feature-status.py`, medindo o motor.
> Tabelas de status escritas à mão apodrecem.

**40 tags `q:` registradas · 29 executores · 154 exemplos executados · IA ao vivo: não.**

Colunas: **tier** vem de `quantum/core/tiers.py`. **exemplos**: arquivos em
`examples/` e `components/` que usam a tag. **parseia**: pelo menos um deles
passa no parser. **executa**: dos exemplos executáveis, quantos o
`quantum run` executa sem erro, numa cópia temporária do repositório (só
Core e IA; alvos interativos e tags experimentais não são executados).
**testes** e **docs**: arquivos que mencionam a tag.

## Core (12 tags)

| Tag | Exemplos | Parseia | Executa | Testes | Docs |
|---|---|---|---|---|---|
| `q:action` | 29 | sim | 12/12 (17 não executados) | 11 | 9 |
| `q:data` | 7 | sim | 7/7 | 5 | 5 |
| `q:flash` | 6 | sim | 3/3 (3 não executados) | 1 | 5 |
| `q:function` | 64 | sim | **23/46** (18 não executados) | 16 | 27 |
| `q:if` | 52 | sim | 25/25 (27 não executados) | 19 | 31 |
| `q:import` | 2 | sim | 2/2 | 1 | 4 |
| `q:invoke` | 8 | sim | 4/4 (4 não executados) | 7 | 6 |
| `q:loop` | 54 | sim | 30/30 (24 não executados) | 12 | 26 |
| `q:query` | 21 | sim | **8/9** (12 não executados) | 14 | 17 |
| `q:redirect` | 17 | sim | 7/7 (10 não executados) | 4 | 7 |
| `q:set` | 143 | sim | **83/107** (36 não executados) | 39 | 37 |
| `q:slot` | 2 | sim | — (2 não executados) | 1 | 2 |

## Diferencial (4 tags)

| Tag | Exemplos | Parseia | Executa | Testes | Docs |
|---|---|---|---|---|---|
| `q:agent` | 4 | sim | — (4 não executados) | 9 | 4 |
| `q:knowledge` | 2 | sim | — (2 não executados) | 3 | 3 |
| `q:llm` | 1 | sim | — (1 não executados) | 5 | 3 |
| `q:team` | 2 | sim | — (2 não executados) | 4 | 2 |

## Experimental (24 tags)

| Tag | Exemplos | Parseia | Testes | Docs |
|---|---|---|---|---|
| `q:class` | 2 | sim | 2 | 0 |
| `q:decorator` | 1 | sim | 1 | 0 |
| `q:dispatchEvent` | 0 | — sem exemplo | 0 | 1 |
| `q:dump` | 6 | sim | 1 | 1 |
| `q:file` | 4 | sim | 4 | 2 |
| `q:job` | 2 | sim | 7 | 2 |
| `q:log` | 13 | sim | 4 | 3 |
| `q:mail` | 10 | sim | 1 | 3 |
| `q:message` | 4 | sim | 4 | 2 |
| `q:messageAck` | 2 | sim | 2 | 0 |
| `q:messageNack` | 2 | sim | 2 | 0 |
| `q:persist` | 1 | sim | 1 | 2 |
| `q:pyclass` | 0 | — sem exemplo | 1 | 0 |
| `q:pydecorator` | 0 | — sem exemplo | 0 | 0 |
| `q:pyimport` | 2 | sim | 2 | 0 |
| `q:python` | 15 | sim | 7 | 1 |
| `q:queue` | 3 | sim | 3 | 0 |
| `q:schedule` | 2 | sim | 4 | 1 |
| `q:subscribe` | 3 | sim | 3 | 0 |
| `q:thread` | 2 | sim | 3 | 0 |
| `q:transaction` | 4 | sim | 3 | 4 |
| `q:websocket` | 1 | sim | 5 | 1 |
| `q:websocket-close` | 1 | sim | 1 | 0 |
| `q:websocket-send` | 1 | sim | 1 | 0 |

## Exemplos Core/IA que não executam

| Arquivo | Resultado | Primeira linha de erro |
|---|---|---|
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
| `examples/test-query-insert.q` | erro | [ERROR] Execution error: Execution error: Query execution error in 'insertResult': Query execution failed: UNIQUE constraint failed: users.email |

## Não executados, e por quê

- 49 arquivo(s): usa tag experimental
- 5 arquivo(s): usa IA (rode com --live-ai)
- 5 arquivo(s): alvo interativo (ui)
- 5 arquivo(s): fragmento, não é arquivo raiz (q:behavior)
- 4 arquivo(s): componente exige parâmetros
- 3 arquivo(s): alvo interativo (terminal)
- 2 arquivo(s): precisa do banco do admin
- 1 arquivo(s): fragmento, não é arquivo raiz (qg:scene)

## Lacunas que esta medição expõe

- **3 tags sem nenhum exemplo**: `q:dispatchEvent`, `q:pyclass`, `q:pydecorator`.
- **0 tags cujos exemplos não parseiam**: nenhuma.
- **24 exemplos Core/IA que não executam** (tabela acima).
