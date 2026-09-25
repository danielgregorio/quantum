---
source: stability/index.md
source_hash: b2f88ba7b500
---

# Estabilidad

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. La página en
inglés se genera a partir de `SUPPORT_TIERS.md` y esta traducción puede
quedar atrás; si algo no coincide, vale el [original en inglés](/stability/).
:::

Lo que Quantum promete, etiqueta por etiqueta. Desde la 1.0, **el Núcleo (Core)
y la IA siguen el versionado semántico (semver)**: una versión 1.x no rompe un
programa que usa solo esos niveles; su significado lo fijan las reglas de la
[especificación](/reference/spec), y una ruptura espera a la 2.0. Experimental
y Laboratorio no tienen esa promesa.

Esta página es la promesa. Lo que de verdad funciona hoy se mide en la página
de [Estado](/status/), y cada cambio está en el [registro de cambios](/changelog/).

## La frase

> **Quantum: aplicaciones web declarativas en XML, con IA y RAG en el propio
> lenguaje. Sin cadena de build, sin JavaScript, sin framework de front-end.**

Lo que no encaja en esa frase no pertenece al README ni a la presentación.
Puede seguir existiendo, en otro nivel o en otro repositorio.

## Para quién es

Personas que desarrollan solas y equipos pequeños que construyen herramientas
internas, paneles, pantallas de administración y aplicaciones de IA, y que no
quieren una cadena de build de front-end.

---

## Los niveles

### Núcleo: lo que el framework es

Documentado, probado de punta a punta, estable. Una ruptura aquí es un bug
crítico. Ninguna etiqueta entra sin: una regla en `SPEC.md` con una prueba que
la cite, un ejemplo que funcione, una página de guía y una línea en
`FEATURE_STATUS.md`.

| Etiqueta | Función |
|---|---|
| `q:component` | Unidad de composición, con `q:param` / `q:return` |
| `q:set` | Variables y ámbitos (`session.` / `application.` / `request.`) |
| `q:if` | Condicional (`q:elseif` / `q:else`) |
| `q:loop` | Iteración (array, lista, rango, consulta) |
| `q:function` | Función reutilizable, con `q:param` / `q:return` |
| `q:query` | SQL parametrizado: `q:param` obligatorio, inyección imposible por construcción; paginación, verificación del esquema (`quantum check`), historial (DB-11) |
| `q:transaction` | Consultas que se confirman o se revierten juntas (DB-4) |
| `q:action` | Manejador de formularios, con `q:redirect` y `q:flash`; las reglas de `q:param` se verifican en el servidor y se muestran junto a cada campo |
| `q:invoke` | Llamar a una función, a un componente o a un servicio HTTP |
| `q:data` | Importar y transformar CSV/JSON/XML |
| `q:import` / `q:slot` | Composición de componentes |
| `q:file` | Archivos subidos bajo `paths.uploads`, y descargas cuyo acceso decide una página (FILE-1, FILE-2) |
| `q:mail` | Correo mediante la configuración `mail:`, con un modo de registro para desarrollo (MAIL-1, MAIL-2) |
| `ui:*`, el conjunto del Núcleo | Pantallas en una página, enumeradas en la regla UI-7. El navegador (`quantum start`), la consola (`quantum console`) y la ventana (`quantum desktop`, la página en una ventana local) las dibujan con el mismo significado; un único guion de paridad se ejecuta en un navegador real y en la consola |
| `require_auth` / `require_role` | Autenticación y autorización por componente, sobre el ámbito `session` (decisión D4); `hashPassword` / `verifyPassword` en las expresiones |

### IA: la razón de ser del proyecto

El mismo contrato que el Núcleo, más una prueba en vivo contra un modelo real
antes de cada versión. Es lo que Quantum tiene y ningún otro framework
declarativo tiene.

| Etiqueta | Función | Lo prueba |
|---|---|---|
| `q:llm` | Completado y chat; `knowledge=` responde a partir de una base y cita sus fuentes; `stream="true"` envía la respuesta mientras se escribe | IA-1…IA-8, `projects/docs-assistant` |
| `q:knowledge` | Una base de conocimiento vectorial (RAG) sobre texto, archivos y consultas | IA-2, IA-6, IA-8, `projects/docs-assistant` |
| `q:agent` | Un agente cuyas herramientas se declaran en `.q`, con un contrato de fallo y un presupuesto de tiempo | IA-4, IA-5, `projects/shop-agent` |

### Experimental: existe, sin promesa

Se mantiene y funciona, pero **fuera del README y de la presentación**, sin
garantía de estabilidad de la API. Pasa al Núcleo con el mismo rigor: una regla
de la especificación con su prueba, un ejemplo, una página de guía y una línea
en el estado.

| Área | Etiquetas |
|---|---|
| Multiagente | `q:team`: todavía sin regla en la especificación ni aplicación que lo demuestre |
| Tareas | `q:job`, `q:schedule`, `q:thread` |
| Mensajería | `q:message`, `q:queue`, `q:subscribe`, `q:messageAck`, `q:messageNack`, `q:websocket`, `q:websocket-send`, `q:websocket-close` |
| Servicios | `q:log`, `q:dump` |
| Scripting | `q:python`, `q:pyclass`, `q:pyimport`: **desactivados por defecto**, se activan con `security.python_scripting` (ver SECURITY.md) |
| Eventos | `q:dispatchEvent` |
| Decoradores | `q:decorator` / `q:pydecorator`: un parser y un nodo del AST sin consumidor en el entorno de ejecución; o se diseñan decoradores para `q:function` o las etiquetas se van. Sin documentar hasta entonces |
| UI / otros destinos | Elementos `ui:*` fuera del conjunto del Núcleo (solo en el navegador; la consola dice que no los dibuja); la compilación independiente `q:application type="ui"` (`--target html`/`textual`, solo diseño, UI-8); el destino de terminal (`qt:`), htmx, islands |

### Laboratorio: se queda en el repositorio, fuera de la promesa

Decisión D1/D2 (2026-09-10): estos proyectos **se quedan en el repositorio**
porque exigen más del lenguaje: jugando es como aparecen las funcionalidades y
los bugs que el núcleo necesita. No forman parte de la presentación ni tienen
promesa de estabilidad, y el entorno de ejecución avisa una vez cuando uno se
ejecuta (`quantum/core/tiers.py`). Sus pruebas se ejecutan en CI en un job
propio (`pytest -m laboratory`), obligatorio como el principal, para que un
cambio en el núcleo que rompa un juego se note, y un CI en rojo diga de
inmediato qué lado se rompió.

| Área | Nota |
|---|---|
| Motor de juegos 2D (`qg:`), generación de código para Godot | Los juegos de `projects/` y `examples/` los construye el generador de código; nunca edites la salida generada. Los cambios del lenguaje que rompen un juego migran sus fuentes `.q` en el mismo cambio |
| `quantum-as4` (compilador MXML/AS4 → JS) | Tiene una regresión abierta en `test_transpiler_comprehensive.py` |
| `quantum run --target mobile` (React Native) | Traduce `q:set`/`q:function` a JavaScript por su cuenta, lo contrario de "un solo entorno de ejecución". Los teléfonos quedan fuera de la 1.0. Avisa una vez (`tiers.warn_ui_target`) |

---

## Cómo evitamos que esto se pudra

`ROADMAP.md` se pudrió porque se mantenía a mano y nadie lo verificaba. Las
defensas:

1. **`FEATURE_STATUS.md` se genera** ejecutando de verdad los ejemplos
   (`scripts/generate-feature-status.py`).
2. **`manifest.yaml` no tiene autoridad** sobre "funciona o no": 29 archivos
   sincronizados a mano es justamente la razón por la que se desviaron.
3. **El motor aplica los niveles** (`quantum/core/tiers.py`, probado en
   `tests/unit/test_tiers.py`); esta página y ese archivo cambian juntos.
4. **Este documento solo cambia por una decisión explícita**, y el cambio es
   pequeño: mover una etiqueta de un nivel a otro.

## Cambios para la 1.0

| Cambio | Por qué |
|---|---|
| Los nombres de los niveles están en inglés: Core, AI, Experimental, Laboratory (antes eran Core, Diferencial, Experimental, Laboratório) | El repositorio está en inglés |
| `q:file`, `q:mail` y `q:transaction` → Núcleo | Cada uno tiene reglas en la especificación con pruebas (FILE-1/2, MAIL-1/2, DB-4) y una aplicación en CI que lo usa (`projects/helpdesk`, `projects/blog`) |
| `q:team` → Experimental | Sin regla en la especificación ni aplicación que lo demuestre; el nivel de IA promete solo lo que está demostrado |
| Conjunto del Núcleo de `ui:*` → Núcleo (0.16) | UI-1…UI-14, el guion de paridad, tres renderizadores |
| `q:decorator` / `q:transaction` quedaron "sin nivel" | `q:transaction` recibió su regla (DB-4); los decoradores son Experimentales, con la nota de arriba |
