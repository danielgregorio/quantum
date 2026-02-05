# Devlog: Task Master Dashboard

**Data:** 2026-01-30
**Projeto:** quantum-dashboard (Task Master)
**Status:** Funcional no forge (10.10.1.40), pendente roteamento via sargas.cloud

---

## Objetivo

Criar um app Dashboard/Admin com CRUD completo usando `q:query` e SQLite, demonstrando as capacidades de banco de dados do Quantum Framework.

## O que foi feito

### Parte A: Suporte a Datasources Locais no Framework

O `database_service.py` dependia da API do Quantum Admin (`http://localhost:8000`) para obter configs de datasources. Como o Admin nao roda no forge, foi adicionado fallback para ler datasources do `quantum.config.yaml` local.

**Arquivos modificados:**
- `src/runtime/database_service.py` - Adicionado param `local_datasources` no `__init__`, usado como fallback em `get_datasource_config()`
- `src/runtime/component.py` - Passa config de datasources para `DatabaseService()`
- `src/runtime/web_server.py` - Passa `self.config` para `ComponentRuntime()`

### Parte B: App Task Master

**Estrutura:**
```
projects/quantum-dashboard/
├── quantum.config.yaml          # Config com datasource SQLite local
├── gunicorn.conf.py             # Init DB + patches do runtime
├── components/
│   └── index.q                  # Dashboard principal (CRUD + stats)
└── static/
    └── dashboard.css            # Estilos do dashboard
```

**Funcionalidades implementadas:**
1. Dashboard com stats (total, pending, done) via `q:query` + SQLite
2. Criar task via formulario POST
3. Marcar task como done (botao inline)
4. Reabrir task (botao inline)
5. Deletar task com confirmacao
6. Badges coloridos por status e prioridade
7. Dados seed automaticos no primeiro boot

### Parte C: Debugging de Stats Vazias

O problema principal do dia: os numeros de stats (Total, Pending, Completed) apareciam vazios no dashboard deployed.

#### Investigacao

1. **Primeira hipotese:** Problema na resolucao de variaveis dotted (`statsTotal.cnt`) no renderer
   - Investigado `_evaluate_expression`, `_evaluate_nested_property`, `_apply_databinding`
   - Adicionado patch `patched_evaluate_expression` para checar `local_vars` diretamente
   - Resultado: nao resolveu

2. **Segunda hipotese:** Remover o `q:loop` wrapper e usar `{statsTotal.cnt}` diretamente
   - Resultado: erro `'int' object has no attribute 'replace'`
   - Descoberta: `_apply_databinding` retorna int raw para full-match expressions, e `html.escape()` nao aceita int

3. **Root cause encontrado via debug logs:**
   - Adicionado debug prints no `_render_loop` do gunicorn.conf.py
   - Deploy + leitura de logs via API do forge (`/api/apps/dashboard/logs`)
   - Resultado: `body_count=0` para loops de stats!
   - O loop tinha items (1 por query) mas ZERO filhos no body

4. **Root cause real:** Parser XML bug
   - `_parse_loop_statement` usa `for child in loop_element:` que so itera child ELEMENTS XML
   - O texto `{statsTotal.cnt}` e `.text` property do elemento `<q:loop>`, nao um child element
   - O parser nunca capturava text content dentro de loops

#### Solucao

**Fix no parser (src/core/parser.py):**
- Adicionado captura de `.text` e `.tail` content como TextNodes em `_parse_loop_statement`
- Porem: este fix NAO chega ao forge (o tarball usa `quantum-src/` do deploy service)

**Workaround para o forge:**
- Envolver texto em `<span>` tags: `<q:loop query="statsTotal"><span>{statsTotal.cnt}</span></q:loop>`
- Isso faz o parser capturar como child element HTML

**Fix adicional (gunicorn.conf.py):**
- `patched_render_text_node` - Trata valores nao-string do `_apply_databinding`:
  ```python
  def patched_render_text_node(self, node):
      text = node.content
      if node.has_databinding:
          text = self._apply_databinding(text)
      if callable(text):
          text = ''
      return html_module.escape(str(text) if text is not None else '')
  ```

### Resultado Final

Dashboard 100% funcional em `http://10.10.1.40/dashboard/`:
- Stats renderizando: 7 total, 5 pending, 2 completed
- CRUD completo funcionando
- CSS e layout corretos
- Botoes condicionais (Done/Reopen) via `q:if`

## Problema Pendente: Roteamento via quantum.sargas.cloud

O dashboard funciona via IP direto (`http://10.10.1.40/dashboard/`) mas NAO via dominio (`https://quantum.sargas.cloud/dashboard/`).

**Diagnostico:**
- O custom `http.conf` gerado pelo deploy service cria server block com `server_name 10.10.1.40`
- O NPM (nginx-proxy-manager) tem proxy host para `quantum.sargas.cloud` que intercepta requests com esse Host header
- Requests via dominio nao chegam ao custom server block
- Apenas `/blog/` e `/quantum-blog/` funcionam via dominio (provavelmente configurados manualmente no NPM)
- Todos os outros apps (`/dashboard/`, `/mario/`, `/chat/`, `/snake/`, etc.) mostram pagina default do Quantum via dominio

**Solucao necessaria:**
- Configurar o proxy host do NPM para `quantum.sargas.cloud` para fazer proxy para `http://localhost:80` com `proxy_set_header Host 10.10.1.40`
- OU adicionar custom locations no proxy host do NPM para cada app
- OU alterar `QUANTUM_SERVER_NAME` para incluir `quantum.sargas.cloud`

## Patches ativos no gunicorn.conf.py

O `gunicorn.conf.py` do dashboard contem monkey-patches para corrigir comportamentos do runtime antigo no forge:

1. `patched_render` - Dispatch correto de LoopNode/IfNode no renderer
2. `patched_get_loop_items` - Resolve query results para `loop_type='query'`
3. `patched_render_loop` - Seta dotted variables para rows de query
4. `patched_render_html_node` - Trata atributos nao-string com `str()`
5. `patched_renderer_evaluate_condition` - Avalia condicoes com databinding
6. `patched_evaluate_expression` - Checa `local_vars` para keys dotted
7. `patched_render_text_node` - Trata valores nao-string do databinding

## Licoes Aprendidas

1. **XML Parser `.text` vs children:** `for child in element:` so itera child elements, nao `.text` content
2. **Databinding retorna tipos raw:** `_apply_databinding` retorna int/list para full-match, nao string
3. **Debug no forge:** Usar prints no gunicorn.conf.py + API de logs (`/api/apps/{name}/logs`) e eficaz
4. **Monkey-patching:** O gunicorn.conf.py e o ponto de extensao mais poderoso para apps no forge
5. **NPM routing:** O custom `http.conf` com `server_name` especifico so funciona para requests com Host header correspondente
