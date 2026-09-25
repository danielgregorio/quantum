---
source: guide/quick-start.md
source_hash: c82f4c234ab8
---

# Inicio rápido

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/quick-start).
:::

Construye tu primera aplicación Quantum en 5 minutos.

Cada paso de esta página se ejecuta en CI (`tests/docs/test_guide_quick_start.py`).

## Paso 1: Crea un componente

Crea un archivo llamado `counter.q`:

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

**Output:** `Count: 2, doubled: 4`

Ejecútalo: `quantum run` imprime lo que devuelve el componente:

```bash
quantum run counter.q
```

```text
[SUCCESS] Result: Count: 2, doubled: 4
```

## Paso 2: Agrega un bucle

Crea `todo-list.q`:

```xml
<q:component name="TodoList" xmlns:q="https://quantum.lang/ns">
  <q:set name="tasks" type="array" value='["Buy groceries", "Walk the dog", "Write code"]' />

  <!-- each q:return adds one item to the result -->
  <q:loop type="array" var="task" items="{tasks}">
    <q:return value="- {task}" />
  </q:loop>
</q:component>
```

**Output:** `["- Buy groceries", "- Walk the dog", "- Write code"]`

Un `q:return` dentro de un bucle no detiene el bucle: cada valor se acumula, y
cuando el bucle termina el componente devuelve la lista (LOOP-1, LOOP-2). Un
bucle que no ejecuta ningún `q:return` deja que la ejecución continúe con lo
que viene después.

## Paso 3: Agrega condicionales

Crea `weather.q`:

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

**Output:** `Nice weather for a walk.`

## Paso 4: Sirve una página web

Las páginas viven en una carpeta `components/`; el nombre del archivo es la
URL. Crea `components/index.q`:

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

Inicia el servidor desde la carpeta que contiene `components/`:

```bash
quantum start
```

Abre `http://localhost:8080`: la página muestra los tres elementos y
`10 + 5 = 15`. `components/about.q` se serviría en `/about`. Detén el servidor
con `quantum stop`.

> Sin `<!DOCTYPE html>` en el archivo: un `.q` es XML, y un DOCTYPE solo es
> válido antes del elemento raíz. El servidor lo agrega a la respuesta.

## Paso 5: Lee de una base de datos

Crea una base de datos SQLite con una tabla (sirve cualquier Python; Quantum
ya lo necesita):

```bash
python -c "import sqlite3, os; os.makedirs('data', exist_ok=True); c = sqlite3.connect('data/app.db'); c.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)'); c.executemany('INSERT INTO users (name, email) VALUES (?, ?)', [('Ana', 'ana@example.com'), ('Bruno', 'bruno@example.com')]); c.commit()"
```

Declárala en `quantum.config.yaml`, junto a `components/`:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

Crea `components/users.q`:

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

Reinicia el servidor y abre `http://localhost:8080/users`: **2 users**, Ana y
Bruno.

## Paso 6: Maneja un formulario

Agrega un formulario y una `q:action` que inserta una fila: el parámetro está
declarado, así que el SQL nunca ve la entrada sin procesar. Reemplaza
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

Enviar `Carla` y `carla@example.com` la agrega a la tabla y muestra
**Added Carla**; un nombre de una sola letra se rechaza, y no se inserta nada.

## ¿Qué sigue?

Ya aprendiste lo básico. Ahora explora (en inglés):

- [Acciones y formularios](/guide/actions): validación, redirecciones, varias acciones
- [Autenticación](/guide/authentication): inicio de sesión con verificación de contraseña
- [Componentes](/guide/components): el sistema de componentes en detalle
- [Manejo de estado](/guide/state-management): variables en detalle
- [IA](/guide/ai): llamadas a LLM, RAG y agentes como etiquetas
- [Consultas a bases de datos](/guide/query): SQL y operaciones con datos
- [Recetario](/cookbook/): recetas probadas, una tarea cada una
