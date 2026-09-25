---
source: guide/getting-started.md
source_hash: e67760de8b10
---

# Primeros pasos

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/getting-started).
:::

¡Te damos la bienvenida a Quantum! Esta guía te ayuda a poner en marcha el framework Quantum en pocos minutos.

## ¿Qué es Quantum? {#what-is-quantum}

Quantum es un **framework declarativo full-stack** para aplicaciones web escritas en XML. Está diseñado con la filosofía de "simplicidad por encima de la configuración": hacer simples las tareas complejas y mantener el lenguaje limpio y legible.

### Beneficios principales {#key-benefits}

- **Sin JavaScript** - Construye aplicaciones interactivas usando solo XML y SQL
- **La IA como etiquetas** - Llamadas a modelos, RAG y agentes con herramientas, sin código Python de pegamento
- **Full-stack** - Consultas a bases de datos, formularios, sesiones y autenticación incluidos
- **Entrada validada** - Los parámetros declarados se verifican por tipo antes de que tu código se ejecute

## Requisitos previos {#prerequisites}

- **Python 3.12+**
- **pip**

## Instalación {#installation}

```bash
pip install quantum-framework
quantum --version
```

Los extras opcionales (PostgreSQL/MySQL, RAG, jobs, websockets) y la dependencia
adicional del destino de escritorio están en [Instalación](/es/guide/installation).

## Tu primer componente {#your-first-component}

Crea un archivo llamado `hello.q`:

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World!" />
</q:component>
```

**Output:** `Hello World!`

Ejecútalo:

```bash
quantum run hello.q
```

## Agregar contenido dinámico {#adding-dynamic-content}

Hagámoslo más interesante con variables y bucles:

```xml
<q:component name="Greetings" xmlns:q="https://quantum.lang/ns">
  <!-- Define a variable -->
  <q:set name="greeting" value="Hello" />

  <!-- Loop through a list -->
  <q:loop type="list" var="name" items="Alice,Bob,Charlie">
    <q:return value="{greeting} {name}!" />
  </q:loop>
</q:component>
```

**Output:**

```
["Hello Alice!", "Hello Bob!", "Hello Charlie!"]
```

## Usar condicionales {#using-conditionals}

```xml
<q:component name="AgeCheck" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="25" />

  <q:if condition="age >= 18">
    <q:return value="You are an adult" />
  </q:if>
  <q:else>
    <q:return value="You are a minor" />
  </q:else>
</q:component>
```

**Output:** `You are an adult`

## Crear funciones {#creating-functions}

```xml
<q:component name="Calculator" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:set name="result" value="{a + b}" />
    <q:return value="{result}" />
  </q:function>

  <q:set name="sum" value="{add(5, 3)}" />
  <q:return value="5 + 3 = {sum}" />
</q:component>
```

**Output:** `5 + 3 = 8`

## Aplicaciones web {#web-applications}

Las páginas son componentes en una carpeta `components/`, y el nombre del archivo es la URL.
Crea `components/index.q`:

```xml
<q:component name="index" xmlns:q="https://quantum.lang/ns">
  <html><body>
    <h1>Welcome to My App</h1>
    <p>Now: {dateFormat(now(), '%H:%M')}</p>
  </body></html>
</q:component>
```

**Shows:** `Welcome to My App`

Inicia el servidor desde la carpeta que contiene `components/`:

```bash
quantum start
```

Abre `http://localhost:8080`. El [Inicio rápido](/es/guide/quick-start) continúa
con una base de datos y un formulario.

::: warning `q:application type="html"`
Algunas páginas antiguas describen las aplicaciones web como un `q:application type="html"` con bloques
`q:route`. Esa forma nunca ejecutó sus rutas y se eliminó en la 0.11 — usa
`components/` como arriba. Ver [q:application](/guide/applications).
:::

## Modo de depuración {#debug-mode}

Para obtener información detallada de la ejecución:

```bash
quantum run hello.q --debug
```

Esto muestra:
- Detalles del análisis del archivo
- Información sobre la generación del AST
- Pasos de validación
- Flujo de ejecución

## Próximos pasos {#next-steps}

- [Detalles de la instalación](/es/guide/installation) - Guía completa de configuración
- [Estructura del proyecto](/guide/project-structure) - Cómo organizar tu código
- [Componentes](/es/guide/components) - Todo sobre los componentes
- [IA](/es/guide/ai) - Llamadas a LLM, RAG y agentes como etiquetas
- [Recetario](/es/cookbook/) - Recetas probadas, una tarea cada una
