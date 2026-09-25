---
source: tutorial/tasks-app.md
source_hash: 0b96f8323cd6
---

# Construa a aplicação de tarefas

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/tutorial/tasks-app).
:::

Este tutorial constrói uma aplicação completa a partir de uma pasta vazia:
uma lista de tarefas com formulários validados, botões para concluir e
apagar, um filtro, uma tabela ordenável que você edita no lugar, uma página
de edição com o histórico de cada mudança, e uma suíte de testes. É a gêmea
em inglês de
[`projects/tarefas`](https://github.com/danielgregorio/quantum/tree/main/projects/tarefas),
uma das aplicações que o próprio CI do Quantum roda, e termina com o mesmo
código. O código desta página está em inglês, como no original.

Você não escreve JavaScript nem Python. Cada passo é uma aplicação completa
que funciona, e o código desta página é executado pela suíte de testes do
Quantum exatamente como aparece (`tests/docs/test_tutorial_tasks_app.py`): o
que você lê é o que roda.

## 1. Instale e comece o projeto

Você precisa do Python 3.12 ou mais novo.

```bash
pip install quantum-framework
mkdir tasks && cd tasks
```

Uma aplicação é uma pasta com um `quantum.config.yaml`. Este diz onde ficam
as páginas e as migrações do banco, e declara um banco SQLite chamado `db`.

Salve como `quantum.config.yaml`:

```yaml
server:
  port: 8080
  host: 127.0.0.1

paths:
  components: ./components
  migrations: ./migrations

datasources:
  db:
    driver: sqlite
    database: ./data/tasks.db
```

A tabela vem de uma migração: arquivos SQL simples em `migrations/`,
aplicados em ordem. A restrição `CHECK` importa mais adiante: o Quantum a lê e
recusa uma prioridade fora da lista, no formulário de edição e no editor da
tabela, sem você escrever essa regra de novo.

Salve como `migrations/V001_tasks.sql`:

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT INTO tasks (title, priority) VALUES
    ('Read the Quantum guide', 'high'),
    ('Write the first page', 'medium');
INSERT INTO tasks (title, priority, done) VALUES
    ('Install Quantum', 'low', 1);
```

Crie o banco (ele fica em `data/tasks.db`):

```bash
quantum migrate up
```

### A primeira página

Um arquivo em `components/` é uma página: `components/index.q` responde em
`/`. Duas consultas leem o banco, e as tags `ui:*` organizam o resultado: um
painel lateral com as contagens, e a lista, uma linha por tarefa.

Salve como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
          </ui:hbox>
        </q:loop>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

```bash
quantum start
```

Abra http://127.0.0.1:8080: três tarefas e suas contagens. Numa tela
estreita, o painel fica em cima da lista ([UI](/guide/ui), em inglês).

## 2. Crie tarefas, com validação

Um formulário envia seus campos para uma `q:action`. Os `q:param` da ação são
as regras dela: `title` é obrigatório e tem entre 3 e 200 caracteres,
`priority` é um de três valores. Um valor que quebra uma regra nunca chega ao
SQL: a página volta com a mensagem no campo e o que foi digitado
([Actions and forms](/guide/actions), em inglês).

Depois do insert, o `q:redirect` manda o navegador de volta para a lista com
uma mensagem flash, mostrada uma vez pelo bloco `q:if condition="flash"`. O
formulário desenha seus campos a partir da ação para a qual envia:
`ui:input bind="title"` vira um campo de texto obrigatório com
`minlength="3"`, tirado da regra.

Salve como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
          </ui:hbox>
        </q:loop>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

Tente um título vazio, depois uma letra só: o formulário diz o que está
errado, ao lado do campo.

## 3. Concluir e apagar

Mais duas ações, cada uma chamada por um botão na linha.
`with="id={tasks.id}"` envia o id da linha, e `type="integer"` no `q:param`
recusa qualquer coisa que não seja um número antes de o `UPDATE` ou o
`DELETE` rodar.

Salve como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:button on-click="toggle" with="id={tasks.id}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

## 4. Filtre a lista

A página lê `?show=` do endereço com `q:set` e o passa para a consulta como
parâmetro, nunca colado no SQL. O painel lateral ganha três links, a ação
`toggle` mantém o filtro atual quando redireciona, e uma lista vazia diz isso.

Salve como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="show" default="all" enum="all,open,done" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?show={show}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:set name="show" value="{query.show}" default="all" />

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    WHERE :show = 'all' OR (:show = 'open' AND done = 0) OR (:show = 'done' AND done = 1)
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Show">
          <ui:vbox gap="sm">
            <ui:link to="/?show=all">All</ui:link>
            <ui:link to="/?show=open">Open</ui:link>
            <ui:link to="/?show=done">Done</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:button on-click="toggle" with="id={tasks.id}, show={show}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tasks_result.recordCount == 0">
          <ui:text>No tasks here.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

`http://127.0.0.1:8080/?show=done` agora lista só a tarefa concluída.

## 5. Uma tabela que se ordena e se edita

Uma segunda página, `components/sheet.q`, responde em `/sheet`. A consulta é
`sortable` e paginada, e `ui:table` com `edit="tasks"` transforma cada célula
num pequeno formulário que salva uma coluna de uma linha. Você não escreve
nenhuma ação: o esquema da tabela é a regra, então uma prioridade fora da
lista do `CHECK` é recusada, e a célula diz por quê ([UI](/guide/ui), em
inglês).

Salve como `components/sheet.q`:

```xml
<q:component name="Sheet">
  <q:query name="tasks" datasource="db" sortable="true" paginate="true" page_size="20">
    SELECT id, title, priority, done FROM tasks ORDER BY id
  </q:query>

  <ui:window title="Task sheet">
    <ui:vbox gap="md" padding="lg">
      <ui:hbox gap="md">
        <ui:link to="/">Back</ui:link>
        <ui:text>Click a header to sort; edit a cell and confirm with ✓ (or Enter).</ui:text>
      </ui:hbox>
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
      </q:if>
      <ui:table source="{tasks}" sort="true" edit="tasks" datasource="db">
        <ui:column key="title" label="Title" />
        <ui:column key="priority" label="Priority" />
        <ui:column key="done" label="Done" />
      </ui:table>
      <ui:pager for="tasks" />
    </ui:vbox>
  </ui:window>
</q:component>
```

Crie um link para ela no painel lateral:

Salve como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="show" default="all" enum="all,open,done" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?show={show}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:set name="show" value="{query.show}" default="all" />

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    WHERE :show = 'all' OR (:show = 'open' AND done = 0) OR (:show = 'done' AND done = 1)
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Show">
          <ui:vbox gap="sm">
            <ui:link to="/?show=all">All</ui:link>
            <ui:link to="/?show=open">Open</ui:link>
            <ui:link to="/?show=done">Done</ui:link>
            <ui:link to="/sheet">Sheet</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:button on-click="toggle" with="id={tasks.id}, show={show}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tasks_result.recordCount == 0">
          <ui:text>No tasks here.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

## 6. Uma página de edição com histórico

Ligue o histórico de mudanças do banco: cada escrita que uma ação faz é
registrada, com quem a fez e o que mudou.

Salve como `quantum.config.yaml`:

```yaml
server:
  port: 8080
  host: 127.0.0.1

paths:
  components: ./components
  migrations: ./migrations

datasources:
  db:
    driver: sqlite
    database: ./data/tasks.db
    history: true          # every change made by an action is recorded
```

A página de edição é `components/task/[id].q`: o `[id]` no nome do arquivo
responde em `/task/1`, `/task/2`… e dá à página uma variável `id`.

A ação dela nomeia uma tabela e colunas em vez de declarar `q:param`, então as
regras vêm do esquema (`title` é `NOT NULL`, `priority` está na lista do
`CHECK`). O `ui:form`, sem campos próprios, desenha um campo por coluna
preenchido com os valores da tarefa, e o `ui:history` lista cada mudança
feita nesta tarefa.

Salve como `components/task/[id].q`:

```xml
<q:component name="EditTask">
  <q:action name="save" method="POST" table="tasks" datasource="db" columns="title,priority">
    <q:query name="saved" datasource="db">
      UPDATE tasks SET title = :title, priority = :priority WHERE id = :id
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Saved: {title}" />
  </q:action>

  <q:query name="task" datasource="db">
    SELECT id, title, priority FROM tasks WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>

  <ui:window title="Edit task">
    <ui:vbox gap="md" padding="lg">
      <ui:link to="/">Back</ui:link>
      <q:if condition="task_result.recordCount == 0">
        <ui:alert variant="danger">That task does not exist.</ui:alert>
      </q:if>
      <q:else>
        <ui:form on-submit="save" values="{task}" submit="Save" />
        <ui:section title="History">
          <ui:history table="tasks" key="{id}" datasource="db" />
        </ui:section>
      </q:else>
    </ui:vbox>
  </ui:window>
</q:component>
```

E um link *Edit* em cada linha:

Salve como `components/index.q`:

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="show" default="all" enum="all,open,done" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?show={show}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:set name="show" value="{query.show}" default="all" />

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    WHERE :show = 'all' OR (:show = 'open' AND done = 0) OR (:show = 'done' AND done = 1)
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Show">
          <ui:vbox gap="sm">
            <ui:link to="/?show=all">All</ui:link>
            <ui:link to="/?show=open">Open</ui:link>
            <ui:link to="/?show=done">Done</ui:link>
            <ui:link to="/sheet">Sheet</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:link to="/task/{tasks.id}">Edit</ui:link>
            <ui:button on-click="toggle" with="id={tasks.id}, show={show}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tasks_result.recordCount == 0">
          <ui:text>No tasks here.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

Essa é a aplicação inteira: 151 linhas de `.q`, 13 de SQL, 0 de JavaScript.

## 7. Teste

Uma aplicação Quantum é testada na própria linguagem
([Testing an App](/guide/testing), em inglês). Cada `q:test` começa de um
banco novo construído pelas suas migrações, visita páginas, envia ações e
confere o redirecionamento, a mensagem flash, o erro num campo, as linhas da
tabela e o histórico.

Salve como `tests/tasks.test.q`:

```xml
<q:test name="the list shows the summary and the tasks" page="/">
  <test:visit />
  <test:expect text="Total: 3" />
  <test:expect text="Open: 2" />
  <test:expect text="Done: 1" />
  <test:expect text="Write the first page" />
</q:test>

<q:test name="create a task" page="/">
  <test:submit action="create" title="Test the UI" priority="high" />
  <test:expect status="302" redirect="/" flash="Created: Test the UI" />
  <test:expect table="tasks" count="1" where="title = 'Test the UI' AND priority = 'high'" />
  <test:expect text="Total: 4" />
</q:test>

<q:test name="a title that is too short is refused on its field" page="/">
  <test:submit action="create" title="x" />
  <test:expect redirect="/" />
  <test:expect error="title" />
  <test:expect text="at least 3 characters" />
  <test:expect table="tasks" count="3" />
</q:test>

<q:test name="a priority outside the list is refused" page="/">
  <test:submit action="create" title="With a wrong priority" priority="urgent" />
  <test:expect error="priority" />
  <test:expect table="tasks" count="0" where="title = 'With a wrong priority'" />
</q:test>

<q:test name="finish a task and show the open ones" page="/">
  <test:given table="tasks" title="Buy bread" />
  <test:expect table="tasks" count="1" where="title = 'Buy bread' AND done = 0" />
  <test:submit action="toggle" id="4" show="open" />
  <test:expect redirect="/?show=open" />
  <test:expect table="tasks" count="1" where="id = 4 AND done = 1" />
  <test:expect no-text="Buy bread" />
  <test:expect text="Read the Quantum guide" />
</q:test>

<q:test name="delete a task" page="/">
  <test:submit action="delete" id="2" />
  <test:expect redirect="/" flash="Task deleted." />
  <test:expect table="tasks" count="0" where="id = 2" />
  <test:expect text="Total: 2" />
</q:test>

<q:test name="the page runs a fixed number of queries" page="/">
  <test:given table="tasks" />
  <test:given table="tasks" />
  <test:visit />
  <test:expect queries="2" />
  <test:expect var="show" value="all" />
</q:test>

<q:test name="the filter comes from the query string" page="/">
  <test:visit show="done" />
  <test:expect var="show" value="done" />
  <test:expect text="Install Quantum" />
  <test:expect no-text="Read the Quantum guide" />
</q:test>
```

Os testes também podem ficar ao lado da página que testam:

Salve como `components/sheet.test.q`:

```xml
<q:test name="a cell edit is saved and recorded in the history" page="/sheet">
  <test:submit action="__edit" __table="tasks" __key="1" __column="priority" value="low" />
  <test:expect redirect="/sheet" flash="Saved: priority" />
  <test:expect table="tasks" count="1" where="id = 1 AND priority = 'low'" />
  <test:expect history="tasks" count="1" op="update" where="id = 1" />
</q:test>

<q:test name="a cell refuses a value the schema does not allow" page="/sheet">
  <test:submit action="__edit" __table="tasks" __key="1" __column="priority" value="urgent" />
  <test:expect table="tasks" count="1" where="id = 1 AND priority = 'high'" />
  <test:expect history="tasks" count="0" />
</q:test>

<q:test name="the edit form validates with the schema's rules" page="/task/1">
  <test:submit action="save" title="" priority="urgent" />
  <test:expect error="title" message="Required" />
  <test:expect error="priority" message="Must be one of: low, medium, high" />
  <test:expect table="tasks" count="1" where="id = 1 AND title = 'Read the Quantum guide'" />
</q:test>

<q:test name="an edit is saved and shows in the task's history" page="/task/1">
  <test:as user="ana" />
  <test:submit action="save" title="Read the whole guide" priority="low" />
  <test:expect redirect="/" flash="Saved: Read the whole guide" />
  <test:expect table="tasks" count="1" where="id = 1 AND title = 'Read the whole guide' AND priority = 'low'" />
  <test:expect history="tasks" action="save" op="update" user="ana" where="id = 1" count="1" />
  <test:visit path="/task/1" />
  <test:expect text="title: Read the Quantum guide → Read the whole guide" />
</q:test>

<q:test name="a task that does not exist" page="/task/99">
  <test:visit />
  <test:expect text="That task does not exist" />
</q:test>
```

Rode:

```bash
quantum test
```

<!-- report: pass -->
```text
components/sheet.test.q
  PASS  a cell edit is saved and recorded in the history  (304 ms)
  PASS  a cell refuses a value the schema does not allow  (32 ms)
  PASS  the edit form validates with the schema's rules  (35 ms)
  PASS  an edit is saved and shows in the task's history  (55 ms)
  PASS  a task that does not exist  (33 ms)
tests/tasks.test.q
  PASS  the list shows the summary and the tasks  (29 ms)
  PASS  create a task  (47 ms)
  PASS  a title that is too short is refused on its field  (34 ms)
  PASS  a priority outside the list is refused  (33 ms)
  PASS  finish a task and show the open ones  (39 ms)
  PASS  delete a task  (34 ms)
  PASS  the page runs a fixed number of queries  (33 ms)
  PASS  the filter comes from the query string  (26 ms)
13 passed, 0 failed
```

O `quantum test` sai com `1` quando um teste falha, então roda no CI do jeito
que está.

## 8. A mesma aplicação, em outros lugares

As páginas `ui:*` não são só HTML:

```bash
quantum console    # the same pages in the terminal
quantum desktop    # in a desktop window (pip install "quantum-framework[desktop]")
```

## Para onde ir depois

Páginas em inglês:

- [Actions and forms](/guide/actions): cada regra que um `q:param` aceita
- [Queries](/guide/query): parâmetros, paginação e histórico
- [UI](/guide/ui): as tags `ui:*`
- [Testing an App](/guide/testing): cada passo `test:`
