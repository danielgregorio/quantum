---
title: Hoja de ruta
source: roadmap/index.md
source_hash: bf70795ae40e
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

## 1.0: hoy

Quantum 1.0 son aplicaciones web declarativas en XML, con IA y RAG en el propio
lenguaje. Lo que promete la 1.0 lo fijan sus niveles:

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
| Un playground: escribir Quantum y ejecutarlo en el navegador | planeado |
| Benchmarks que cualquiera puede volver a ejecutar | planeado |

## Laboratorio

| Elemento | Estado |
|---|---|
| Games 2: los juegos como una simulación declarativa determinista, en la que las mismas entradas siempre dan el mismo juego, para que un juego se pueda probar y reproducir | en diseño |

El trabajo del Laboratorio no tiene ninguna promesa: puede cambiar o detenerse
en cualquier momento.
