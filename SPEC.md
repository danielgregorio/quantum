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
> Versão da especificação: acompanha `quantum-framework` 0.11 (em construção).

---

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

## 7. Invocação

**INV-1** — `q:invoke url=` faz a requisição com o método declarado (padrão
`GET`) e timeout de 30 segundos quando `timeout` não é declarado. Cada `q:param`
vira um parâmetro da query string com o seu `value`. Uma resposta JSON vira o
valor de `<nome>`.

**INV-2** — Uma resposta fora de 2xx, ou falha de conexão, não é erro da página:
`<nome>_result.success` é falso e `<nome>_result.error.message` diz o motivo.

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

---

## Em aberto

Lacunas medidas e ainda não decididas. Cada uma é um teste
`xfail(strict=True)` em `tests/conformance/test_known_gaps.py`, com o
comportamento proposto; quando decidida, vira regra acima e o teste muda de
arquivo.

| Lacuna | Tema |
|---|---|
| G3 | Mensagem de conversão para número (`"{a} + {b}"`) |
| G4 | `${VAR}` em `quantum.config.yaml` |
| G5 | Traceback exibido em falha de `q:invoke` |
| G13 | Mensagem de array com aspas simples |
| G16 | `q:data` que falha é silencioso |
| G17 | `q:application type="html"` não inicia |
| G18 | `q:application type="api"` não executa as rotas |
