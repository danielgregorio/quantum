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

## 3. Ações e formulários

**ACT-1** — Numa página com várias `q:action`, a action executada é a nomeada pelo
campo `action` do corpo da requisição.

**ACT-2** — Só os campos declarados com `q:param` chegam à action, já convertidos
para o tipo declarado. Se uma regra de validação falhar (`required`, `type`,
`minlength`, `maxlength`, `min`, `max`, `pattern`), a action não executa: a
resposta redireciona para a página de origem com `flash` contendo o motivo e
`flashType="error"`.

**ACT-3** — `q:redirect` encerra a action. Seu `flash` aceita expressões e fica
disponível como `flash` (e o tipo como `flashType`) na próxima página
renderizada, uma única vez.

**ACT-4** — `q:query` dentro de `q:action` usa os mesmos datasources declarados em
`quantum.config.yaml` que a página.

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

## 6. IA

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
| G6 | Nome de action inexistente cai na primeira action |
| G7 | `{form.campo}` dentro de `q:action` |
| G12 | Variável inexistente fica literal na saída |
| G13 | Mensagem de array com aspas simples |
| G14 | Erro de avaliação devolve as chaves cruas |
| G15 | Conta com variável de escopo ausente |
| G16 | `q:data` que falha é silencioso |
| G17 | `q:application type="html"` não inicia |
| G18 | `q:application type="api"` não executa as rotas |
