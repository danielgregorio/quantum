---
order: 6
title: "La misma página en una terminal"
description: "Una página ui:*, servida al navegador por quantum start y dibujada en una terminal por quantum console."
source: cookbook/screens/browser-and-console.md
source_hash: 0ceede109e4d
---

# La misma página en una terminal

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/cookbook/screens/browser-and-console).
:::

**Tarea:** usar la misma página desde un navegador y desde una terminal.

<<< @/../examples/cookbook/screens/browser-and-console/quantum.config.yaml{yaml}

Una página hecha con etiquetas `ui:*` del Núcleo no está atada al HTML.
`quantum start` la sirve a un navegador; `quantum console` la dibuja en la
terminal, y `quantum desktop` en una ventana local. La consola le pide al
mismo servidor el árbol de vista de la página y envía las mismas acciones:
la regla de `name`, el mensaje flash y la sesión funcionan igual, sin nada
traducido.

<<< @/../examples/cookbook/screens/browser-and-console/components/index.q{xml}

En el navegador, `quantum test`:

<<< @/../examples/cookbook/screens/browser-and-console/tests/guests.test.q{xml}

<<< @/../examples/cookbook/screens/browser-and-console/output/test-report.txt{text}

En la consola,
[`tests/docs/test_cookbook_console.py`](https://github.com/danielgregorio/quantum/blob/main/tests/docs/test_cookbook_console.py) abre la misma
aplicación en el renderizador de consola. Verifica que cada texto que esta
suite espera en una visita simple esté en la pantalla de la consola; después
escribe un nombre demasiado corto y uno correcto, y presiona **Sign**: la
consola muestra el error del campo, luego el mensaje flash y el nombre nuevo.

```bash
quantum start      # http://localhost:8080
quantum console    # the same page in this terminal
```

Ver [UI-3](../../../reference/spec.md#UI-3) y [UI-7](../../../reference/spec.md#UI-7).
