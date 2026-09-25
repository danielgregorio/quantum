---
source: tools/cli.md
source_hash: 12afaadf1bf6
---

# Comandos de la CLI

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/tools/cli).
:::

`pip install quantum-framework` instala el comando `quantum`.

```bash
quantum <command>
python -m quantum.cli.runner <command>   # the same, without the script on PATH
```

Todos los comandos aceptan `-h` / `--help`. Esta página trata de los del día a
día; la [referencia de la línea de comandos](/reference/cli), generada a partir
del código, lista todos los comandos y opciones.

## Resumen de comandos {#commands-overview}
| Comando | Descripción |
|---------|-------------|
| `run` | Ejecuta un archivo `.q` |
| `start` | Sirve las páginas de la aplicación |
| `stop` | Detiene el servidor que inició `quantum start` |
| `console` | Las páginas de la aplicación en la terminal |
| `desktop` | Las páginas de la aplicación en una ventana de escritorio |
| `check` | Las páginas se analizan, el SQL compila, los campos de las consultas existen |
| `test` | Ejecuta las pruebas `*.test.q` de la aplicación |
| `migrate` | Aplica, revierte y planifica migraciones de la base de datos |

## quantum run {#quantum-run}
Ejecuta un archivo de Quantum (`.q`).

```bash
quantum run <file.q> [options]
```

| Opción | Descripción | Valor por defecto |
|--------|-------------|---------|
| `--debug` | Muestra lo que se analiza y se ejecuta | desactivado |
| `--config` | Ruta del archivo de configuración | `quantum.config.yaml` |
| `--target` | Compilación de UI independiente (`type="ui"`): `html`, `textual` (solo diseño), `mobile` (Laboratorio) | `html` |

```bash
$ quantum run hello.q
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!

$ quantum run hello.q --debug
[DEBUG] Parsing file: hello.q
[DEBUG] AST generated: ComponentNode
[DEBUG] Validating AST...
[EXEC] Executing component: HelloWorld
   Type: pure
   Params: 0
   Returns: 1
[SUCCESS] Result: Hello World!
```

Lo que hace `run` depende del archivo:

| Archivo | Comportamiento |
|------|----------|
| `q:component` | Lo ejecuta y muestra el resultado |
| `q:application type="ui"` | Compila la UI independiente (Experimental) |
| `q:application type="terminal"` | Compila la aplicación de terminal (Experimental) |
| `q:application type="game"` | Compila el juego (Laboratorio) |
| `q:job` | Ejecuta la tarea (Experimental) |

Una aplicación web no es una `q:application`: son páginas en `components/`,
servidas por `quantum start` (APP-1).

Un archivo que no existe, no se analiza o falla termina con `1`.

## quantum start {#quantum-start}
Sirve las páginas de `components/` en el puerto definido en
`quantum.config.yaml` (8080 por defecto).

```bash
quantum start                  # in the application's folder
quantum start --port 3000
quantum start --hot-reload     # reload the open pages on every save
```

El modo de depuración — el [panel /_dev](/es/tools/dev-panel) y las
[páginas de error](/es/tools/error-pages) detalladas — es `server.debug: true` en
`quantum.config.yaml`. La opción `--debug` solo muestra el traceback cuando el
servidor no logra iniciar. Consulta también [Hot Reload](/es/tools/hot-reload).

## quantum stop {#quantum-stop}
Detiene el servidor que `quantum start` inició desde esta carpeta (registra su
proceso en `.quantum.pid`). Un proceso del que no puede estar seguro que sea ese
servidor no se termina: el comando lo dice y termina con `1` (RUN-3).

## quantum console {#quantum-console}
Las mismas páginas en la terminal:

```bash
quantum console              # the home page
quantum console /reports     # another page
quantum console --config other.config.yaml
```

## quantum desktop {#quantum-desktop}
Las mismas páginas en una ventana de escritorio ([Escritorio](/es/targets/desktop)):

```bash
quantum desktop
quantum desktop /reports --width 800 --height 600
```

## quantum check {#quantum-check}
Analiza todas las páginas y compila todas las consultas contra la base de datos,
sin ejecutarlas ([quantum check](/es/tools/check)):

```bash
quantum check
quantum check --config other.config.yaml
```

## quantum test {#quantum-test}
Ejecuta los archivos `*.test.q` de la aplicación ([Testing an App](/es/guide/testing)):

```bash
quantum test                   # every *.test.q under the current folder
quantum test tests/            # a folder, or files
```

Termina con `1` cuando una prueba falla, así que encaja en CI.

## quantum migrate {#quantum-migrate}
Migraciones de la base de datos en `migrations/` ([Database Queries](/es/guide/query)):

```bash
quantum migrate status
quantum migrate up
quantum migrate down           # the last one
quantum migrate create add_due_date
quantum migrate plan           # compare schema.sql with the migrations
```

## Otros comandos {#other-commands}
`quantum admin` inicia el [Quantum Admin](/guide/admin). `quantum jobs` y
`quantum mq` pertenecen a las tareas y la mensajería, que son Experimentales (ver
[Estabilidad](/es/stability/)). `quantum pkg` empaqueta e instala carpetas de
componentes, pero una página todavía no puede importar un componente de un
paquete instalado: `q:import from=` es una carpeta dentro de `paths.components`.
Sus opciones están en la [referencia de la línea de comandos](/reference/cli).

## Relacionado {#related}
- [Hot Reload](/es/tools/hot-reload) - `quantum start --hot-reload`
- [Extensión de VS Code](/es/tools/vscode-extension) - Soporte en el editor
- [Estructura del proyecto](/guide/project-structure) - Organización de los archivos
