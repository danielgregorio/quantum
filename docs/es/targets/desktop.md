---
source: targets/desktop.md
source_hash: 27a8d69fc37c
---

# Escritorio (`quantum desktop`)

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/targets/desktop).
:::

`quantum desktop` abre tu aplicación en una ventana nativa. Inicia el servidor
de la aplicación en un puerto local libre (`127.0.0.1`) y abre sobre él una
ventana de [pywebview](https://pywebview.flowrl.com/): la ventana es un
navegador sin el marco del navegador, así que las páginas, las `q:action`, las
sesiones y el diseño adaptable son exactamente los de la web. Cerrar la ventana
detiene el servidor.

```bash
pip install "quantum-framework[desktop]"

quantum desktop                      # the home page
quantum desktop /reports             # another page
quantum desktop --width 800 --height 600
quantum desktop --config other.config.yaml
```

Sin el extra `[desktop]`, el comando dice qué instalar en lugar de fallar con un
error de importación.

El título de la ventana sigue a la página: el `title` de la primera `ui:window`,
si no el nombre del componente — el mismo título que muestran la pestaña del
navegador y `quantum console`.

Notas por plataforma (de pywebview):

- **Windows**: usa Edge WebView2, que ya viene en Windows 10/11.
- **macOS**: usa WebKit, no hay nada que instalar.
- **Linux**: necesita GTK/WebKit, por ejemplo `sudo apt install python3-gi gir1.2-webkit2-4.1`.

## Escribe páginas, no una aplicación de escritorio {#write-pages-not-a-desktop-app}
No existe una "versión de escritorio" separada de una pantalla. Escribe la
página una vez, con elementos `ui:*` — ver [One App, Many Screens](/es/guide/ui) —
y ábrela con `quantum start`, `quantum console` o `quantum desktop`.

## Qué pasó con `--target desktop` {#what-happened-to-target-desktop}
Hasta la 0.15, `quantum run app.q --target desktop` generaba un archivo Python
con un puente JavaScript que traducía `q:set` y `q:function` a su propio estado
reactivo. Era una segunda implementación del lenguaje, y no coincidía con la
primera. Se eliminó en la 0.16 (SPEC `UI-8`); compilar con él es un error que
apunta a `quantum desktop`.
