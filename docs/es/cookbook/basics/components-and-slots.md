---
order: 8
title: "Componentes reutilizables"
description: "Un componente con props y un slot, importado de una carpeta _ que nunca se sirve."
source: cookbook/basics/components-and-slots.md
source_hash: e3f5b5e42dc9
---

# Componentes reutilizables

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/basics/components-and-slots).
:::

**Tarea:** escribir una tarjeta una vez y usarla en cualquier página, con contenido distinto.

<<< @/../examples/cookbook/basics/components-and-slots/quantum.config.yaml{yaml}

Un componente también es un archivo `.q`. Sus `q:param`s son sus props, y
`q:slot` es donde va el contenido de quien lo usa. Guárdalo en una carpeta
cuyo nombre empieza con `_`: se puede importar, y nunca responde a una URL.

<<< @/../examples/cookbook/basics/components-and-slots/components/_shared/Card.q{xml}

`q:import` lo trae a la página, y `<Card>` lo usa. Cada atributo es una prop,
y el contenido entre las etiquetas llena el slot, calculado con las variables
de la página:

<<< @/../examples/cookbook/basics/components-and-slots/components/index.q{xml}

<<< @/../examples/cookbook/basics/components-and-slots/tests/cards.test.q{xml}

<<< @/../examples/cookbook/basics/components-and-slots/output/test-report.txt{text}

Ver [COMP-1](../../../reference/spec.md#COMP-1), [COMP-3](../../../reference/spec.md#COMP-3)
y [ROUTE-3](../../../reference/spec.md#ROUTE-3).
