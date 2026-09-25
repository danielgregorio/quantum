---
order: 2
title: "Datos de prueba con test:given"
description: "Poner las filas que una prueba necesita en su base de datos nueva con test:given, e iniciar la sesión de un usuario con test:as."
source: cookbook/testing/test-data.md
source_hash: 96b9d6f6e931
---

# Datos de prueba con `test:given`

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/testing/test-data).
:::

**Tarea:** probar una página que depende de los datos y de quién la mira — sin
un archivo de fixtures y sin una contraseña.

La página lista las tareas abiertas del usuario que inició sesión:

<<< @/../examples/cookbook/testing/test-data/quantum.config.yaml{yaml}

<<< @/../examples/cookbook/testing/test-data/migrations/V001_tasks.sql{sql}

<<< @/../examples/cookbook/testing/test-data/components/index.q{xml}

Cada prueba empieza con una base de datos vacía construida por `migrations/`.
`test:given` inserta las filas que la prueba necesita — a través de las reglas
del esquema, así que una fila que la aplicación nunca podría haber escrito (un
`done` fuera del `CHECK (… IN …)`, una columna obligatoria que no puede
completar) hace fallar el paso en lugar de colarse. `test:as` inicia la sesión
de un usuario como lo hace un login:

<<< @/../examples/cookbook/testing/test-data/tests/tasks.test.q{xml}

<<< @/../examples/cookbook/testing/test-data/output/test-report.txt{text}

`no-text` verifica lo que *no* debe estar en la página — aquí, la tarea de otro
usuario y una terminada. Todo el vocabulario está en la guía
[Testing an App](../../../guide/testing.md) (en inglés).

*Probado:* esta página importa los archivos de `examples/cookbook/testing/test-data/`,
y el resultado de arriba es el informe de ejecutarlos.
