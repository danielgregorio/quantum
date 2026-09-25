---
source: guide/project-structure.md
source_hash: 47f6949064e6
---
# Estrutura do projeto

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/project-structure). O código é o mesmo do original.
:::

Uma aplicação web Quantum é uma pasta. O `quantum start`, rodado dentro dela,
a serve.

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

Só `components/` é obrigatória. As regras são
[ROUTE-1](../../reference/spec#ROUTE-1), [DB-6](../../reference/spec#DB-6) e
[CFG-1](../../reference/spec#CFG-1); a página abaixo é servida no CI
(`tests/docs/test_guide_project_structure.py`).

## Páginas e URLs {#pages-and-urls}

Cada arquivo `.q` em `components/` é servido no seu caminho:

| Arquivo | URL |
|------|-----|
| `components/index.q` | `/` |
| `components/about.q` | `/about` |
| `components/shop/index.q` | `/shop` |
| `components/shop/[id].q` | `/shop/<qualquer coisa>` |

Um segmento `[name]` aceita qualquer valor e o entrega à página como o
parâmetro `name`. Salve como `components/shop/[id].q`:

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

Com os produtos do [banco de exemplo](./query#the-example-database), `/shop/2`
mostra **Mouse**. Uma URL sem arquivo correspondente responde `404`.

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

Os valores podem vir de variáveis de ambiente: `password: ${DB_PASSWORD}`.
Veja [Instalação](/pt/guide/installation#configuration) e
[Consultas ao banco](/pt/guide/query).

## Migrações {#migrations}

```bash
quantum migrate create create_users   # writes migrations/V001_create_users.sql and .down.sql
quantum migrate up                    # applies pending migrations
quantum migrate status
quantum migrate down                  # rolls back the last one
```

As migrações são aplicadas à fonte de dados declarada no
`quantum.config.yaml` — o mesmo banco que as páginas consultam. Com mais de
uma fonte de dados, escolha: `quantum migrate --datasource db up`.

### Ou: escreva o esquema e deixe o Quantum escrever a migração {#or-write-the-schema-let-quantum-write-the-migration}

Mantenha um `schema.sql` com as tabelas **como devem ser**, e deixe o
`quantum migrate plan` descobrir a migração:

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

- Ele compara o `schema.sql` com o esquema **que as migrações produzem**
  (construído em memória), não com o seu banco local — a mesma resposta em
  qualquer máquina.
- Uma coluna nova que aceita nulo (ou que tem um padrão) é `ADD COLUMN`;
  qualquer outra mudança reconstrói a tabela e copia as linhas (o SQLite não
  consegue alterar uma coluna).
- Apagar uma tabela ou uma coluna, ou mudar o tipo de uma coluna, perde
  dados: o plano diz isso e o `--write` o recusa sem `--allow-data-loss`. Uma
  coluna nova `NOT NULL` sem padrão é sinalizada: as linhas que já existem não
  têm valor.
- O rollback é escrito ao lado. Antes de escrever, o plano é conferido:
  aplicado ao esquema das migrações, ele precisa dar exatamente o do
  `schema.sql`.
- Por enquanto, só SQLite. O `projects/tarefas` mantém um `schema.sql`.

## Componentes reutilizáveis {#reusable-components}

Um componente usado dentro de páginas também é um arquivo `.q`: uma página o
importa com `q:import` e o usa como uma tag. Um arquivo ou pasta cujo nome
começa com `_` (`components/_parts/Card.q`) nunca é servido como página
(ROUTE-3). O exemplo em [Componentes](/pt/guide/components) roda no CI.

## Próximos passos {#next-steps}

- [Início rápido](/pt/guide/quick-start) — uma página com um banco de dados e um formulário
- [Ações e formulários](/pt/guide/actions)
