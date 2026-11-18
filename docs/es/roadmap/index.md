---
title: Hoja de ruta
source: roadmap/index.md
source_hash: 3ba5ae8316ba
---

# Hoja de ruta

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/roadmap/).
:::

Qué es Quantum hoy y qué viene después. Aquí no hay fechas, ni promesas más
allá de los [niveles de soporte](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md):
un elemento está hecho cuando salió en una versión y su entrada en el
[registro de cambios](/changelog/) lo dice.

Cada elemento muestra su estado: **planeado** (aprobado, sin empezar), **en
diseño** (se está escribiendo antes de cualquier código) o **en progreso** (se
está construyendo ahora).

## 1.1: hoy

Quantum son aplicaciones declarativas en XML, con IA y RAG en el propio
lenguaje. La 1.1 lleva una aplicación a cada lugar donde se puede leer: el
navegador, una ventana propia, una pantalla de texto dibujada por Godot, la
terminal, un instalador para Linux, Windows y macOS, y el teléfono, con una
API REST propia ([qué cambió](/changelog/v1-1-0), en inglés). Lo que promete
lo fijan sus niveles:

- El **Núcleo** (componentes, consultas y transacciones, acciones y
  formularios, archivos, correo, autenticación, el conjunto del Núcleo de
  `ui:*`) y la **IA** (`q:llm`, `q:knowledge`, `q:agent`) siguen el versionado
  semántico: una versión 1.x no rompe un programa que usa solo esos niveles.
  La IA además se prueba contra un modelo real antes de cada versión.
- Las etiquetas **Experimentales** funcionan, sin promesa de estabilidad.
- Los proyectos del **Laboratorio** se quedan en el repositorio porque exigen
  más del lenguaje; no forman parte del producto y no tienen ninguna promesa.

Lo que funciona hoy se mide, no se afirma: ver [Estado](/status/). Cada
etiqueta y cada regla están en la [Referencia](/reference/).

## Lo próximo

### IA

| Elemento | Estado |
|---|---|
| Un modelo falso para desarrollo: construir y probar páginas de IA sin ningún modelo en ejecución, con respuestas iguales en cada ejecución | planeado |
| La IA en el [panel de desarrollo](/tools/dev-panel): cada llamada que hizo una página, con su prompt, las fuentes que usó, la respuesta, el tiempo y los tokens | planeado |
| Presupuestos y ocultamiento de datos: un límite de gasto por aplicación, y los datos personales eliminados antes de salir hacia el modelo, con el registro de ambos | planeado |
| Conversaciones que recuerdan, y un `ui:chat` para mantenerlas | planeado |

### Una aplicación que se conoce a sí misma

| Elemento | Estado |
|---|---|
| `quantum map`: qué páginas y acciones leen y escriben cada tabla | planeado |
| `quantum explain page.q`: qué lee, qué escribe y de qué depende una página, en texto simple | planeado |
| `q:cache` por tabla: un fragmento en caché que se renueva cuando una escritura toca una de sus tablas, sin un tiempo de expiración que adivinar | planeado |

### Pruebas

`quantum test` salió en la 1.0 ([Testing](/guide/testing), en inglés). Lo
próximo:

| Elemento | Estado |
|---|---|
| Una ejecución de prueba contra cada pantalla: el navegador y la consola | planeado |
| Pruebas derivadas de las reglas de una acción, que Quantum escribe por ti | planeado |
| Pruebas de IA reproducidas desde una grabación, para que funcionen sin un modelo | planeado |
| Cobertura en los términos de la propia aplicación: qué páginas, acciones y reglas alcanza un conjunto de pruebas | planeado |

### El sitio web

| Elemento | Estado |
|---|---|
| Recetario: recetas cortas, cada una probada en CI | en progreso |
| El sitio en más idiomas | en progreso |
| Un [playground](/playground/): escribir Quantum y ejecutarlo en el navegador | hecho |
| Benchmarks que cualquiera puede volver a ejecutar | planeado |

## Laboratorio

| Elemento | Estado |
|---|---|
| Games 2: los juegos como una simulación declarativa determinista, en la que las mismas entradas siempre dan el mismo juego, para que un juego se pueda probar y reproducir — un compilador a Godot 4, ocho juegos ([Hopper, Keep, Drift, las demos Pong y Dodge the Creeps de Godot, un tower defense, un juego de lucha y ajedrez](/targets/games)), cada uno reproducido en CI y [jugable en el sitio](/targets/play), y multijugador en lockstep a partir del mismo determinismo (`PLAN_MULTIPLAYER.md`) | hecho |
| Games 3: lo que el lenguaje de juegos toma de Godot y Unity — lógica de juego, apuntar, rompecabezas y aventura, opciones y partidas guardadas, táctil, puestos y pantalla dividida, luces, mapas de hexágonos (`PLAN_GAMES_3.md`) — con diecisiete juegos [jugables en el sitio](/targets/play) | hecho |
| PandaFoot: un juego de mánager de fútbol al estilo de Elifoot 2, en una pantalla de texto, en una beta abierta cuyos jugadores informan desde dentro del juego (`PLAN_PANDAFOOT.md`) | en progreso |
| Un servidor de juegos (`q:gameserver`): un mundo para quinientos jugadores escrito en etiquetas — vistas, bestias, un libro de cuentas, chat, grupos, misiones, personajes con IA — con su motor en Rust (`PLAN_GAME_SERVER.md`, `PLAN_WORLD_ENGINE.md`) | en progreso |

El trabajo del Laboratorio no tiene ninguna promesa: puede cambiar o detenerse
en cualquier momento.
