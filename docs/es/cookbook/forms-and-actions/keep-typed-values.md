---
order: 2
title: "Un formulario rechazado conserva lo escrito"
description: "Después de un rechazo, el formulario vuelve lleno con los valores enviados, una vez, para que nadie escriba dos veces un mensaje largo."
source: cookbook/forms-and-actions/keep-typed-values.md
source_hash: fb01e4e771dc
---

# Un formulario rechazado conserva lo escrito

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/forms-and-actions/keep-typed-values).
:::

**Tarea:** cuando el servidor rechaza un formulario, devolverlo con lo que la
persona escribió, no vacío.

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/migrations/V001_messages.sql{sql}

No hay nada que escribir para esto. Después de un rechazo, el siguiente
renderizado de un `ui:form` llena cada campo con el valor enviado, una vez,
como el mensaje flash. Un campo de contraseña o de archivo nunca vuelve.
`rows="6"` hace del mensaje un campo de varias líneas.

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/components/index.q{xml}

La primera prueba envía una dirección mala con un mensaje bueno: la dirección
se rechaza y el mensaje sigue en su campo. La segunda abre la página de nuevo:
los valores ya no están.

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/tests/contact.test.q{xml}

<<< @/../examples/cookbook/forms-and-actions/keep-typed-values/output/test-report.txt{text}

Ver [UI-9](../../../reference/spec.md#UI-9) y, para el campo de varias líneas,
[UI-14](../../../reference/spec.md#UI-14).
