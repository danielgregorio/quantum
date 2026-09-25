---
source: guide/why-quantum.md
source_hash: b3e57fbe210d
---

# Por qué Quantum

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/why-quantum).
:::

**Quantum construye aplicaciones web a partir de páginas XML declarativas,
con la base de datos, los formularios, las sesiones y la IA en el propio
lenguaje. Sin cadena de build, sin JavaScript, sin framework de front-end.**

Es para quien desarrolla solo o en un equipo pequeño herramientas internas,
paneles, pantallas de administración y aplicaciones que usan un modelo de
lenguaje: el tipo de software en el que una cadena de build de front-end
cuesta más que el producto.

## Cómo se ve una página

```xml
<q:component name="Tasks">
  <q:action name="add" method="POST">
    <q:param name="title" required="true" minlength="3" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title) VALUES (:title)
      <q:param name="title" value="{title}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Added: {title}" />
  </q:action>

  <q:query name="tasks" datasource="db">SELECT id, title FROM tasks ORDER BY id</q:query>

  <ui:window title="Tasks">
    <q:if condition="flash"><ui:alert variant="info">{flash}</ui:alert></q:if>
    <ui:form on-submit="add" submit="Add" />
    <ui:table source="{tasks}" />
  </ui:window>
</q:component>
```

Esa es toda la funcionalidad: el formulario dibuja su campo a partir del
`q:param` de la acción (con `required` y `minlength` verificados en el
navegador y en el servidor), la consulta está parametrizada por construcción,
y la misma página funciona en un navegador (`quantum start`), en una terminal
(`quantum console`) y en una ventana de escritorio (`quantum desktop`).

## Qué es diferente

- **Un archivo por página, de arriba abajo.** Las guardas, las acciones, las
  consultas y la pantalla están en el orden en que se ejecutan
  ([cómo se ejecuta una página](/guide/how-a-page-runs)).
- **Las reglas viven en un solo lugar.** Un `q:param` dice qué debe ser un
  campo; el formulario, el servidor y `quantum check` lo leen.
- **La IA es parte del lenguaje.** `q:llm` responde a partir de una base
  `q:knowledge` y cita sus fuentes, transmite la respuesta mientras la
  escribe, y `q:agent` llama herramientas que escribes como funciones de
  Quantum, cada una con un contrato de fallo que la página puede manejar
  ([IA](/guide/ai)).
- **No finge.** Un correo sin servidor, una fuente de conocimiento que no se
  puede leer, un atributo que una etiqueta `q:` no tiene: cada uno es un error
  que dice qué hacer, no un éxito silencioso.

## Cómo sabemos que funciona

- Una [especificación](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)
  con reglas numeradas; el conjunto de pruebas falla cuando una regla no tiene
  prueba.
- Aplicaciones reales en `projects/`, cada una probada de punta a punta en CI:
  una lista de tareas (navegador, consola, escritorio), un blog, un panel, una
  mesa de ayuda con archivos subidos y correo, un asistente de documentación
  (RAG) y un agente sobre una base de datos SQLite. Las aplicaciones de IA
  también se prueban contra un servidor de modelos real.
- Una versión se construye solo después de que todo el conjunto de pruebas
  pasa en el commit etiquetado, y el ejemplo de esta página se ejecuta en CI
  tal como se muestra.

## Qué no es

- **No es un framework móvil.** Los teléfonos quedan fuera de la 1.0; el
  destino React Native es un experimento.
- **No es un framework SPA.** Las páginas se generan en el servidor; el
  navegador recibe HTML, más pequeños scripts donde una página los necesita
  (búsqueda mientras escribes, respuestas transmitidas).
- **No está atado a un proveedor de modelos, pero tampoco es magia.** Un
  modelo local pequeño responde peor que uno grande; Quantum muestra las
  fuentes para que quien lee pueda verificar.
- **SQLite primero.** Existen drivers para PostgreSQL y MySQL, pero se usan
  menos; las migraciones, los planes de esquema y `quantum check` están
  probados en SQLite.

Lo que promete cada parte está en
[SUPPORT_TIERS.md](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md)
y en [Estabilidad](/es/stability/): Núcleo e IA son estables; Experimental
funciona sin promesa de estabilidad; el Laboratorio (juegos, Godot, AS4) vive
en el repositorio para exigir más del lenguaje.
