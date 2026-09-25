---
order: 1
title: "Correo en desarrollo"
description: "\"Enviar correo desde una acción sin servidor de correo mientras desarrollas — host: log escribe cada mensaje en el log.\""
source: cookbook/files-and-mail/mail-in-development.md
source_hash: 6103acae1466
---

# Correo en desarrollo

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/files-and-mail/mail-in-development).
:::

**Tarea:** un formulario de contacto que envía un correo al equipo de soporte
— y que puedes desarrollar y probar sin un servidor de correo.

Con `host: log`, `q:mail` escribe cada mensaje en el log en lugar de
enviarlo. La configuración lee el host del entorno, así que en producción
solo se define `SMTP_HOST`:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/components/index.q{xml}

Las pruebas envían el formulario y verifican lo que se le dice al visitante,
y que una dirección mala se rechaza en su campo antes de enviar nada:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/tests/contact.test.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/output/test-report.txt{text}

Y este es el mensaje que la primera prueba "envió" — lo que escribió
`host: log`:

<<< @/../examples/cookbook/files-and-mail/mail-in-development/output/mail.txt{text}

Sin una sección `mail:`, `q:mail` es un error que lo dice — nunca finge que
envía. Más en [Files & Mail](../../../guide/files-and-mail.md) (en inglés).

*Probado:* esta página importa los archivos de
`examples/cookbook/files-and-mail/mail-in-development/`, y los resultados de
arriba vienen de ejecutarlos.
