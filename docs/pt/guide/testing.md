---
source: guide/testing.md
source_hash: d3d9fb557d8b
---
# Testar uma aplicação (`quantum test`)

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/testing). O código é o mesmo do original.
:::

Uma aplicação Quantum é testada na própria linguagem. Um arquivo `*.test.q`
guarda testes que visitam páginas, enviam ações e conferem o que aconteceu —
o redirecionamento, a mensagem flash, as linhas no banco, o erro ao lado de
um campo — com as palavras que a aplicação já usa. O `quantum test` os roda
contra o servidor de verdade, cada teste com um banco novo, e sai com `1`
quando um falha.

Sem Python, sem navegador, sem seletores CSS.

## Um primeiro teste {#a-first-test}

Uma pequena aplicação de notas. Salve como `quantum.config.yaml`:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/notes.db
    history: true
```

Salve como `migrations/V001_notes.sql`:

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'idea' CHECK (kind IN ('idea', 'todo')),
    created_at TEXT DEFAULT (datetime('now'))
);
INSERT INTO notes (title) VALUES ('Read the guide');
```

Salve como `components/index.q`:

```xml
<q:component name="Notes">
  <q:action name="add" method="POST">
    <q:param name="title" required="true" minlength="3" />
    <q:param name="kind" default="idea" enum="idea,todo" />
    <q:query name="added" datasource="db">
      INSERT INTO notes (title, kind) VALUES (:title, :kind)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="kind" value="{kind}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Added: {title}" />
  </q:action>

  <q:query name="notes" datasource="db">SELECT title, kind FROM notes ORDER BY id</q:query>

  <ui:window title="Notes">
    <ui:vbox gap="md" padding="lg">
      <q:if condition="flash"><ui:alert variant="success">{flash}</ui:alert></q:if>
      <ui:form on-submit="add">
        <ui:input bind="title" />
        <ui:button variant="primary">Add</ui:button>
      </ui:form>
      <ui:text>{notes_result.recordCount} notes</ui:text>
      <q:loop query="notes"><ui:text>{notes.title} ({notes.kind})</ui:text></q:loop>
    </ui:vbox>
  </ui:window>
</q:component>
```

E os testes dela. Salve como `tests/notes.test.q`:

```xml
<q:test name="the list" page="/">
  <test:visit />
  <test:expect text="1 notes" />
  <test:expect text="Read the guide (idea)" />
</q:test>

<q:test name="add a note" page="/">
  <test:submit action="add" title="Buy bread" kind="todo" />
  <test:expect redirect="/" flash="Added: Buy bread" />
  <test:expect table="notes" count="1" where="title = 'Buy bread' AND kind = 'todo'" />
  <test:expect text="2 notes" />
  <test:expect history="notes" action="add" op="insert" count="1" />
</q:test>

<q:test name="a title needs three letters" page="/">
  <test:submit action="add" title="x" />
  <test:expect error="title" message="Must be at least 3 characters" />
  <test:expect table="notes" count="1" />
</q:test>
```

Rode a partir da pasta da aplicação:

```bash
quantum test
```

<!-- report: pass -->
```text
tests/notes.test.q
  PASS  the list  (31 ms)
  PASS  add a note  (38 ms)
  PASS  a title needs three letters  (27 ms)
3 passed, 0 failed
```

Cada teste começa do mesmo lugar: um banco novo construído por
`migrations/`, com só `Read the guide`. O que `add a note` gravou já sumiu
quando `a title needs three letters` começa.

## Quando um teste falha {#when-a-test-fails}

Mude a mensagem flash em `add a note` para `flash="Added: Buy milk"` e rode
de novo. O relatório nomeia o passo que falhou, com a sua linha, e o que a
aplicação fez no lugar:

<!-- report: fail -->
```text
tests/notes.test.q
  PASS  the list  (29 ms)
  FAIL  add a note  (35 ms)
        tests/notes.test.q:9  <test:expect redirect="/" flash="Added: Buy milk"/>
        expected flash "Added: Buy milk", got "Added: Buy bread"
  PASS  a title needs three letters  (26 ms)
2 passed, 1 failed
```

O `quantum test` sai com `1`, então um job de CI falha junto.

Quando a própria página falha — uma expressão que não avalia, um SQL que o
banco recusa — o passo que fez a requisição falha com o erro e também com a
linha **da página**:

```text
        tests/bill.test.q:2  <test:visit/>
        the server answered 500: ComponentExecutionError: …
        page: components/bill.q:4
```

Um passo cuja requisição responde um status de erro (`400` ou mais) falha, a
menos que o passo seguinte diga que o espera — `<test:expect status="404"/>`
depois de visitar uma página que não deveria existir.

## Onde os testes ficam {#where-tests-live}

O `quantum test` procura `*.test.q` na pasta que recebe (a atual, por
padrão):

- **ao lado de uma página** — `components/admin/index.test.q` testa
  `components/admin/index.q`. Um `.test.q` nunca é servido como página e não
  cria rota; o `quantum check` o lê como um arquivo de teste.
- **em `tests/`** — suítes sobre a aplicação inteira, como
  `tests/signin.test.q`.

Um arquivo de teste pertence à aplicação do `quantum.config.yaml` mais
próximo acima dele. `quantum test projects/blog tests/one.test.q` roda vários
lugares de uma vez.

## Os passos {#the-steps}

Um `q:test` tem um `name` e a `page` em que começa (`/` por padrão). Os
passos dele rodam em ordem.

| Passo | O que faz |
|---|---|
| `<test:given table="notes" title="Draft"/>` | Insere uma linha, verificada contra o esquema |
| `<test:as user="Ana" role="admin" id="1"/>` | Entra sem senha |
| `<test:visit/>` | Abre a página — ou `path="/other"` — com os outros atributos como query string |
| `<test:submit action="add" title="…"/>` | Envia a ação com os outros atributos como campos |
| `<test:expect …/>` | Confere o que aconteceu |

### `test:given` — as linhas de que o teste precisa {#test-given-—-rows-the-test-needs}

```xml
<test:given table="notes" title="Draft" kind="todo" />
```

A linha entra no banco do teste passando pelas regras do esquema: uma tabela
ou coluna que não existe, um valor fora de uma lista `CHECK (… IN …)`, texto
numa coluna `INTEGER`, uma chave estrangeira apontando para o nada — cada um
faz o passo falhar com uma mensagem, em vez de inserir algo que a aplicação
nunca poderia ter gravado. As colunas obrigatórias que o passo deixa de fora
são preenchidas: o primeiro valor permitido de um `CHECK … IN`, a primeira
linha da tabela para a qual uma chave estrangeira aponta, um número, ou
`"<column> <n>"` para texto. Com várias fontes de dados, `datasource="…"` diz
qual.

### `test:as` — quem está usando a aplicação {#test-as-—-who-is-using-the-app}

```xml
<test:as user="Ana" role="admin" id="1" plan="pro" />
```

Define a sessão como um login faz: `session.userName` é `Ana`,
`session.userRole` é `admin`, `session.userId` é `1`, e as páginas com
`require_auth` e `require_role` deixam o teste entrar. Qualquer outro
atributo é uma variável de sessão (`session.plan` acima). Para testar o
próprio formulário de login, envie-o como uma pessoa faria.

### `test:visit` e `test:submit` — o que um navegador faz {#test-visit-and-test-submit-—-what-a-browser-does}

O `test:submit` envia para a página em que o teste está, do jeito que o
formulário dessa página enviaria: passando pelas guardas da página, pelas
regras dos `q:param` da ação, pelo histórico, pelo redirecionamento e pela
mensagem flash. Os dois passos seguem redirecionamentos como um navegador, e
o teste fica então na página em que terminou — então o próximo
`test:submit` envia para lá. Depois de um redirecionamento para a página de
login, por exemplo, o teste está em `/login`.

Uma página com uma única `q:action` a roda seja qual for o nome enviado; se a
página rodou outra ação que não a que o passo nomeia, o passo falha — senão o
teste passaria testando a ação errada.

## O que o `test:expect` confere {#what-test-expect-checks}

Cada atributo é uma verificação; várias num mesmo `test:expect` precisam
valer todas.

| Verificação | Vale quando |
|---|---|
| `status="302"` | A requisição respondeu esse status (antes de seguir qualquer redirecionamento) |
| `redirect="/?added=1"` | Redirecionou para cá: caminho, query e `#fragment` |
| `flash="Added: Buy bread"` | Definiu exatamente essa mensagem flash |
| `text="2 notes"` | A página em que o teste está mostra esse texto (sem as tags, espaços juntados) |
| `no-text="Draft"` | … não o mostra |
| `error="title"` | O envio foi recusado com um erro nesse campo; `message="…"` confere a mensagem |
| `var="filter" value="open"` | A página (ou a ação) terminou com esse valor na variável, comparado como texto |
| `queries="2"`, `queries="at most 3"` | A requisição rodou esse número de consultas ao banco |
| `table="notes"` | O banco tem linhas nessa tabela — `where="…"` filtra, `count="N"` confere quantas |
| `history="notes"` | O `history: true` registrou mudanças nessa tabela — com `action`, `op` (`insert`, `update`, `delete`), `user`, `where`, `count` |

`queries` pega a página que roda uma consulta por linha: uma lista de 3
linhas e uma de 300 deveriam ambas dizer `queries="2"`.

## Nada fora do vocabulário {#nothing-outside-the-vocabulary}

Os passos e as verificações acima são a linguagem inteira. Uma tag que não é
uma delas, uma verificação que não existe, um `count` sem `table` ou
`history` para contar — cada um é um erro de parse com a sua linha, nunca um
passo que em silêncio não faz nada:

```text
tests/notes.test.q: <test:click> is not a test step. The steps are: test:given, test:as, test:visit, test:submit, test:expect
  at line 4: <test:click text="Add" />
```

## No CI {#in-ci}

O `quantum test` sai com `0` quando todos os testes passaram e `1` caso
contrário — inclusive quando um arquivo não passa pelo parser, um caminho não
existe ou nenhum teste é encontrado. Rode-o na pasta da aplicação como um
passo do CI:

```bash
quantum test
```

## Limites por enquanto {#limits-for-now}

- Só fontes de dados `sqlite`: cada teste constrói o seu próprio banco SQLite.
- Com várias fontes de dados e uma pasta `migrations/`, as migrações teriam
  de dizer qual fonte de dados constroem; o teste falha dizendo isso.
- Clicar pela tela (`test:click`, `test:fill`), rodar um teste na web e no
  console, testes derivados das regras das ações, respostas de IA gravadas e
  cobertura estão planejados, não construídos.

Veja também: [Ações e formulários](./actions.md), [Consultas ao banco](./query.md),
[Autenticação](./authentication.md).
