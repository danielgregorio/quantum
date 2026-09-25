---
order: 1
title: "Un diseño que se adapta a la pantalla"
description: "ui:hbox lado a lado en una pantalla ancha y apilado en una angosta, con grow, width y hide-below."
source: cookbook/screens/responsive-layout.md
source_hash: a5899ccac57b
---

# Un diseño que se adapta a la pantalla

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/screens/responsive-layout).
:::

**Tarea:** un menú lateral junto al contenido en una pantalla ancha, y encima de él en un teléfono.

<<< @/../examples/cookbook/screens/responsive-layout/quantum.config.yaml{yaml}

`stack-below="md"` pone las cajas de un `ui:hbox` una encima de otra por
debajo del ancho `md` (768 px en el navegador, 96 columnas en una terminal).
`width` fija la caja lateral, `grow="true"` le da el resto al contenido, y
`hide-below="lg"` deja una ayuda solo para pantallas anchas.

<<< @/../examples/cookbook/screens/responsive-layout/components/index.q{xml}

`quantum test` lee el texto de la página, no su diseño, así que verifica el
contenido:

<<< @/../examples/cookbook/screens/responsive-layout/tests/layout.test.q{xml}

<<< @/../examples/cookbook/screens/responsive-layout/output/test-report.txt{text}

El apilado en sí se verifica en la consola, donde una prueba puede medirlo:
con 80 columnas `#main` está apilado, con 140 está lado a lado y `#side`
tiene 220 / 8 = 27 columnas de ancho
([`tests/docs/test_cookbook_console.py`](https://github.com/danielgregorio/quantum/blob/main/tests/docs/test_cookbook_console.py)). La regla:
[UI-2](../../../reference/spec.md#UI-2).
