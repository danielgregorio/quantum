---
source: guide/admin.md
source_hash: 94cd00f82477
---

# Quantum Admin

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/admin).
:::

El admin es una aplicación Quantum que administra las aplicaciones de una
carpeta: las lista y las crea, inicia y detiene sus servidores, edita su
configuración y sus conectores, recorre sus componentes y ejecuta sus pruebas.
Sus pantallas son archivos `.q` sobre [servicios declarados](/es/guide/services).

## Instalar e iniciar {#install-and-start}

```bash
pip install "quantum-framework[admin]"
cd my-workspace
quantum admin
```

Abre `http://127.0.0.1:8090/admin` e inicia sesión como `admin`. Sin
`ADMIN_PASSWORD`, se genera una contraseña y se imprime cuando el admin
arranca; cambia en cada reinicio. Defínela para tener un inicio de sesión estable:

```bash
ADMIN_PASSWORD="a long password" quantum admin
```

El admin escucha solo en `127.0.0.1`.

## Dónde van los datos {#where-the-data-goes}

| Opción | Por defecto | Qué es |
|--------|---------|------------|
| `--data` | `./.quantum-admin` | La base de datos del admin, su configuración (conectores, configuración global, PID de los procesos), las claves de sesión y el `quantum.config.yaml` generado |
| `--root` | la carpeta actual | La carpeta respecto de la cual se toman las rutas de las aplicaciones; **Sync** registra cada carpeta dentro de `<root>/projects` |
| `--port` | `8090` | |

La configuración generada se reescribe en cada inicio; cambia las opciones, no el
archivo. Deja la carpeta de datos fuera del control de versiones: guarda secretos.

Sin el extra `[admin]`, el comando se detiene y dice qué instalar.
