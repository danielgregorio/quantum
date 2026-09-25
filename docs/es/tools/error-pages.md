---
source: tools/error-pages.md
source_hash: 0611f0033fe0
---

# Páginas de error

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/tools/error-pages).
:::

Cuando una página falla mientras desarrollas (`server.debug: true`), la página
de error muestra **dónde**: el archivo `.q`, las líneas alrededor de la que
falló con esa línea marcada, el mensaje — que dice qué cambiar — y enlaces a las
reglas de la SPEC que cita el mensaje (`PARSE-2`, `ACT-9`…). El traceback de
Python también está, plegado, para cuando el problema está en Quantum mismo.

La línea es la más interna que falló:

- un error de análisis apunta a la etiqueta (`<q:sett>` en la línea 3);
- un error de ejecución apunta a la instrucción — el `q:set` dentro del `q:if`,
  no el `q:if`;
- un error dentro de un componente que llamaste apunta al **archivo de ese
  componente**, no al `<Card />` que lo llamó.

Los errores de análisis llevan la línea en todas partes, no solo en la página:
`quantum run` y los logs muestran `at line 3: <q:sett name="x" value="1"/>`.

Con `debug: false` la página dice solo que ocurrió un error — sin código, sin
detalles del mensaje. Todo en una página de error se escapa: un mensaje puede
llevar lo que envió la solicitud.

## Recargar mantiene tu sesión {#reloading-keeps-you-logged-in}
Con `debug: true` y `reload: true`, guardar un archivo reinicia el proceso del
servidor. Sin un `security.secret_key` configurado, cada proceso inventaba su
propia clave de sesión, así que cada guardado cerraba la sesión de todos. En
modo de depuración la clave ahora se guarda en `.quantum/dev-secret-key`, junto
a tu `quantum.config.yaml` (agrega `.quantum/` al git-ignore), y las sesiones
sobreviven a las recargas. En producción, define `QUANTUM_SECRET_KEY` o
`security.secret_key` — el archivo nunca se usa con `debug: false`.
