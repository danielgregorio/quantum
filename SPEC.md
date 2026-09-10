# Quantum — Especificação da linguagem

> **Normativo.** Este documento diz o que um programa Quantum significa. Cada
> regra tem um ID (`RET-1`, `LOOP-2`…) e pelo menos um teste que a cita pelo ID;
> `tests/conformance/test_spec_ids.py` falha se uma regra ficar sem teste ou se
> um teste citar um ID que não existe aqui.
>
> Cobre o **Core** e a **IA** (ver `SUPPORT_TIERS.md`). Tags experimentais e de
> Laboratório não são especificadas.
>
> O que ainda não foi decidido está em [Em aberto](#em-aberto), cada item com um
> teste `xfail(strict=True)` em `tests/conformance/test_known_gaps.py`.
>
> Versão da especificação: acompanha `quantum-framework` 0.11.

---

## 0. Parse

**PARSE-1** — Uma tag do namespace `q:` que a linguagem não conhece é erro de
parse, em qualquer lugar do arquivo, e a mensagem sugere a tag de nome parecido
quando há (`<q:sett>` → `<q:set>`). Elementos HTML e tags de outros namespaces
não são afetados.

## 1. Retorno

**RET-1** — O primeiro `q:return` executado, em ordem de documento, encerra o
componente com o seu valor. Um `q:return` de topo não é adiado para depois dos
demais comandos.

**RET-2** — Um `value` que é exatamente uma expressão (`"{x}"`) produz o valor da
expressão, com o tipo dele. Qualquer outro `value` — texto literal, ou texto
misturado com expressões — produz **texto**: `"{i}.{j}"` é `"1.2"`, e `"007"` é
`"007"`.

**RET-3** — Um `q:return` dentro de `q:if` encerra o corpo que contém o `q:if`
quando o ramo executa. Quando nenhum ramo executa um `q:return`, a execução
segue.

## 2. Repetição

**LOOP-1** — Um `q:return` dentro de `q:loop` não encerra o loop: cada `q:return`
executado acrescenta um item a uma lista.

**LOOP-2** — Um `q:loop` que executou ao menos um `q:return` encerra o corpo que o
contém com a lista (como RET-3). Um loop que não executou nenhum deixa a
execução seguir.

**LOOP-3** — Os `q:return` de um loop aninhado entram soltos, em ordem, na lista
do loop externo. Um valor que por acaso é uma lista entra como um item.

## 2a. Condicionais

**IF-1** — `q:elseif` e `q:else` podem ser escritos dentro do `q:if` ou logo
depois de `</q:if>`, com o mesmo significado, em qualquer corpo: componente,
`q:loop`, `q:function`, `q:action`, elementos HTML. Um `q:elseif`/`q:else` sem
um `q:if` imediatamente antes é erro de parse. Dentro de um `q:if`, um `q:else`
filho direto pertence a esse `q:if`.

## 2b. Funções

**FN-1** — Numa chamada de `q:function`, os argumentos se ligam aos `q:param` por
posição ou por nome; o `default` vale para o que faltar. Cada argumento é
convertido para o `type` do `q:param` e checado contra suas regras (`required`,
`email`, `url`, `min`, `max`, `minlength`, `maxlength`, `pattern`, `enum`) — as
mesmas de `q:action` (ACT-2) — em toda chamada. Um argumento que não passa é
erro que cita o parâmetro.

**FN-2** — `q:function` aceita `name`, `returnType`, `description` e `hint`. Os
atributos que eram aceitos e nunca fizeram nada (`cache`, `memoize`, `pure`,
`async`, `retry`, `timeout`, `access`, `scope`, `validate`, `endpoint` e os de
REST) são erro de parse que diz isso.

**FN-3** — Uma `q:function` do componente pode ser chamada em qualquer expressão
dele: atributos `q:` e conteúdo HTML.

## 3. Ações e formulários

**ACT-1** — Numa página com várias `q:action`, a action executada é a nomeada pelo
campo `action` do corpo da requisição.

**ACT-2** — Cada campo declarado com `q:param` vira uma variável da action, já
validado e convertido para o tipo declarado. Se uma regra de validação falhar (`required`, `type`,
`minlength`, `maxlength`, `min`, `max`, `pattern`), a action não executa: a
resposta redireciona para a página de origem com `flash` contendo o motivo e
`flashType="error"`.

**ACT-3** — `q:redirect` encerra a action. Seu `flash` aceita expressões e fica
disponível como `flash` (e o tipo como `flashType`) na próxima página
renderizada, uma única vez.

**ACT-4** — `q:query` dentro de `q:action` usa os mesmos datasources declarados em
`quantum.config.yaml` que a página.

**ACT-5** — Numa página com mais de uma `q:action`, uma requisição cujo campo
`action` falta ou não nomeia nenhuma action da página responde `400`, citando o
nome pedido e as actions disponíveis. Nenhuma action é executada no lugar. Com
uma única action na página, o campo é opcional.

**ACT-6** — Dentro de `q:action`, como na renderização da página, `form.<campo>`
contém o valor enviado, como texto e sem validação. `q:param` continua sendo o
caminho validado e tipado (ACT-2).

## 3a. Páginas e rotas

**ROUTE-1** — `quantum start` serve cada arquivo de `components/` numa URL com o
caminho dele: `components/sobre.q` em `/sobre`, `components/index.q` em `/`, e
`components/loja/index.q` em `/loja`. Um segmento `[nome]` no caminho casa com
qualquer valor e o entrega como o parâmetro `nome` (`components/loja/[id].q`
em `/loja/41`). Sem arquivo correspondente, ou fora de `components/`, a
resposta é `404`.

## 4. Autenticação

**AUTH-1** — Um componente com `require_auth="true"` só é servido a uma sessão
com `session.authenticated` verdadeiro e `session.sessionExpiry` no futuro.
Sem sessão, a resposta redireciona para `/login`; com a sessão expirada, para
`/login?expired=true`. A ausência de `sessionExpiry` conta como expirada.

**AUTH-2** — Com `require_role`, a sessão autenticada precisa ter
`session.userRole` igual a um dos papéis listados (separados por vírgula); do
contrário a resposta é `403`.

**AUTH-3** — `hashPassword(senha)` devolve um hash bcrypt com sal próprio.
`verifyPassword(senha, hash)` devolve verdadeiro só quando a senha corresponde ao
hash; para senha vazia, hash ausente ou malformado devolve falso, nunca erro.

## 5. Importação de dados

**DATA-1** — `q:data type="csv"` produz uma lista de registros; as colunas
declaradas com `q:column` são convertidas para o tipo declarado, e as não
declaradas vêm como texto.

**DATA-2** — Em `type="xml"`, o `xpath` de `q:data` seleciona os registros e cada
`q:field` extrai um valor relativo ao registro, aceitando `@atributo`,
`filho/text()`, `filho/@atributo` e `filho`; o `type` do campo é aplicado.

**DATA-3** — As operações de `q:transform` executam em ordem: `q:filter` (mesma
sintaxe de condição que `q:if`, com os campos do registro como variáveis),
`q:sort`, `q:limit` e `q:compute` (acrescenta um campo calculado).

**DATA-4** — Uma importação que falha (fonte inexistente, conteúdo inválido) é erro
que cita o nome, a fonte e o motivo. Com `onerror="continue"` a execução segue e o
motivo fica em `<nome>_result.error.message`, como em INV-2.

## 5a. Banco de dados

**DB-1** — `q:query` executa o SQL no datasource declarado em
`quantum.config.yaml`. Cada `:nome` no SQL é ligado a um `q:param` — nunca
interpolado — e um `:nome` sem `q:param` é erro de parse. `<nome>` é a lista de
registros; `<nome>_result` tem `success`, `recordCount`, `columnList`,
`executionTime` e, em escritas, `affectedRows` e `lastInsertId` (`result=` dá
outro nome a esse objeto). Quando o resultado tem uma única linha, seus campos
também ficam em `<nome>.<campo>`.

**DB-2** — Com `paginate="true"`, `page` e `page_size`, a consulta devolve só a
página pedida, e `<nome>_result.pagination` tem `totalRecords`, `totalPages`,
`currentPage`, `pageSize`, `hasNextPage`, `hasPreviousPage`, `startRecord` e
`endRecord`.

**DB-3** — `q:query source="outra"` executa o SQL em memória sobre o resultado
de uma consulta anterior, que aparece como tabela com o nome dela.

**DB-4** — Dentro de `q:transaction datasource="…"`, as consultas usam esse
datasource quando não declaram um. Se qualquer comando falhar, tudo é desfeito e
a transação é erro que diz isso.

**DB-5** — `q:query` não aceita `cache`, `ttl`, `reactive`, `interval`,
`timeout`, `maxrows` e `batch`, que eram aceitos e nunca fizeram nada: são erro
de parse.

**DB-6** — `quantum migrate` aplica os arquivos `migrations/V<nnn>_<nome>.sql` ao
datasource declarado em `quantum.config.yaml` — o mesmo que as páginas usam:
o indicado com `--datasource`, ou o único declarado. Com mais de um e sem
`--datasource`, ou sem nenhum, é erro que diz como resolver. Não há conexão de
reserva.

## 6. Expressões

Uma expressão é o que está entre chaves: `{total * 2}`. Ela aparece em dois
lugares com regras diferentes, de propósito: **atributos de tags `q:`**
(`value`, `condition`, `url`…), que são sempre código, e **conteúdo HTML**, que
também carrega exemplos de código e chaves soltas.

**EXPR-1** — Num atributo `q:`, um nome que não existe é erro. A mensagem cita a
expressão e o nome, e sugere um nome parecido quando há. `"x{nada}y"` não produz
`"x{nada}y"`.

**EXPR-2** — Num atributo `q:`, uma expressão que falha ao avaliar (divisão por
zero, índice fora da lista, chave ausente) é erro que cita a expressão.

**EXPR-3** — Uma referência a escopo (`session.`, `application.`, `request.`,
`form.`, `query.`, `cookie.`) cujo valor não existe produz `''` quando a
expressão é só a referência (`{session.nome}`): uma página renderiza antes do
login. Numa operação (`{session.visitas + 1}`) é erro, que diz que o valor não
existe e indica `q:if` ou `operation="increment"`.

**EXPR-4** — No conteúdo HTML, uma expressão que não resolve fica como texto
literal e é registrada no log uma vez por expressão distinta. Em qualquer lugar,
um objeto JSON (`{"a": 1}`) e um quantificador de regex (`\d{10,11}`) não são
expressões e passam intactos.

**EXPR-5** — Uma `condition` é um teste de presença: um nome, chave, atributo ou
índice que não existe a torna falsa, registrado no log uma vez.
`<q:if condition="flash">` antes de existir `flash` não executa o ramo. Qualquer
outra falha (sintaxe inválida, função que não existe) é erro, como em EXPR-2.
Nunca uma falha torna uma condição verdadeira.

**EXPR-6** — Além da sintaxe de Python (`and`, `or`, `not`), as expressões aceitam
`&&`, `||` e `!` com o mesmo significado. `!=` continua sendo diferença, e nada
dentro de uma string é traduzido.

**EXPR-7** — `-`, `*`, `/`, `//`, `%` e `**` operam sobre números (texto que
parece número conta como número); com qualquer outro operando são erro. `+` soma
números, ou junta dois textos ou duas listas. Um atributo `q:` que é só `{3}` é o
número 3; dentro de outro texto, `\d{3}` continua um quantificador de regex
(EXPR-4).

## 6a. Tipos em `q:set`

**ERR-1** — O `type` de `q:set` converte o valor assim: `number` mantém o número
(`{5 / 2}` é `2.5`); `integer` aceita só número inteiro (`{7 / 2}` é erro, que
indica `round()`); `decimal` é número com casas; `boolean` aceita `true`/`false`,
`1`/`0`, `yes`/`no` e vazio (falso); `array`, `object` e `json` leem JSON. Um
valor que não converte é erro que mostra o valor. Quando o valor é texto com
expressões (`"{a} + {b}"`), a mensagem mostra a forma que calcula
(`"{a + b}"`); quando é JSON com aspas simples, diz para usar aspas duplas.

**SET-1** — Em `q:set`, `default` é o valor guardado quando `value` resolve para
nada: ausente, `null` ou texto vazio. `value="{session.cliques}" default="0"` guarda
`0` na primeira visita.

## 7. Invocação

**INV-1** — `q:invoke url=` faz a requisição com o método declarado (padrão
`GET`) e timeout de 30 segundos quando `timeout` não é declarado. Cada `q:param`
vira um parâmetro da query string com o seu `value`. Uma resposta JSON vira o
valor de `<nome>`.

**INV-2** — Uma invocação que falha (resposta fora de 2xx, falha de conexão, função
que levanta erro) é erro que cita o nome e o motivo, como `q:query`. Com
`onerror="continue"` a execução segue: `<nome>_result.success` é falso e
`<nome>_result.error.message` diz o motivo. `onerror` só aceita `fail` (padrão) e
`continue`.

## 7a. Serviços declarados

**SVC-1** — `@service("nome")` (de `quantum.services`) registra uma função Python
sob esse nome. Registrar outra função com um nome já usado é erro.

**SVC-2** — Um módulo de serviços só é importado quando listado em `services:` no
`quantum.config.yaml`. Um módulo listado que não importa é erro que o nomeia.

**SVC-3** — `<q:invoke name="x" service="nome">` chama a função registrada com os
`q:param` como argumentos nomeados, convertidos pelo `type` de cada um; o valor
devolvido vira `x`. Uma exceção da função é falha de invocação (INV-2). Um nome
não registrado é erro que lista os registrados. `endpoint=` não é aceito.

## 8. IA

**IA-1** — Todas as tags de IA usam o mesmo servidor de modelos:
`QUANTUM_LLM_BASE_URL`, senão `llm.base_url` de `quantum.config.yaml`, senão
`http://localhost:11434`.

**IA-2** — Uma base `q:knowledge` persistida é reutilizada só quando o texto das
fontes, o modelo de embedding e o fatiamento são os mesmos da indexação; do
contrário é reindexada. Qualquer `name` é aceito.

**IA-3** — Se o modelo não produzir a resposta de um `q:query mode="rag"`, a
consulta falha com erro; a falha nunca é devolvida como resposta.

**IA-4** — `q:agent` executa as tools declaradas com os argumentos convertidos
para os tipos dos `q:param` da tool, e expõe em `<nome>_result` o `success`, as
`actions` (tool, argumentos, resultado) e, na falha, `error.message`.

## 8a. Configuração

**CFG-1** — Em `quantum.config.yaml`, `${NOME}` em qualquer valor é substituído
pela variável de ambiente `NOME`, e `${NOME:-padrão}` usa o padrão quando ela não
existe; `$$` é um `$` literal. Uma variável ausente sem padrão é erro ao carregar a
configuração, citando a variável e a chave — o programa não roda com a
configuração pela metade. Vale para `quantum run`, `quantum start` e todos os
serviços.

## 9. Execução (`quantum run`)

**RUN-1** — Executar um componente não cria arquivos nem inicia serviços que o
programa não usa, e a saída não traz o log interno do framework. Cada serviço
(banco, jobs, IA, filas…) existe numa única instância por execução,
compartilhada por todas as tags.

**RUN-2** — Uma falha tratada — que a linguagem entrega ao programa, como
`<nome>_result` de `q:invoke` — aparece como mensagem, nunca como traceback do
Python.

## 9a. `q:application`

**APP-1** — Uma aplicação web são páginas em `components/` servidas por
`quantum start`. `q:application` com `type="html"`, `type="api"`,
`type="microservices"` ou sem `type` é erro de parse, que diz para usar
`components/` e `quantum start`. Os tipos `game`, `terminal`, `ui` e `testing`
existem, fora do Core (Laboratório e Experimental), e não são especificados.

---

## Em aberto

Lacunas medidas e ainda não decididas. Cada uma é um teste
`xfail(strict=True)` em `tests/conformance/test_known_gaps.py`, com o
comportamento proposto; quando decidida, vira regra acima e o teste muda de
arquivo.

Nenhuma lacuna aberta: G1–G18 foram decididas e viraram as regras acima.
