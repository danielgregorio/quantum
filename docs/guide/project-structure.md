# Project Structure

A Quantum web app is a folder. `quantum start`, run inside it, serves it.

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

Only `components/` is required. Everything on this page is checked by the
conformance tests (`ROUTE-1`, `DB-6`, `CFG-1` in `SPEC.md`).

## Pages and URLs

Each `.q` file in `components/` is served at its path:

| File | URL |
|------|-----|
| `components/index.q` | `/` |
| `components/about.q` | `/about` |
| `components/shop/index.q` | `/shop` |
| `components/shop/[id].q` | `/shop/<anything>` |

A `[name]` segment matches any value and hands it to the page as the parameter
`name`:

```xml
<!-- components/shop/[id].q -->
<q:component name="product" xmlns:q="https://quantum.lang/ns">
  <q:param name="id" type="integer" />
  <q:query name="product" datasource="db">
    SELECT name, price FROM products WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>
  <h1>{product.name}</h1>
</q:component>
```

A URL with no matching file answers `404`.

## quantum.config.yaml

```yaml
server:
  port: 8080
  host: 127.0.0.1

datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

Values can come from environment variables: `password: ${DB_PASSWORD}`. See
[Installation](/guide/installation#configuration) and
[Database Queries](/guide/query).

## Migrations

```bash
quantum migrate create create_users   # writes migrations/V001_create_users.sql and .down.sql
quantum migrate up                    # applies pending migrations
quantum migrate status
quantum migrate down                  # rolls back the last one
```

Migrations are applied to the datasource declared in `quantum.config.yaml` —
the same database the pages query. With more than one datasource, choose it:
`quantum migrate --datasource db up`.

## Reusable components

A component used inside pages is a `.q` file too. Import it and use it as a tag:

```xml
<q:component name="index" xmlns:q="https://quantum.lang/ns">
  <q:import component="Card" />
  <Card title="Welcome" />
</q:component>
```

See [Components](/guide/components).

## Next steps

- [Quick Start](/guide/quick-start) — a page with a database and a form
- [Actions & Forms](/guide/actions)
