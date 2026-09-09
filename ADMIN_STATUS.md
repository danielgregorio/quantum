# Quantum Admin — estado atual e o que falta

> Medido em 2026-09-07 executando o admin, não lendo o código. Todos os
> números aqui vieram de rodar as rotas contra o app real.
>
> Antecedentes: `SATELLITES_AUDIT.md` (auditoria e Fases A–F) e
> `PRODUCTION_READINESS.md` (o plano geral).

---

## O que foi medido

| Medição | Resultado |
|---|---|
| Rotas totais | 270 |
| Rotas de API (`/api/*`) | 51 |
| Rotas GET exercidas com token válido | 162 |
| Rotas que respondem **sem** token | **0** |
| Rotas que devolvem 500 | **0** |
| Rotas que devolvem 503 | 6 (Docker ausente — resposta correta) |
| Alvos htmx estáticos referenciados pela UI | 47 |
| Alvos htmx que **não resolvem** | **0** |
| Testes de admin na suíte | 58 |

As três primeiras linhas eram, antes desta sessão: API aberta (as rotas de
dados respondiam 200 sem token), duas rotas em 500, e a tela de login
incapaz de logar.

---

## Estado por área

Legenda: **núcleo** = o recorte escolhido na Fase A (projetos, datasources,
jobs). O resto continua no código, sem promessa.

| Área | Ler | Criar | Editar | Excluir | Veredito |
|---|:--:|:--:|:--:|:--:|---|
| **Projetos** (núcleo) | ✅ | ✅ | ✅ | ✅ | completo |
| **Datasources** (núcleo) | ✅ | ✅ | ❌ | ✅ | **falta editar** |
| **Jobs** (núcleo) | ✅ | ✅ (dispatch) | — | ❌ | falta excluir |
| Settings | ✅ | ✅ | ✅ | ✅ | completo |
| Schedules | ✅ | ✅ | ❌ | ✅ | falta editar |
| Queues | ✅ | ✅ (purge) | — | ❌ | parcial |
| Usuários | ✅ | ✅ | ❌ | ✅ | em memória (some no restart) |
| Docker | ✅ | ✅ | — | ✅ | depende do daemon |
| Recursos | ✅ | ✅ | — | ✅ | parcial |
| Deploy | ✅ | ✅ | — | — | **build real; push/deploy não** |
| CI/CD, Incidentes, Templates | ✅ | — | — | — | só leitura |

---

## O que falta para "implementação final"

Em ordem: o que impede uso, depois o que incomoda, depois o que é escopo novo.

### 1. Bloqueia o uso do núcleo

- **Editar datasource não existe.** Há criar, excluir, start/stop/restart,
  testar, logs e setup — mas nenhum `PUT`. Errou o host ou a senha: exclua e
  recrie. É o buraco mais visível do núcleo.
- **Usuários vivem em memória.** Criar um usuário funciona e ele some no
  próximo restart; só `admin` é reconstruído, de `ADMIN_PASSWORD`. A tela diz
  isso hoje, o que é honesto, mas não é gerência de usuários. Precisa de
  tabela e migração.
- **Editar usuário não existe** (trocar papel, renomear). O botão foi
  removido porque não havia nada atrás dele.

### 2. Funciona, mas pela metade

- **Deploy**: só o passo de *build* é real (compila os `.q` com o parser de
  verdade). Push, deploy local, docker e ssh **falham dizendo que não estão
  implementados** — antes diziam que tinham funcionado. Para completar é
  preciso build de imagem, que o admin não tem em lugar nenhum.
- **Schedules sem edição**: pausar, retomar, rodar agora e excluir existem;
  alterar a expressão cron, não.
- **Jobs sem exclusão**: dá para cancelar e reprocessar, não para remover o
  registro.
- **Queues**: purge existe; criar/excluir fila pela UI, não.

### 3. Escopo novo (decidir se entra)

- **Registro de auditoria** existe como serviço e aparece por projeto; não há
  tela global de "quem fez o quê".
- **CI/CD e Incidentes** são leitura sobre dados que nada escreve.
- **Templates**: listagem e wizard de criação; sem edição.
- **Métricas**: não há. `/health` responde, e é tudo.

---

## Dívida estrutural (não é feature, mas cobra juros)

1. **`main.py` tem ~13.500 linhas** e mistura rotas, HTML e JavaScript em
   f-strings. Foi o que permitiu que `{URL_PREFIX}` literal chegasse a nove
   telas e que a tela de login parasse de funcionar sem ninguém notar.
2. **Duas linguagens de UI convivem**: htmx com HTML gerado por concatenação
   em `main.py`, e as telas em `.q` (`components/admin/`). A Fase E existe
   para colapsar isso; falta a tela de jobs.
3. **Sem Alembic.** `models.py` cria tabelas na primeira execução; não há
   migração. Adicionar coluna hoje significa apagar o banco.
4. **`python-multipart` não é declarado** e o FastAPI precisa dele para
   `Form(...)`. A rota de settings foi escrita lendo o corpo à mão por causa
   disso.

---

## Como verificar isto de novo

```bash
pytest tests/admin/ -q                       # 58 testes
pytest tests/integration/test_admin_screens_in_q.py -q   # as telas .q
```

A varredura que produziu a tabela acima está em
`tests/admin/test_admin_smoke.py`: ela exercita todas as rotas GET, falha se
alguma responder 500, falha se alguma rota de API responder sem token, e
falha se alguma página emitir `{URL_PREFIX}` literal.
