---
order: 7
title: "Leer la query string"
description: "query.name lee ?name= de la dirección; default cubre el que falta; urlencode arma un enlace."
source: cookbook/basics/query-string.md
source_hash: 04f0affeada2
---

# Leer la query string

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/basics/query-string).
:::

**Tarea:** filtrar y ordenar una lista a partir de valores en la dirección.

<<< @/../examples/cookbook/basics/query-string/quantum.config.yaml{yaml}

`query.q` es el valor de `?q=` en la dirección, y está vacío cuando la
dirección no lo tiene, así que `default` le da un valor. Un formulario GET
completa la dirección por ti. `urlencode()` hace que un valor escrito sea
seguro dentro de un enlace.

<<< @/../examples/cookbook/basics/query-string/components/index.q{xml}

<<< @/../examples/cookbook/basics/query-string/tests/search.test.q{xml}

<<< @/../examples/cookbook/basics/query-string/output/test-report.txt{text}

Ver [SET-1](../../../reference/spec.md#SET-1) y [EXPR-12](../../../reference/spec.md#EXPR-12).
