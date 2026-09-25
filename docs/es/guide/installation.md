---
source: guide/installation.md
source_hash: aac979eb127d
---

# Instalación

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/installation).
:::

## Requisitos

- **Python 3.12+**
- **pip**

## Instalar

```bash
pip install quantum-framework
```

Esto instala el comando `quantum` y el paquete de Python `quantum`. Verifícalo:

```bash
quantum --version
```

```
quantum 1.0.0
```

::: tip Usa un entorno virtual
`python -m venv .venv`, y luego actívalo (`source .venv/bin/activate`, o
`.venv\Scripts\activate` en Windows) antes de `pip install`.
:::

### Extras opcionales

La instalación base cubre los componentes, el servidor web, las consultas a
SQLite y el destino de terminal. Todo lo demás es un extra:

| Extra | Instalación | Agrega |
|-------|---------|------|
| `db` | `pip install "quantum-framework[db]"` | Drivers de PostgreSQL y MySQL para `q:query` |
| `rag` | `pip install "quantum-framework[rag]"` | Almacén vectorial para `q:knowledge` / consultas RAG |
| `jobs` | `pip install "quantum-framework[jobs]"` | Planificador detrás de `q:schedule` |
| `websocket` | `pip install "quantum-framework[websocket]"` | Transporte detrás de `q:websocket` |

Los extras se combinan: `pip install "quantum-framework[db,jobs]"`.

El destino de **escritorio** también necesita `pip install pywebview` (en
Linux, pywebview tiene dependencias propias del sistema; consulta su
documentación).

Las etiquetas de IA (`q:llm`, `q:knowledge`, `q:agent`) hablan con un servidor
[Ollama](https://ollama.com): `http://localhost:11434`, salvo que
`QUANTUM_LLM_BASE_URL` diga otra cosa.

Consulta [SUPPORT_TIERS.md](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md)
o [Estabilidad](/es/stability/) para saber cuáles son estables y cuáles son
experimentales.

## Verificar

Crea `hello.q`:

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World!" />
</q:component>
```

**Output:** `Hello World!`

```bash
quantum run hello.q
```

```
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!
```

### Servidor web

Pon los componentes en una carpeta `components/` e inicia el servidor desde la
carpeta que la contiene:

```
myapp/
└── components/
    └── index.q      # served at /
```

```bash
quantum start               # http://localhost:8080
quantum start --port 9000   # another port
quantum stop                # stops the server started above
```

`components/orders.q` se sirve en `/orders`, y así sucesivamente.

## Configuración

La configuración vive en `quantum.config.yaml`, junto a `components/`. Las
fuentes de datos para `q:query`:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

Deja los secretos fuera del archivo haciendo referencia a variables de
entorno. `${NAME:-default}` usa un valor por defecto, y `$$` es un `$` literal:

```yaml
datasources:
  db:
    driver: postgres
    host: ${DB_HOST:-localhost}
    database: app
    username: app
    password: ${DB_PASSWORD}
```

Si `DB_PASSWORD` no está definida, Quantum se niega a iniciar y dice qué
variable y qué configuración.

## Desde el código fuente

Para trabajar en Quantum mismo:

```bash
git clone https://github.com/danielgregorio/quantum.git
cd quantum
pip install -e ".[dev,db,jobs,websocket]" -r quantum_admin/backend/requirements.txt
pytest
```

El sitio de documentación se construye desde la raíz del repositorio:

```bash
npm ci
npm run docs:dev
```

[CONTRIBUTING.md](https://github.com/danielgregorio/quantum/blob/main/CONTRIBUTING.md)
explica la arquitectura y cómo agregar una etiqueta.

## Solución de problemas

**`quantum: command not found`**: el entorno donde ejecutaste `pip install` no
está activo, o su carpeta `Scripts`/`bin` no está en el `PATH`.
`python -m quantum.cli.runner --version` funciona en cualquier caso.

**Errores de análisis XML**: un archivo `.q` es XML: toda etiqueta se cierra,
los atributos van entre comillas, y `<`, `>`, `&` en el texto se escriben
`&lt;`, `&gt;`, `&amp;`. El error indica la línea y la columna.

**`Port 8080 already in use`**: hay otro servidor en ejecución. Usa
`quantum stop`, o `quantum start --port <otro>`.

**`Not stopping PID …`**: `quantum stop` encontró un `.quantum.pid` cuyo
proceso no es el servidor que lo escribió (el servidor terminó sin limpiar, y
su número ahora pertenece a otro programa). No mata nada y elimina el archivo
viejo; si un servidor de Quantum sigue en ejecución, detenlo a mano.

## Próximos pasos

- [Inicio rápido](/es/guide/quick-start): construye tu primera aplicación
- [Componentes](/guide/components): el sistema de componentes (en inglés)
- [Ayuda e issues](https://github.com/danielgregorio/quantum/issues)
