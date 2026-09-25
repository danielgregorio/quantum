---
order: 3
title: "Pestañas"
description: "ui:tabpanel con un ui:tab por cada sección de una página."
source: cookbook/screens/tabs.md
source_hash: d1171ed5c0b9
---

# Pestañas

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/screens/tabs).
:::

**Tarea:** dividir una página en secciones, con una visible a la vez.

<<< @/../examples/cookbook/screens/tabs/quantum.config.yaml{yaml}

Cada `ui:tab` es una sección con un `title`; la primera se abre con la
página. El contenido de todas las pestañas está en la página, así que una
pestaña oculta sigue ahí para la búsqueda y para las pruebas.

<<< @/../examples/cookbook/screens/tabs/components/index.q{xml}

<<< @/../examples/cookbook/screens/tabs/tests/tabs.test.q{xml}

<<< @/../examples/cookbook/screens/tabs/output/test-report.txt{text}

`ui:tabpanel` está en el conjunto del Núcleo que dibujan el navegador, la
consola y la ventana de escritorio: [UI-7](../../../reference/spec.md#UI-7).
