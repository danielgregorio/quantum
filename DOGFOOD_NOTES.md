# O que doeu ao escrever uma tela de verdade

> `FRAMEWORK_PLAN.md` Fase 4. Reescrevi a listagem de projetos do `quantum_admin`
> — hoje FastAPI + fetch + Jinja — como um único arquivo `.q`, lendo o mesmo
> SQLite. Resultado: **`components/admin/projects.q`**, 100 linhas, servido em
> `http://localhost:8080/admin/projects`, mostrando os 3 projetos reais do banco.
>
> Este documento é o produto da fase. O critério de saída dizia: *"se a lista vier
> vazia, ou eu não olhei direito, ou o framework está pronto — e a segunda hipótese
> precisa de mais evidência que uma tela."* A lista não veio vazia.

**Placar:** 11 atritos em ~100 linhas de template. **4 eram bugs**, corrigidos
com teste de regressão (`tests/unit/test_dogfooding_regressions.py`, 6 dos 7
falham contra o código anterior). Dos 7 restantes, **3 foram resolvidos depois**
pela Fase 2.2 e pela correção do htmx (itens 5, 6 e a metade que importava do 8).
**Restam 4 decisões de design em aberto** — itens 7, 9, 10, 11 —, registradas
aqui em vez de corrigidas no impulso.

Nenhum dos 4 bugs era pego pelos 2.506 testes existentes. É esse o argumento
da Fase 4: eles só aparecem quando alguém usa a coisa de ponta a ponta.

---

## Os bugs (corrigidos)

### 1. `quantum start` mentia — banner de sucesso, servidor morto, exit 0

O pior da lista, e o primeiro que um estranho encontraria.

O Werkzeug re-executa o programa inteiro num processo filho quando o reloader
está ligado. O filho reentrava em `start()`, rodava a checagem de porta,
encontrava **o socket do próprio pai** ligado, concluía "porta em uso" e saía.

Como `reload: true` é o **default que vem no `quantum.config.yaml`**, o jeito
documentado de subir o servidor era incapaz de subir o servidor. E como o
`return` era nu, o CLI saía com código **0** — um supervisor, um healthcheck de
container ou um passo de CI veriam "started OK" com nada escutando.

Perdi ~15 minutos achando que era porta ocupada de uma sessão anterior. Um
usuário novo desiste antes.

**Correção:** guarda `WERKZEUG_RUN_MAIN` na checagem de porta; `start()` devolve
código de saída; `runner.py` propaga em vez de engolir.

### 2. Toda página em rota aninhada carregava sem CSS e sem JS

O servidor extrai `<style>`/`<script>` inline para arquivos estáticos com hash
de conteúdo — recurso bom. Mas emitia `href="static/styles-….css"`, **relativo**.
Numa página em `/admin/projects` o browser resolve isso para
`/admin/static/styles-….css`, que dá 404.

Ninguém percebe rápido porque **um 404 de stylesheet não falha nada**: a página
renderiza, sem estilo. Só notei porque conferi o link na mão.

**Correção:** `href="/static/…"` e `src="/static/…"`.

### 3. `<q:loop query="projects" var="p">` descartava o `var=` em silêncio

O parser lia `var` só no ramo não-query. Com `query=` presente, a variável de
linha virava o nome da query, e o `var="p"` que eu escrevi era jogado fora — sem
erro, sem warning, nem no parser nem no renderer.

A página saiu com **todos os campos como placeholder literal**: `{p.name}`,
`{p.status}`. O loop iterou 3 vezes, certinho, com os dados certos carregados —
só que nada resolvia. Levei um tempo desnecessário procurando o erro no
databinding, que estava perfeito.

O idioma estabelecido é `<q:loop query="users">` + `{users.name}`, e continua
funcionando idêntico. O problema nunca foi o default: era aceitar um atributo e
descartá-lo calado.

**Correção:** `var=` é respeitado quando presente; ausente, nada muda.

### 4. `<!DOCTYPE html>` dentro de `<q:component>` é erro de parse

Um `.q` é XML, e um DOCTYPE só é válido **antes** do elemento raiz — mas o
elemento raiz é `<q:component>`. Escrever uma página HTML completa da forma
óbvia não compila.

Nenhum dos 168 exemplos do repo emite DOCTYPE, o que explica por que nunca
apareceu. O servidor injeta um na saída, então na prática funciona — mas só
descobri isso depois de remover o meu e ir olhar o HTML servido.

**Estado:** documentado no template, não "corrigido" — o certo é o `q:component`
saber emitir DOCTYPE, e isso é decisão de design (item 8 abaixo).

---

## As decisões pendentes (não corrigidas de propósito)

### 5. ✅ `q:query` publica duas variáveis, e a errada falhava calada

`<q:query name="projects">` cria **duas** coisas: `projects` (a lista de linhas)
e `projects_result` (os metadados, com `recordCount`). Escrevi
`{projects.recordCount}` — o que qualquer pessoa escreveria — e não recebi erro
nenhum.

Pior: eu tinha isso dentro de um `<q:set name="total" value="{projects.recordCount}" />`.
O `q:set` guardou a **string literal** `"{projects.recordCount}"`, e o `{total}`
mais adiante renderizou essa string na página. **O erro se propagou por duas
tags antes de aparecer**, e apareceu como texto na tela, não como erro.

O sufixo `_result` é a convenção; `{projects.length}` também funciona. O
problema não é a API, é o silêncio. Isto é a Fase 2.2 (mensagens de erro como
UX) com um caso de teste concreto: `{projects.recordCount}` deveria dizer
*"`projects` é uma lista de 3 linhas; você quis `{projects.length}` ou
`{projects_result.recordCount}`?"*.

> **Resolvido** (commit `e581d4f`). A mensagem hoje é literalmente:
> `{projects.recordCount} did not resolve: list of 3 items has no 'recordCount';`
> `use .length for the count, or the query's <name>_result for its metadata`.
> E o `{p.name}` do item 3 vira
> `variable 'p' is not defined (in scope: projects, projects_result, total)` —
> que teria me dado a causa do bug 3 na primeira linha do log.

### 6. ✅ Duas representações diferentes para a mesma falha

A mesma expressão quebrada sai de dois jeitos, dependendo de onde está:

| Contexto | Saída |
|---|---|
| Expressão pura (`<span>{p.name}</span>`) | `{p.name}` — o placeholder literal |
| Conteúdo misto (`#{p.id} · branch {p.git_branch}`) | `{ERROR: p.id}` |

As duas vazam para o HTML de produção. A segunda vaza o nome interno da
variável para o usuário final. Escolher uma das duas é trivial; escolher *qual*
é a decisão — e ela depende do item 5.

> **Resolvido** (commit `e581d4f`): as duas viraram o placeholder. O
> `{ERROR: …}` saiu — o diagnóstico agora vai para o log, onde é útil, em vez de
> para a página, onde vazava nome interno para o usuário final.

### 7. Não existe distinção entre componente reutilizável e página roteável

Os dois vivem em `./components`. Consequência medida: `GET /Layout` responde
**500, não 404** — o `components/Layout.q`, que é um partial de layout, é uma
URL pública. Ele não renderiza sozinho, então falha; mas está roteado.

Num framework web isso é uma decisão que precisa ser explícita: ou `pages/` vs
`components/`, ou uma convenção de prefixo (`_Layout.q`), ou um atributo no
próprio componente. Hoje é acidente.

### 8. ⚠️ Não há como o `.q` controlar o documento HTML (htmx resolvido)

Ligado ao item 4. Hoje o servidor decide o DOCTYPE, injeta `htmx` de
`https://unpkg.com`, e injeta as tags de CSS/JS extraídos. O `.q` não tem voz
nisso.

O htmx merece nota própria: **toda página servida carrega um script de um CDN
externo**, sem eu ter pedido. Isso é uma dependência de rede em runtime, um
problema para deploy offline/homelab — que é exatamente o público declarado na
Fase 0.3 — e algo que uma CSP restritiva bloqueia.

> **A parte do htmx foi resolvida** (commits `6ac73ac` + correção posterior).
> Medido: **5 de 268** arquivos `.q` carregam um marcador htmx, ou seja **98% das
> páginas** puxavam um CDN externo para uma biblioteca que nunca tocavam.
> (O commit `6ac73ac` dizia "6 de 214" — número errado, corrigido depois por
> verificação independente: o glob não pegava subdiretórios.) Agora só é injetado quando a página
> realmente usa (`hx-*` ou `htmx.`), nos dois caminhos de injeção — o de
> documento completo e o de fragmento, sendo que só o primeiro tinha sido
> examinado. O script de config também estava chamando `htmx.config` direto, de
> modo que um CDN bloqueado virava `htmx is not defined` em toda página; agora
> tem guarda. E `_htmx_url()` prefere `static/vendor/htmx.min.js` se existir.
>
> **Continua aberto:** vendorizar o arquivo de fato, e dar ao `.q` controle
> sobre o próprio documento (DOCTYPE, `<head>`, o que é injetado).

### 9. `quantum run pagina.q` não renderiza nada

Rodar o componente pelo CLI executa as queries e imprime
`[WARN] Component executed without return`. O HTML é descartado —
`_execute_component` nunca chama o renderer.

Não dá para pré-visualizar uma página sem subir o servidor. Para o ciclo de
desenvolvimento, um `quantum render pagina.q` que cuspisse o HTML no stdout
resolveria, e é barato.

### 10. Os assets gerados se acumulam no repositório

Cada `<style>` extraído vira `static/styles-<hash>.css`. O hash é do conteúdo,
então **cada edição de CSS de qualquer página cria um arquivo novo**, e o antigo
nunca é recolhido. Já havia **5 deles commitados** no repo antes da minha tela.

Adicionei o padrão ao `.gitignore`, mas os 5 continuam rastreados (o `.gitignore`
não destrastreia) e não há coleta de lixo. Precisa ou de um diretório de build
descartável, ou de limpeza no boot do servidor.

### 11. A porta não está onde a documentação sugere

Tentei `localhost:5000` (o default de Flask) antes de descobrir 8080 lendo o
banner. Trivial, mas some com uma linha no README.

---

## O que funcionou sem atrito

Vale registrar, porque a lista acima não é o quadro completo:

- **`q:query` com o datasource local.** Declarei o banco em
  `quantum.config.yaml` e a query funcionou de primeira, sem nenhum processo
  externo. Isso era um bloqueador P1 e não é mais.
- **`q:loop query=`** iterou as 3 linhas certas, na ordem do `ORDER BY`, de
  primeira.
- **`q:if condition="{total} == 0"`** acertou o estado vazio (não renderizou
  nada com 3 projetos) sem eu testar nada.
- **Databinding aninhado** (`{p.git_branch}`, `{p.updated_at}`) resolveu direto
  depois do bug 3, incluindo dentro de atributo (`class="badge {p.status}"`).
- **Extração de CSS com hash de conteúdo** é um recurso melhor do que eu
  esperava encontrar — o bug 2 era no link, não na ideia.
- **A tela inteira são 100 linhas de um arquivo**, contra rota FastAPI +
  handler + template Jinja + fetch em JS. A proposta da linguagem se sustenta
  neste caso.

---

## O que isso diz sobre a ordem das próximas fases

A Fase 4 existia para trocar opinião por evidência sobre as Fases 2 e 3. A
evidência aponta para um lugar diferente do que eu teria chutado:

1. **Fase 2.2 (mensagens de erro) subiu para primeira.** Dos 11 atritos, **6 são
   a mesma doença**: falha silenciosa. Nenhum dos 4 bugs me deu uma mensagem
   útil; três não deram mensagem nenhuma. O tempo que perdi não foi consertando,
   foi *descobrindo o que estava errado*. Numa linguagem declarativa a mensagem
   de erro é a interface de debugging, e hoje ela é o buraco maior — maior que
   qualquer feature faltando.

2. **A camada HTTP/servidor precisa de uma passada própria.** Não estava no
   plano como fase. Dois dos quatro bugs (1 e 2) estão nela, e são do tipo que
   define a primeira impressão de quem clona o repo.

3. **A distinção página/componente (item 7) é decisão de arquitetura**, não
   melhoria incremental, e trava as duas acima. Vale decidir antes.

4. **O avaliador de expressões (Fase 2.1) se comportou.** Zero atritos vindos
   dele nesta tela, incluindo o `{total}` numérico, comparação em `q:if` e
   acesso pontilhado em atributo. É a confirmação por uso que a fase pedia.
