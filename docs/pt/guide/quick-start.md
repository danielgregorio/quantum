---
source: guide/quick-start.md
source_hash: c82f4c234ab8
---

# Início rápido

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/quick-start).
:::

Construa sua primeira aplicação Quantum em 5 minutos.

Cada passo desta página roda no CI (`tests/docs/test_guide_quick_start.py`).
O código está em inglês, como no original.

## Passo 1: crie um componente

Crie um arquivo chamado `counter.q`:

```xml
<q:component name="Counter" xmlns:q="https://quantum.lang/ns">
  <q:function name="double">
    <q:param name="n" type="number" />
    <q:return value="{n * 2}" />
  </q:function>

  <q:set name="count" type="number" value="0" />
  <q:set name="count" operation="increment" />
  <q:set name="count" operation="increment" />

  <q:return value="Count: {count}, doubled: {double(count)}" />
</q:component>
```

**Saída:** `Count: 2, doubled: 4`

Rode — o `quantum run` mostra o que o componente retorna:

```bash
quantum run counter.q
```

```text
[SUCCESS] Result: Count: 2, doubled: 4
```

## Passo 2: acrescente um loop

Crie `todo-list.q`:

```xml
<q:component name="TodoList" xmlns:q="https://quantum.lang/ns">
  <q:set name="tasks" type="array" value='["Buy groceries", "Walk the dog", "Write code"]' />

  <!-- each q:return adds one item to the result -->
  <q:loop type="array" var="task" items="{tasks}">
    <q:return value="- {task}" />
  </q:loop>
</q:component>
```

**Saída:** `["- Buy groceries", "- Walk the dog", "- Write code"]`

Um `q:return` dentro de um loop não interrompe o loop: cada valor é
guardado, e quando o loop termina o componente retorna a lista (LOOP-1,
LOOP-2). Um loop que não executa nenhum `q:return` deixa a execução seguir
para o que vem depois dele.

## Passo 3: acrescente condicionais

Crie `weather.q`:

```xml
<q:component name="Weather" xmlns:q="https://quantum.lang/ns">
  <q:set name="temperature" value="25" type="number" />

  <q:if condition="temperature > 30">
    <q:return value="It's hot! Stay hydrated." />
  </q:if>
  <q:elseif condition="temperature > 20">
    <q:return value="Nice weather for a walk." />
  </q:elseif>
  <q:elseif condition="temperature > 10">
    <q:return value="Bring a jacket." />
  </q:elseif>
  <q:else>
    <q:return value="Bundle up, it's cold!" />
  </q:else>
</q:component>
```

**Saída:** `Nice weather for a walk.`

## Passo 4: sirva uma página web

As páginas ficam numa pasta `components/`; o nome do arquivo é a URL. Crie
`components/index.q`:

```xml
<q:component name="index" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" value='["Apple", "Banana", "Cherry"]' />
  <q:set name="a" value="10" type="number" />
  <q:set name="b" value="5" type="number" />

  <html>
  <head><title>My Quantum App</title></head>
  <body>
    <h1>Welcome to Quantum</h1>
    <ul>
      <q:loop type="array" var="item" items="{items}">
        <li>{item}</li>
      </q:loop>
    </ul>
    <p>{a} + {b} = {a + b}</p>
  </body>
  </html>
</q:component>
```

Inicie o servidor a partir da pasta que contém `components/`:

```bash
quantum start
```

Abra `http://localhost:8080`: a página mostra os três itens e
`10 + 5 = 15`. `components/about.q` seria servido em `/about`. Pare o
servidor com `quantum stop`.

> Sem `<!DOCTYPE html>` no arquivo: um `.q` é XML, e um DOCTYPE só é válido
> antes do elemento raiz. O servidor o acrescenta à resposta.

## Passo 5: leia de um banco de dados

Crie um banco SQLite com uma tabela (qualquer Python serve — Quantum já
precisa dele):

```bash
python -c "import sqlite3, os; os.makedirs('data', exist_ok=True); c = sqlite3.connect('data/app.db'); c.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)'); c.executemany('INSERT INTO users (name, email) VALUES (?, ?)', [('Ana', 'ana@example.com'), ('Bruno', 'bruno@example.com')]); c.commit()"
```

Declare o banco em `quantum.config.yaml`, ao lado de `components/`:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

Crie `components/users.q`:

```xml
<q:component name="users" xmlns:q="https://quantum.lang/ns">
  <q:query name="users" datasource="db">
    SELECT id, name, email FROM users ORDER BY name
  </q:query>

  <html><body>
    <h1>{users_result.recordCount} users</h1>
    <table>
      <q:loop query="users">
        <tr><td>{users.name}</td><td>{users.email}</td></tr>
      </q:loop>
    </table>
  </body></html>
</q:component>
```

Reinicie o servidor e abra `http://localhost:8080/users`: **2 users**, Ana e
Bruno.

## Passo 6: trate um formulário

Acrescente um formulário e uma `q:action` que insere uma linha — o parâmetro é
declarado, então o SQL nunca vê a entrada crua. Substitua
`components/users.q` por:

```xml
<q:component name="users" xmlns:q="https://quantum.lang/ns">
  <q:action name="add" method="POST">
    <q:param name="name" required="true" minlength="2" />
    <q:param name="email" type="email" required="true" />
    <q:query name="inserted" datasource="db">
      INSERT INTO users (name, email) VALUES (:name, :email)
      <q:param name="name" value="{name}" type="string" />
      <q:param name="email" value="{email}" type="string" />
    </q:query>
    <q:redirect url="/users" flash="Added {name}" />
  </q:action>

  <q:query name="users" datasource="db">
    SELECT id, name, email FROM users ORDER BY name
  </q:query>

  <html><body>
    <q:if condition="flash"><p>{flash}</p></q:if>
    <table>
      <q:loop query="users">
        <tr><td>{users.name}</td><td>{users.email}</td></tr>
      </q:loop>
    </table>
    <form method="POST" action="/users">
      <input name="name" /> <input name="email" type="email" />
      <button>Add</button>
    </form>
  </body></html>
</q:component>
```

Enviar `Carla` e `carla@example.com` a acrescenta à tabela e mostra
**Added Carla**; um nome de uma letra só é recusado, e nada é inserido.

## E agora?

Você aprendeu o básico! Agora explore (páginas em inglês):

- [Actions & Forms](/guide/actions) - validação, redirecionamentos, várias ações
- [Authentication](/guide/authentication) - login com verificação de senha
- [Components](/guide/components) - o sistema de componentes a fundo
- [State Management](/guide/state-management) - variáveis em detalhe
- [AI](/guide/ai) - chamadas a LLM, RAG e agentes como tags
- [Database Queries](/guide/query) - SQL e operações com dados
- [Receitas](/cookbook/) - receitas testadas, uma tarefa cada
