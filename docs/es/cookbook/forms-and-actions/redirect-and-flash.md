---
order: 3
title: "Redirigir y decir qué pasó"
description: "Terminar una acción con q:redirect y un mensaje flash; q:flash para una advertencia; el mensaje se muestra una vez en la página siguiente."
source: cookbook/forms-and-actions/redirect-and-flash.md
source_hash: 1783ffa2ce2e
---

# Redirigir y decir qué pasó

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/forms-and-actions/redirect-and-flash).
:::

**Tarea:** después de enviar un formulario, llevar al navegador a una página y
decirle qué pasó, una sola vez.

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/migrations/V001_notes.sql{sql}

`q:redirect` termina la acción. Su `flash` acepta expresiones y se convierte
en `flash` en la siguiente página que se renderiza, con `flashType` en
`success`. Para otro tipo de mensaje, `q:flash type="warning"` define ambos
antes de la redirección. La URL puede ser cualquier página de la aplicación.

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/components/index.q{xml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/components/done.q{xml}

La segunda prueba abre la página de nuevo después de la redirección: el
mensaje flash ya no está, y `flash` es `''`.

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/tests/notes.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/redirect-and-flash/output/test-report.txt{text}

Ver [ACT-3](../../../reference/spec.md#ACT-3).
