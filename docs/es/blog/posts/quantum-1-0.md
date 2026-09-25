---
title: Quantum 1.0
date: 2026-09-25
description: Aplicaciones web declarativas en XML, con IA y RAG en el lenguaje — qué promete la 1.0, cómo se verificó y qué viene después.
source: blog/posts/quantum-1-0.md
source_hash: 83905caaa8ae
---

# Quantum 1.0

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/blog/posts/quantum-1-0).
:::

*2026-09-25*

Salió Quantum 1.0. Este artículo dice qué es, qué promete el número de
versión, cómo verificamos que la promesa se cumple y qué viene después.

## Qué es Quantum

**Aplicaciones web declarativas en XML, con IA y RAG en el propio lenguaje.
Sin cadena de build, sin JavaScript, sin framework de front-end.**

Una página es un archivo `.q`. El estado, el SQL parametrizado, los
formularios y su validación, los componentes, la autenticación, la subida de
archivos y el correo son etiquetas; también lo son una llamada a un LLM que
responde a partir de una base de conocimiento y cita sus fuentes, y un agente
cuyas herramientas se escriben en el propio Quantum. `quantum start` sirve una
carpeta de páginas; no hay nada que compilar.

Es para personas que desarrollan solas y equipos pequeños que construyen
herramientas internas, paneles, pantallas de administración y aplicaciones de
IA, y que prefieren no mantener una cadena de build de front-end. No es un
reemplazo de propósito general para un framework de JavaScript.

## Qué promete la 1.0

La promesa está escrita en
[Support tiers](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md)
(ver también [Estabilidad](/es/stability/)), y el motor la hace cumplir:

- **Núcleo (Core)**: componentes, `q:set`, `q:if`, `q:loop`, `q:function`,
  `q:query` y `q:transaction`, `q:action` y los formularios, `q:invoke`,
  `q:data`, composición, archivos, correo, el conjunto del Núcleo de `ui:*`,
  autenticación.
- **IA**: `q:llm`, `q:knowledge`, `q:agent`.
- **Experimental**: etiquetas que funcionan pero sin promesa (tareas,
  mensajería, websockets, scripting en Python, el destino de terminal, …). Una
  etiqueta fuera del Núcleo y de la IA imprime un aviso la primera vez que se
  ejecuta.
- **Laboratorio**: el motor de juegos 2D y otros destinos que se mantienen
  para ejercitar el lenguaje, sin ninguna promesa.

Desde la 1.0, **el Núcleo y la IA siguen el versionado semántico**: una versión
1.x no rompe un programa que usa solo esos niveles. Un cambio que lo rompería
espera a la 2.0. Experimental y Laboratorio pueden cambiar en cualquier
versión.

## Cómo se verificó

Una promesa vale lo que vale aquello que la verifica. Cuatro cosas lo hacen:

1. **Una especificación con identificadores de reglas.** [SPEC.md](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)
   dice qué significa un programa de Quantum en 137 reglas numeradas
   (`LOOP-2`, `DB-4`, `IA-6`…), y quedó congelada en la 1.0. Cada regla está
   citada por al menos una prueba de conformidad (866 en total), y CI falla si
   una regla no tiene prueba o si una prueba cita una regla que no existe.
2. **Aplicaciones que la usan.** El repositorio tiene aplicaciones pequeñas y
   reales para cada nivel: una lista de tareas dibujada con `ui:*` en el
   navegador, la terminal y una ventana de escritorio; un blog; una mesa de
   ayuda con adjuntos y correo; una transferencia bancaria dentro de una sola
   `q:transaction`; un asistente de documentación y un agente de tienda para
   las etiquetas de IA.
3. **`quantum test`.** Las aplicaciones se prueban en su propio lenguaje: un
   `*.test.q` visita una página, envía una acción y verifica la redirección, el
   mensaje flash, las filas de la tabla y el historial, cada prueba sobre una
   base de datos nueva construida a partir de las migraciones. Los conjuntos de
   pruebas de las aplicaciones se ejecutan en CI.
4. **Pruebas de IA en vivo.** Las etiquetas de IA se prueban contra un
   servidor de modelos real antes de cada versión, con verificaciones
   estructurales (se llamó a la herramienta, se recuperó el fragmento
   correcto), nunca texto exacto.

Y la [página de estado](/status/) no se escribe a mano: un script ejecuta cada
ejemplo e informa qué se analiza y qué se ejecuta.

## Qué cambió en el camino

El camino de la 0.9 a la 1.0 se trató sobre todo de hacer verdadera la
promesa: un comportamiento que antes fallaba en silencio (un nombre mal
escrito, un atributo que no hacía nada, una clave que faltaba, un campo de
consulta que no existe) ahora es un error que señala la línea. El
[registro de cambios](/changelog/v1-0-0) tiene los detalles, versión por
versión.

## Qué viene después

- **`quantum test` crece**: más de lo que hace una aplicación debería poder
  verificarse en su propio lenguaje.
- **De Experimental al Núcleo, una etiqueta a la vez**, y solo con una regla de
  la especificación, una prueba que la cite, un ejemplo que funcione y una
  página de guía.
- **Este sitio**: traducciones y un dominio propio.

Los bugs, las preguntas y las ideas son bienvenidos en
[GitHub Issues](https://github.com/danielgregorio/quantum/issues). Si Quantum
te resulta útil, la [página de apoyo](/es/sponsor/) dice qué paga la ayuda.
