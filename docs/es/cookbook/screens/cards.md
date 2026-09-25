---
order: 4
title: "Tarjetas"
description: "ui:card con encabezado, cuerpo y pie, en un ui:grid; o una tarjeta con solo un título."
source: cookbook/screens/cards.md
source_hash: fb4a0ba08d55
---

# Tarjetas

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/screens/cards).
:::

**Tarea:** mostrar algunos elementos lado a lado, cada uno en su propia caja.

<<< @/../examples/cookbook/screens/cards/quantum.config.yaml{yaml}

`ui:card` contiene un `ui:card-header`, un `ui:card-body` y un
`ui:card-footer`, todos opcionales. `ui:grid columns="3"` distribuye las
tarjetas en tres columnas. Una tarjeta con solo un título y algo de texto no
necesita partes: basta con `title=`.

<<< @/../examples/cookbook/screens/cards/components/index.q{xml}

<<< @/../examples/cookbook/screens/cards/tests/cards.test.q{xml}

<<< @/../examples/cookbook/screens/cards/output/test-report.txt{text}

Ver [UI-7](../../../reference/spec.md#UI-7).
