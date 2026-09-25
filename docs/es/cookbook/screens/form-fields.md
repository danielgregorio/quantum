---
order: 5
title: "Todos los tipos de campo"
description: "\"ui:form con etiquetas ui:formitem: texto, número, un select con opciones, un switch, radios y un campo de varias líneas.\""
source: cookbook/screens/form-fields.md
source_hash: ef4d1aa946f9
---

# Todos los tipos de campo

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/screens/form-fields).
:::

**Tarea:** un formulario que usa cada tipo de campo, con etiquetas.

<<< @/../examples/cookbook/screens/form-fields/quantum.config.yaml{yaml}

`ui:formitem label="…"` pone una etiqueta junto a su campo. `ui:select` toma
sus opciones de `ui:option`s con sus propios textos, y `ui:radio` las toma
del `enum` del `q:param` de la acción. Un `ui:switch` es una casilla
booleana, y `rows` crea un campo de varias líneas. Las reglas de cada campo
vienen de la acción ([Mostrar cada error en su campo](../forms-and-actions/field-errors.md)).

<<< @/../examples/cookbook/screens/form-fields/components/index.q{xml}

<<< @/../examples/cookbook/screens/form-fields/tests/booking.test.q{xml}

<<< @/../examples/cookbook/screens/form-fields/output/test-report.txt{text}

Ver [UI-9](../../../reference/spec.md#UI-9) y [UI-14](../../../reference/spec.md#UI-14).
