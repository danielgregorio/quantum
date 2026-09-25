---
source: tools/hot-reload.md
source_hash: df2a54054261
---

# Hot Reload

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/tools/hot-reload).
:::

Mientras escribes una aplicación, `quantum start --hot-reload` recarga las
páginas abiertas en el navegador cada vez que guardas un componente o un archivo
estático. No reinicias el servidor ni presionas F5.

```bash
quantum start --hot-reload
```

El servidor muestra su dirección como siempre. Abre una página, edita un archivo
`.q` en `components/`, guarda, y la página muestra el cambio.

## Qué pasa con un cambio {#what-happens-on-a-change}
El servidor observa dos carpetas de `quantum.config.yaml`: `paths.components` y
`paths.static`. Cada página que sirve abre un WebSocket hacia el observador.

| Guardas | Las páginas abiertas |
|---|---|
| Un archivo `.q`, `.html`, `.js`, `.yaml` o `.yml` | Se recargan. Lo que se escribió en sus formularios se conserva |
| Solo archivos `.css` | Vuelven a pedir las hojas de estilo, sin recargar |
| Un archivo `.q` que ya no se analiza | No se recargan. Muestran el archivo y el error de análisis sobre la página hasta que lo corrijas |

Los cambios se agrupan: guardar varios archivos a la vez da una sola recarga.

Las páginas se vuelven a leer después de un cambio, incluso con
`performance.cache_templates` activado. El código Python (servicios,
`q:python`) no se recarga: para eso, define `server.reload: true`, que reinicia
el servidor cuando cambia un archivo `.py`.

## Opciones {#options}
| Opción | Significado |
|---|---|
| `--hot-reload` | Observa el proyecto y recarga las páginas abiertas |
| `--hot-reload-port N` | Puerto del WebSocket al que se conectan las páginas. Por defecto `35729` |

Sin `--hot-reload`, no se observa nada y no se agrega nada a las páginas. El hot
reload es para tu máquina: las páginas se conectan a `localhost`.

## Solución de problemas {#troubleshooting}
**La página no se recarga.** Abre la consola del navegador: el cliente registra
`[Hot Reload] Connected to dev server` cuando se conecta. Si sigue intentando
reconectarse, otro programa puede estar usando el puerto 35729. Inicia con
`--hot-reload-port` y un puerto libre.

**Un cambio no se detecta.** Solo se observan los archivos en
`paths.components` y `paths.static`. Revisa esas rutas en `quantum.config.yaml`.

La regla detrás de esta página es la DEV-4 de la especificación.

## Relacionado {#related}
- [Comandos de la CLI](/es/tools/cli) - `quantum start` y los otros comandos
- [Panel de desarrollo](/es/tools/dev-panel) - Qué hizo cada solicitud (`server.debug: true`)
- [Estructura del proyecto](/guide/project-structure) - Dónde viven los componentes y los archivos estáticos
