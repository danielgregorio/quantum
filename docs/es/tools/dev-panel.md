---
source: tools/dev-panel.md
source_hash: aba77ca68e49
---

# El panel `/_dev`

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/tools/dev-panel).
:::

Mientras escribes una aplicación, `/_dev` muestra lo que hicieron las últimas
solicitudes: qué componente respondió, qué `q:action` se ejecutó, cada consulta
con sus parámetros, tiempo y filas, las variables con las que terminó cada
ámbito, la redirección y el mensaje flash.

Actívalo en `quantum.config.yaml`:

```yaml
server:
  debug: true
  host: 127.0.0.1
```

`quantum start` muestra la dirección (`Dev panel: http://localhost:8080/_dev`).
Usa la aplicación y luego abre `/_dev`: se muestra la solicitud más reciente, y
cada fila de la lista abre su propia solicitud (`/_dev/12`).

| Sección | Qué muestra |
|---|---|
| Component, Action | el archivo `.q` que respondió y la acción que ejecutó un POST |
| Redirect, Flash | a dónde envió una acción al navegador, y el mensaje para la página siguiente |
| Queries | fuente de datos, SQL, parámetros, filas (o el error de la base), tiempo |
| action / page | las variables con las que terminó la acción o la página |
| session / application | los ámbitos tal como quedaron al final de la solicitud |

Un valor de más de 300 caracteres se recorta. Todo se escapa: una variable que
contiene HTML se muestra como texto.

## Solo existe mientras desarrollas {#it-exists-only-while-developing}
- Con `debug: false` no se registra nada y `/_dev` es un 404.
- Solo responde a solicitudes de la propia máquina (`127.0.0.1` / `::1`): el
  panel muestra sesiones y parámetros de consultas, así que desde cualquier otra
  dirección no existe — aunque la configuración diga `debug: true` detrás de un
  bind público.
- Guarda las últimas 30 solicitudes del proceso del servidor, en memoria.
