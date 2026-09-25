---
order: 1
title: "Una primera prueba con quantum test"
description: "Probar una página y su acción en Quantum mismo — visitar, enviar, verificar el mensaje flash, la tabla y el error del campo."
source: cookbook/testing/first-test.md
source_hash: 0285b0b6d11f
---

# Una primera prueba con `quantum test`

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/testing/first-test).
:::

**Tarea:** verificar que una página lista lo que hay en la base de datos, que
su acción guarda una fila y lo dice, y que rechaza una entrada mala — sin
escribir Python.

Una aplicación pequeña: una tabla, una página que la lista y una acción que le
agrega filas.

<<< @/../examples/cookbook/testing/first-test/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/first-test/migrations/V001_notes.sql{sql}

<<< @/../examples/cookbook/testing/first-test/components/index.q{xml}

Las pruebas están al lado, en `tests/`. Cada `q:test` empieza con una base de
datos nueva construida a partir de `migrations/`, así que no dependen unas de
otras:

<<< @/../examples/cookbook/testing/first-test/tests/notes.test.q{xml}

Ejecútalas desde la carpeta de la aplicación:

```bash
quantum test
```

<<< @/../examples/cookbook/testing/first-test/output/test-report.txt{text}

`test:visit` abre la página; `test:submit` envía una acción con los demás
atributos como sus campos; `test:expect` verifica lo que pasó — el estado, la
redirección y el mensaje flash, un texto en la página, filas en una tabla, o
el campo en el que se rechazó una entrada. Todo el vocabulario está en la guía
[Testing an App](../../../guide/testing.md) (en inglés).

*Probado:* esta página importa los archivos de `examples/cookbook/testing/first-test/`,
y el resultado de arriba es el informe de ejecutarlos.
