# FEATURE_STATUS — gerado, não escrito

> **Não edite este arquivo.** Ele é produzido por
> `python scripts/generate-feature-status.py`, medindo o motor.
> Tabelas de status escritas à mão apodrecem — este repositório tem
> manifests marcando como "planned" features já implementadas e uma
> página de docs ensinando uma tag que nenhum parser registra.

**40 tags `q:` registradas · 29 executores.**

Colunas: **tier** vem de `quantum/core/tiers.py` (a superfície que o
motor de fato impõe). **exemplos** conta arquivos em `examples/` e
`components/` que usam a tag. **parseia** diz se pelo menos um desses
arquivos passa no parser — é um proxy honesto e barato; execução
completa exigiria banco, Ollama e rede, então esta coluna não afirma
mais do que mediu.

## Core (12 tags)

| Tag | Exemplos | Parseia |
|---|---|---|
| `q:action` | 29 | sim |
| `q:data` | 7 | sim |
| `q:flash` | 6 | sim |
| `q:function` | 66 | sim |
| `q:if` | 54 | sim |
| `q:import` | 2 | sim |
| `q:invoke` | 9 | sim |
| `q:loop` | 55 | sim |
| `q:query` | 22 | sim |
| `q:redirect` | 17 | sim |
| `q:set` | 145 | sim |
| `q:slot` | 2 | sim |

## Diferencial (4 tags)

| Tag | Exemplos | Parseia |
|---|---|---|
| `q:agent` | 4 | sim |
| `q:knowledge` | 2 | sim |
| `q:llm` | 1 | sim |
| `q:team` | 2 | sim |

## Experimental (24 tags)

| Tag | Exemplos | Parseia |
|---|---|---|
| `q:class` | 2 | sim |
| `q:decorator` | 1 | sim |
| `q:dispatchEvent` | 0 | — sem exemplo |
| `q:dump` | 6 | sim |
| `q:file` | 4 | sim |
| `q:job` | 2 | sim |
| `q:log` | 13 | sim |
| `q:mail` | 10 | sim |
| `q:message` | 4 | sim |
| `q:messageAck` | 2 | sim |
| `q:messageNack` | 2 | sim |
| `q:persist` | 1 | sim |
| `q:pyclass` | 0 | — sem exemplo |
| `q:pydecorator` | 0 | — sem exemplo |
| `q:pyimport` | 2 | sim |
| `q:python` | 15 | sim |
| `q:queue` | 3 | sim |
| `q:schedule` | 2 | sim |
| `q:subscribe` | 3 | sim |
| `q:thread` | 2 | sim |
| `q:transaction` | 4 | sim |
| `q:websocket` | 1 | sim |
| `q:websocket-close` | 1 | sim |
| `q:websocket-send` | 1 | sim |

## Lacunas que esta medição expõe

- **3 tags sem nenhum exemplo** no repositório: `q:dispatchEvent`, `q:pyclass`, `q:pydecorator`. Uma tag sem exemplo que roda não deveria entrar no Core (regra de entrada, PRODUCTION_READINESS.md Fase 6).
- **0 tags cujos exemplos não parseiam**: nenhuma.
