---
source: guide/project-structure.md
source_hash: 47f6949064e6
---

# Estructura del proyecto

::: info Traducción automática
Esta página se tradujo automáticamente del inglés y todavía no la revisó un
hablante nativo; las correcciones son bienvenidas en GitHub. Si algo no
coincide, vale el [original en inglés](/guide/project-structure).
:::

Una aplicación web Quantum es una carpeta. `quantum start`, ejecutado dentro de
ella, la sirve.

```text
my-app/
├── quantum.config.yaml     datasources and server settings
├── components/             one .q file per page (and reusable components)
│   ├── index.q             /
│   ├── about.q             /about
│   └── shop/
│       ├── index.q         /shop
│       └── [id].q          /shop/41  (id = 41)
├── static/                 served as-is under /static/
├── migrations/             V001_create_users.sql, applied by `quantum migrate up`
└── data/                   your SQLite files, CSV/JSON for q:data
```

Solo `components/` es obligatoria. Las reglas son
[ROUTE-1](/reference/spec#ROUTE-1), [DB-6](/reference/spec#DB-6) y
[CFG-1](/reference/spec#CFG-1); la página de abajo se sirve en CI
(`tests/docs/test_guide_project_structure.py`).

## Páginas y URL {#pages-and-urls}

Cada archivo `.q` en `components/` se sirve en su ruta:

| Archivo | URL |
|------|-----|
| `components/index.q` | `/` |
| `components/about.q` | `/about` |
| `components/shop/index.q` | `/shop` |
| `components/shop/[id].q` | `/shop/<anything>` |

Un segmento `[name]` coincide con cualquier valor y se lo entrega a la página
como el parámetro `name`. Guárdalo como `components/shop/[id].q`:

```xml
<q:component name="product" xmlns:q="https://quantum.lang/ns">
  <q:param name="id" type="integer" />
  <q:query name="product" datasource="db">
    SELECT name, price FROM products WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>
  <h1>{product.name}</h1>
</q:component>
```

Con los productos de [la base de datos de ejemplo](/es/guide/query#the-example-database), `/shop/2`
muestra **Mouse**. Una URL sin un archivo que coincida responde `404`.

## quantum.config.yaml {#quantum-config-yaml}

```yaml
server:
  port: 8080
  host: 127.0.0.1

datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

Los valores pueden venir de variables de entorno: `password: ${DB_PASSWORD}`.
Ver [Instalación](/es/guide/installation#configuration) y
[Consultas a la base de datos](/es/guide/query).

## Migraciones {#migrations}

```bash
quantum migrate create create_users   # writes migrations/V001_create_users.sql and .down.sql
quantum migrate up                    # applies pending migrations
quantum migrate status
quantum migrate down                  # rolls back the last one
```

Las migraciones se aplican a la fuente de datos declarada en
`quantum.config.yaml` — la misma base de datos que consultan las páginas. Con
más de una fuente de datos, elígela: `quantum migrate --datasource db up`.

### O bien: escribe el esquema y deja que Quantum escriba la migración {#or-write-the-schema-let-quantum-write-the-migration}

Mantén un `schema.sql` con las tablas **como deberían ser**, y deja que
`quantum migrate plan` calcule la migración:

```bash
quantum migrate plan                     # what changes; what loses data is marked !!
quantum migrate plan --write add_tags    # saves migrations/V00N_add_tags.sql (+ .down.sql), after asking
quantum migrate up
```

```text
Plan: schema.sql vs. the migrations in migrations/

  + add table tags
  ~ rebuild posts (+ slug; status: CHECK)
  + add index posts_slug
```

- Compara `schema.sql` con el esquema **que producen las migraciones**
  (construido en memoria), no con tu base de datos local — la misma respuesta en
  todas las computadoras.
- Una columna nueva que acepta nulos (o con un valor por defecto) es un
  `ADD COLUMN`; cualquier otro cambio reconstruye la tabla y copia las filas
  (SQLite no puede modificar una columna).
- Eliminar una tabla o una columna, o cambiar el tipo de una columna, pierde
  datos: el plan lo dice y `--write` lo rechaza sin `--allow-data-loss`. Una
  columna `NOT NULL` nueva sin valor por defecto se marca: las filas existentes
  no tienen valor.
- La reversión se escribe junto a ella. Antes de escribir, el plan se verifica:
  aplicado al esquema de las migraciones, debe dar exactamente el de `schema.sql`.
- Por ahora, solo SQLite. `projects/tarefas` mantiene un `schema.sql`.

## Componentes reutilizables {#reusable-components}

Un componente que se usa dentro de páginas también es un archivo `.q`: una
página lo importa con `q:import` y lo usa como una etiqueta. Un archivo o una
carpeta cuyo nombre empieza con `_` (`components/_parts/Card.q`) nunca se sirve
como página (ROUTE-3). El ejemplo de [Componentes](/es/guide/components) se ejecuta
en CI.

## Próximos pasos {#next-steps}

- [Inicio rápido](/es/guide/quick-start) — una página con una base de datos y un formulario
- [Acciones y formularios](/es/guide/actions)
