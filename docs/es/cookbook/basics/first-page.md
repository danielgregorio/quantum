---
order: 1
title: "Una primera página, y una segunda"
description: "Cada archivo en components/ es una página en su propia URL; una URL sin archivo es 404."
source: cookbook/basics/first-page.md
source_hash: 2f3e3e2fd454
---

# Una primera página, y una segunda

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/basics/first-page).
:::

**Tarea:** servir dos páginas que se enlazan entre sí.

<<< @/../examples/cookbook/basics/first-page/quantum.config.yaml{yaml}

Un archivo en `components/` es una página, en la URL de su ruta:
`components/index.q` responde a `/` y `components/about.q` responde a `/about`.
Inicia el servidor con `quantum start` en la carpeta que tiene
`quantum.config.yaml`.

<<< @/../examples/cookbook/basics/first-page/components/index.q{xml}

<<< @/../examples/cookbook/basics/first-page/components/about.q{xml}

Una URL sin archivo responde `404`:

<<< @/../examples/cookbook/basics/first-page/tests/pages.test.q{xml}

<<< @/../examples/cookbook/basics/first-page/output/test-report.txt{text}

Ver [ROUTE-1](../../../reference/spec.md#ROUTE-1).
