---
order: 2
title: "Cuando el servidor de correo dice que no"
description: "Conservar un pedido aunque no se pueda enviar su correo de confirmación — onerror=continue, y avisarle al visitante."
source: cookbook/files-and-mail/mail-server-refuses.md
source_hash: 9ffe0f1d6c0a
---

# Cuando el servidor de correo dice que no

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/files-and-mail/mail-server-refuses).
:::

**Tarea:** un pedido debe guardarse aunque no se pueda enviar el correo de
confirmación — y el visitante debe enterarse, no recibir una página de error.

Por defecto, un `q:mail` que el servidor no acepta detiene la acción con el
motivo del servidor. `onerror="continue"` deja que la acción siga y pone el
resultado en `<name>_result`: `success`, y `error.message` cuando falló.

Esta receta apunta a un servidor de correo que no existe, así que todos los
mensajes fallan — como pasa cuando el servidor real está caído:

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/migrations/V001_orders.sql{sql}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/components/index.q{xml}

El pedido se inserta antes del correo, y el mensaje flash dice cómo salió.
La prueba verifica las dos cosas — la fila está ahí, y se le avisó al
visitante:

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/tests/order.test.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/output/test-report.txt{text}

En desarrollo, [`host: log`](./mail-in-development.md) evita el fallo por
completo; `onerror="continue"` es para el día en que el servidor real está
caído. Más en [Files & Mail](../../../guide/files-and-mail.md) (en inglés).

*Probado:* esta página importa los archivos de
`examples/cookbook/files-and-mail/mail-server-refuses/`, y el resultado de
arriba viene de ejecutarlos.
