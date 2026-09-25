---
source: guide/ui.md
source_hash: 238a9346dd15
---
# Uma aplicação, várias telas

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/ui). O código é o mesmo do original.
:::

Uma página escrita com os elementos do UI Engine — `ui:window`, `ui:panel`,
`ui:table`, `ui:form`… — é uma página web, uma aplicação de terminal e uma
janela de desktop ao mesmo tempo. Há um só runtime: as consultas, ações e
regras da página rodam uma vez, no servidor, e cada renderizador só
**desenha** o resultado.

| Abra com | Você recebe |
|---|---|
| `quantum start` | a página num navegador |
| `quantum console` | a mesma página no terminal (Textual) |
| `quantum desktop` | a mesma página numa janela nativa (pywebview) |

Nada da lógica da página é traduzido para outra linguagem, então uma regra
que você escreve uma vez — uma validação, um login, uma consulta — se
comporta igual em todas as telas.

## Uma primeira tela {#a-first-screen}

Salve como `components/index.q` num projeto (uma pasta com um
`quantum.config.yaml`) e rode `quantum start`:

```xml
<q:component name="Counter">
  <q:action name="add" method="POST">
    <q:set name="current" value="{session.clicks}" default="0" type="number" />
    <q:set name="session.clicks" value="{current + 1}" />
    <q:redirect url="/" />
  </q:action>

  <q:set name="clicks" value="{session.clicks}" default="0" />

  <ui:window title="Counter">
    <ui:panel title="Clicks">
      <ui:text>You clicked {clicks} times.</ui:text>
      <ui:button on-click="add" variant="primary">Add</ui:button>
    </ui:panel>
  </ui:window>
</q:component>
```

**Mostra:** `Clicks` · `You clicked 0 times.` · `Add`

Agora rode `quantum console` na mesma pasta: o mesmo painel, texto e botão,
no terminal. Apertar **Add** ali envia a mesma `q:action`, com uma sessão
própria, exatamente como um navegador faz.

O `quantum desktop` a abre numa janela. Ele precisa de um pacote a mais:

```bash
pip install "quantum-framework[desktop]"
quantum desktop            # the home page
quantum desktop /reports   # another page, --width/--height to size the window
```

O título da janela é o `title` do primeiro `ui:window` — o mesmo título que a
aba do navegador e o console mostram.

## Eventos são ações {#events-are-actions}

Um botão ou um formulário não chama código no navegador: ele envia para uma
`q:action` da página. A ação valida, faz o seu trabalho e redireciona, como
qualquer formulário no Quantum (veja [Ações e formulários](/pt/guide/actions)).

- `<ui:button on-click="save">` envia para `<q:action name="save">`.
- `with="id={t.id}, filter={filter}"` acrescenta campos a esse envio — é assim
  que um botão numa linha diz qual linha ele é.
- `<ui:form on-submit="create">` envia os seus campos:
  `<ui:input bind="title">` é o campo `title`.

Um evento que não nomeia nenhuma ação da página é um erro que lista as ações
da página — nunca um botão que em silêncio não faz nada.

## Tabelas e listas a partir de dados {#tables-and-lists-from-data}

`source=` recebe uma lista — uma `q:query` ou um array — e desenha uma linha
por item. A variável da linha é nomeada por `as=` (por padrão `row` para uma
tabela, `item` para uma lista), exatamente como num `q:loop`:

```xml
<q:component name="People">
  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:redirect url="/" flash="Deleted person {id}" />
  </q:action>

  <q:set name="people" type="array"
         value='[{"id": 1, "name": "Ana", "age": 30}, {"id": 2, "name": "Bia", "age": 25}]' />

  <ui:window title="People">
    <ui:table source="{people}" as="p">
      <ui:column key="name" label="Name" />
      <ui:column key="age" label="Age" align="right" />
      <ui:column label="">
        <ui:button on-click="delete" with="id={p.id}" variant="danger">Delete {p.name}</ui:button>
      </ui:column>
    </ui:table>

    <ui:list source="{people}" as="p">
      <ui:item><ui:text>{p.name} is {p.age} years old</ui:text></ui:item>
    </ui:list>
  </ui:window>
</q:component>
```

**Mostra:** `Name` · `Age` · `Ana` · `30` · `Delete Bia` · `Bia is 25 years old`

- `<ui:column key="name">` mostra esse campo da linha, escapado.
- Uma coluna com conteúdo o desenha uma vez por linha — botões, links, badges.
- Um `source` que não é uma lista, ou uma `key` que a linha não tem, é um erro
  que diz isso (com os campos da linha) — nunca uma tabela vazia.

Com um banco de dados, a fonte é uma consulta. Os exemplos daqui em diante
usam este banco (o CI o constrói a partir deste bloco):

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    done INTEGER NOT NULL DEFAULT 0
);
INSERT INTO tasks (title, priority) VALUES ('Write the guide', 'high'), ('Review it', 'low');

CREATE TABLE posts (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL);
WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 12)
INSERT INTO posts (title) SELECT 'Post ' || i FROM n;
```

```xml
<q:component name="Tasks">
  <q:query name="tasks" datasource="db">
    SELECT id, title FROM tasks ORDER BY id
  </q:query>
  <ui:window title="Tasks">
    <ui:table source="{tasks}">
      <ui:column key="title" label="Task" />
    </ui:table>
  </ui:window>
</q:component>
```

**Mostra:** `Task` · `Write the guide` · `Review it`

## Páginas de uma lista longa {#pages-of-a-long-list}

Uma consulta com `paginate="true"` devolve uma página; a página é o `?page=`
da URL. `<ui:pager>` desenha os links:

```xml
<q:component name="Blog">
  <q:query name="posts" datasource="db" paginate="true" page_size="10">
    SELECT title FROM posts ORDER BY id DESC
  </q:query>
  <ui:window title="Blog">
    <ui:list source="{posts}" as="p"><ui:item><ui:text>{p.title}</ui:text></ui:item></ui:list>
    <ui:pager for="posts" />
  </ui:window>
</q:component>
```

**Mostra:** `Post 12` · `Post 3`

Os 12 posts dão duas páginas: a primeira mostra de `Post 12` até `Post 3`.

- Anterior, os números em volta da página atual (a primeira e a última
  sempre, `…` onde pula), próxima. Nas pontas, anterior/próxima não são links;
  com uma página só, nada é desenhado.
- Os links mantêm os outros parâmetros da URL: em `/?tag=news&page=2` eles vão
  para `/?tag=news&page=3`.
- `?page=abc` ou `?page=-1` é a página 1, nunca um erro.
- `window="1"` mostra menos números; `param="p"` (com `page="{query.p}"` na
  consulta) quando uma página tem duas listas paginadas.

O `projects/blog` pagina a sua página inicial assim.

## Busca enquanto você digita {#search-as-you-type}

```xml
<q:component name="Search">
  <q:set name="term" value="{query.q}" default="" />
  <q:query name="found" datasource="db">
    SELECT title FROM posts WHERE title LIKE :p
    <q:param name="p" value="%{term}%" type="string" />
  </q:query>
  <ui:window title="Search">
    <ui:input bind="q" search="results" placeholder="Search" />
    <ui:vbox id="results">
      <ui:list source="{found}" as="a"><ui:item><ui:text>{a.title}</ui:text></ui:item></ui:list>
    </ui:vbox>
  </ui:window>
</q:component>
```

**Mostra:** `Post 1` · `Post 12`

- Cada pausa na digitação (`delay`, 300 ms por padrão) pede a mesma página
  com `?q=…` e troca só `#results` — as próprias consultas da página fazem a
  busca. A URL acompanha, então o resultado pode ser compartilhado ou
  recarregado.
- Por baixo é um formulário GET simples: sem JavaScript, o Enter busca.
- Os outros parâmetros da URL são mantidos; `page` é descartado, então uma
  busca nova começa na página 1 de um `<ui:pager>`.
- No console, o mesmo: depois de uma pausa a página é pedida de novo, e o
  campo mantém o foco.
- Um alvo que não está na página é um erro — nunca um campo que não troca
  nada.

O `projects/blog` busca assim (`components/search.q`).

## Uma tabela que se ordena e se edita {#a-table-that-sorts-and-edits-itself}

```xml
<q:component name="Sheet">
  <q:query name="tasks" datasource="db" sortable="true">
    SELECT id, title, priority FROM tasks
  </q:query>
  <ui:window title="Tasks">
    <ui:table source="{tasks}" sort="true" edit="tasks" datasource="db">
      <ui:column key="title" label="Title" />
      <ui:column key="priority" label="Priority" />
    </ui:table>
  </ui:window>
</q:component>
```

**Mostra:** `Title` · `Priority` · `low` · `medium` · `high`

Cada célula é um pequeno formulário: os títulos estão nos seus campos, e cada
prioridade é uma seleção com a lista do `CHECK`.

- `sort="true"`: cada cabeçalho é um link que ordena a consulta **no SQL**
  (`sortable="true"` na consulta) por `?sort=` e `?dir=` — então funciona com
  um `<ui:pager>`. Uma coluna na URL que a consulta não devolve é ignorada.
- `edit="tasks"`: cada coluna mostrada daquela tabela vira um pequeno
  formulário na sua célula (Enter ou ✓ salva). Você não escreve nenhuma ação:
  o servidor só aceita a tabela e as colunas que esta página declara, roda as
  guardas da página, valida o valor com as regras da coluna tiradas do esquema
  (NOT NULL, `CHECK … IN`, o tipo) e atualiza uma linha pela chave primária.
  Um valor recusado volta na sua célula com o erro. `edit="false"` numa coluna
  a deixa só de leitura.
- As linhas precisam incluir a chave primária (`SELECT id, …`).
- O que ela faz aparece no [`/_dev`](/tools/dev-panel) como qualquer ação.

O `projects/tarefas` tem uma em `/planilha`.

## Formulários que abrem com valores {#forms-that-open-with-values}

Os campos pegam o valor inicial da página, então o mesmo formulário cria e
edita:

```xml
<q:component name="Profile">
  <q:action name="save" method="POST">
    <q:param name="name" required="true" minlength="2" />
    <q:param name="notices" default="off" />
    <q:param name="plan" default="free" />
    <q:set name="session.name" value="{name}" />
    <q:redirect url="/" flash="Saved: {name}, notices {notices}, plan {plan}" />
  </q:action>

  <q:set name="name" value="{session.name}" default="Ana" />

  <ui:window title="Profile">
    <q:if condition="flash">
      <ui:alert variant="success">{flash}</ui:alert>
    </q:if>
    <ui:form on-submit="save">
      <ui:formitem label="Name">
        <ui:input bind="name" value="{name}" />
      </ui:formitem>
      <ui:checkbox bind="notices" label="Receive notices" checked="true" />
      <ui:radio bind="plan" options="free,pro" value="pro" />
      <ui:select bind="color" options="blue,green" value="green" />
      <ui:button variant="primary">Save</ui:button>
    </ui:form>
  </ui:window>
</q:component>
```

**Mostra:** `Name` · `Receive notices` · `free` · `pro` · `Save`

`default=` dá o valor da primeira visita (a sessão ainda não tem `name`).

- `value=` em `ui:input`, `ui:select` e `ui:radio`; `checked=` em
  `ui:checkbox` e `ui:switch` (`true`, ou uma expressão).
- Uma caixa marcada é enviada como `on`; uma desmarcada **não é enviada** — do
  jeito que os navegadores fazem. É por isso que a ação diz
  `<q:param name="notices" default="off">`.

## Formulários que conhecem as regras da ação {#forms-that-know-the-action-s-rules}

Um formulário pega as regras de cada campo dos `q:param` da ação para a qual
envia, então você as escreve uma vez:

```xml
<q:component name="SignUp">
  <q:action name="signUp" method="POST">
    <q:param name="name" required="true" minlength="3" />
    <q:param name="age" type="integer" min="18" />
    <q:param name="plan" enum="free,pro" default="free" />
    <q:redirect url="/" flash="Signed up: {name}" />
  </q:action>

  <ui:window title="Sign up">
    <ui:form on-submit="signUp">
      <ui:formitem label="Name"><ui:input bind="name" /></ui:formitem>
      <ui:formitem label="Age"><ui:input bind="age" /></ui:formitem>
      <ui:select bind="plan" />
      <ui:button>Sign up</ui:button>
    </ui:form>
  </ui:window>
</q:component>
```

**Mostra:** `Name` · `Age` · `free` · `pro` · `Sign up`

- `name` ganha `required minlength="3"`, `age` ganha `type="number" min="18"`,
  e a seleção ganha o `enum` como opções — olhe o código-fonte da página. O
  navegador as verifica antes de enviar.
- O servidor continua validando cada campo. Quando ele recusa, a página volta
  com os valores que foram enviados e **cada erro ao lado do seu campo**
  (também no console). Uma senha nunca é devolvida.
- Um atributo que você escreve num campo vence; `<ui:form rules="off">`
  desliga isso.
- Um `pattern` só vira o do navegador quando está ancorado (`^…$`): o
  navegador confere o valor inteiro, o servidor procura dentro dele.

## Formulários a partir de uma tabela {#forms-from-a-table}

Quando uma ação grava numa tabela, ela pode pegar as regras da própria tabela
— o esquema que você já escreveu na migração (a tabela `tasks` acima):

```xml
<q:component name="EditTask">
  <q:action name="save" method="POST" table="tasks" datasource="db" columns="title,priority">
    <q:param name="id" type="integer" required="true" />
    <q:query name="updated" datasource="db">
      UPDATE tasks SET title = :title, priority = :priority WHERE id = :id
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Saved: {title}" />
  </q:action>

  <q:query name="task" datasource="db">SELECT id, title, priority FROM tasks WHERE id = 1</q:query>

  <ui:window title="Edit task">
    <ui:form on-submit="save" values="{task}" submit="Save" />
  </ui:window>
</q:component>
```

**Mostra:** `Title` · `Priority` · `low` · `high` · `Save`

- `title` é `NOT NULL` → obrigatório; `priority` tem `CHECK … IN` → uma
  seleção com essas opções, e o servidor recusa qualquer outra coisa.
- O formulário não tem campos próprios, então desenha um por coluna — rótulos
  tirados dos nomes (`author_id` → "Author"), uma caixa para `BOOLEAN`, uma
  seleção para uma chave estrangeira, preenchida com as linhas da tabela
  referenciada. `values="{task}"` o abre com os valores de uma linha: um
  formulário de edição numa linha só.
- `columns=` escolhe e ordena as colunas (por padrão: todas menos a chave
  primária). Um `q:param` que você escreve na ação vence o da coluna.
- Uma coluna que aceita nulo, deixada em branco, chega à ação como `None`, e
  uma chave estrangeira precisa nomear uma linha que existe.
- O esquema é lido do banco, e lido de novo quando o arquivo do banco muda —
  acrescente uma coluna numa migração e o formulário a terá. O
  `quantum check` informa uma tabela ou coluna que não existe.

O `projects/tarefas` edita uma tarefa assim (`components/tarefa/[id].q`).

## Um layout que se adapta {#layout-that-adapts}

O layout é declarado, com três pontos de quebra: `sm` (640 px), `md` (768 px)
e `lg` (1024 px). No console eles são contados em colunas (80, 96 e 128).

```xml
<q:component name="Dashboard">
  <ui:window title="Dashboard">
    <ui:hbox stack-below="md" gap="md">
      <ui:vbox width="260"><ui:text>Menu</ui:text></ui:vbox>
      <ui:vbox grow="true"><ui:text>Content</ui:text></ui:vbox>
    </ui:hbox>
    <ui:grid columns="1 sm:2 lg:3">
      <ui:text>One</ui:text><ui:text>Two</ui:text><ui:text>Three</ui:text>
    </ui:grid>
    <ui:text hide-below="md">Only on wide screens</ui:text>
  </ui:window>
</q:component>
```

**Mostra:** `Menu` · `Content` · `One` · `Three`

- `stack-below="md"` coloca os filhos de um `ui:hbox` um embaixo do outro
  abaixo de 768 px, e as larguras fixas deles deixam de valer.
- `grow="true"` pega o resto da linha.
- `ui:grid columns="1 sm:2 lg:3"`: uma coluna, duas a partir de `sm`, três a
  partir de `lg`.
- `hide-below` / `hide-above` escondem um elemento de um lado de um ponto de
  quebra.

## O conjunto do Núcleo {#the-core-set}

Estes elementos são desenhados com o mesmo significado pelo navegador, pelo
console e pela janela de desktop, e um mesmo roteiro de teste — ver,
preencher, marcar, escolher, clicar — roda sem mudanças num navegador de
verdade e no console:

| Tipo | Elementos |
|---|---|
| Layout | `window`, `hbox`, `vbox`, `grid`, `panel`, `section`, `scrollbox`, `spacer`, `rule`, `header`, `footer`, `card` (`card-header`, `card-body`, `card-footer`), `tabpanel` / `tab` |
| Conteúdo | `text`, `badge`, `alert`, `link`, `image`, `progress` |
| Dados | `table` / `column`, `list` / `item` |
| Formulários | `form`, `formitem`, `input`, `checkbox`, `switch`, `radio`, `select` / `option`, `button` |
| Recursos de dados | `pager` (páginas de uma consulta), `history` (as mudanças de uma linha), `stream` (uma resposta de IA enquanto é escrita) |

Todos os outros elementos `ui:*` — gráficos, modais, toasts, seletores de
data, menus… — funcionam só no navegador e são **Experimental** (veja a
[referência das tags UI](/reference/ui), em inglês). No console, um elemento
desses mostra `[ui:chart is not drawn in the console]` em vez de outra coisa
no seu lugar.

Um texto direto dentro de um contêiner é conteúdo:
`<ui:card-header>Summary</ui:card-header>`. HTML simples pode ficar entre
elementos `ui:*`; o console mostra o texto dele.

## Builds avulsos {#standalone-builds}

`<q:application type="ui">` com `quantum run app.q --target html` (um único
arquivo HTML) ou `--target textual` (um único arquivo Python) desenha **só o
layout**: não há runtime nesses arquivos, então um `q:set`, `q:function` ou
qualquer outro comando neles é um erro que aponta para cá. Escreva a tela
como uma página para dar lógica a ela.

`--target mobile` (React Native) é **Laboratório**: ele traduz a lógica para
JavaScript por conta própria, sem promessa de estabilidade. Celulares não
fazem parte da 1.0. O antigo `--target desktop` foi removido; o
`quantum desktop` o substitui.
