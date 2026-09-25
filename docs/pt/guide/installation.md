---
source: guide/installation.md
source_hash: aac979eb127d
---

# Instalação

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/installation).
:::

## Requisitos

- **Python 3.12+**
- **pip**

## Instalar

```bash
pip install quantum-framework
```

Isso instala o comando `quantum` e o pacote Python `quantum`. Confira:

```bash
quantum --version
```

```
quantum 1.0.0
```

::: tip Use um ambiente virtual
`python -m venv .venv`, depois ative (`source .venv/bin/activate`, ou
`.venv\Scripts\activate` no Windows) antes do `pip install`.
:::

### Extras opcionais

A instalação básica cobre componentes, o servidor web, consultas SQLite e o
alvo de terminal. Todo o resto é um extra:

| Extra | Instalação | Acrescenta |
|-------|---------|------|
| `db` | `pip install "quantum-framework[db]"` | Drivers PostgreSQL e MySQL para `q:query` |
| `rag` | `pip install "quantum-framework[rag]"` | Banco vetorial para `q:knowledge` / consultas RAG |
| `jobs` | `pip install "quantum-framework[jobs]"` | O agendador por trás de `q:schedule` |
| `websocket` | `pip install "quantum-framework[websocket]"` | O transporte por trás de `q:websocket` |

Os extras se combinam: `pip install "quantum-framework[db,jobs]"`.

O alvo **desktop** também precisa de `pip install pywebview` (no Linux, o
pywebview tem dependências de sistema próprias — veja a documentação dele).

As tags de IA (`q:llm`, `q:knowledge`, `q:agent`) conversam com um servidor
[Ollama](https://ollama.com) — `http://localhost:11434`, a menos que
`QUANTUM_LLM_BASE_URL` diga outra coisa.

Veja [SUPPORT_TIERS.md](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md)
ou [Estabilidade](/pt/stability/) para saber quais deles são estáveis e quais
são experimentais.

## Verificar

Crie `hello.q`:

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World!" />
</q:component>
```

**Saída:** `Hello World!`

```bash
quantum run hello.q
```

```
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!
```

### Servidor web

Coloque os componentes numa pasta `components/` e inicie o servidor a partir
da pasta que a contém:

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

`components/orders.q` é servido em `/orders`, e assim por diante.

## Configuração

As configurações ficam em `quantum.config.yaml`, ao lado de `components/`.
Fontes de dados para `q:query`:

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

Mantenha segredos fora do arquivo referenciando variáveis de ambiente.
`${NAME:-default}` usa um valor padrão quando a variável falta, e `$$` é um
`$` literal:

```yaml
datasources:
  db:
    driver: postgres
    host: ${DB_HOST:-localhost}
    database: app
    username: app
    password: ${DB_PASSWORD}
```

Se `DB_PASSWORD` não estiver definida, Quantum se recusa a iniciar e diz qual
variável e qual configuração.

## A partir do código-fonte

Para trabalhar no próprio Quantum:

```bash
git clone https://github.com/danielgregorio/quantum.git
cd quantum
pip install -e ".[dev,db,jobs,websocket]" -r quantum_admin/backend/requirements.txt
pytest
```

O site da documentação é gerado a partir da raiz do repositório:

```bash
npm ci
npm run docs:dev
```

[CONTRIBUTING.md](https://github.com/danielgregorio/quantum/blob/main/CONTRIBUTING.md)
explica a arquitetura e como acrescentar uma tag.

## Solução de problemas

**`quantum: command not found`** — o ambiente em que você rodou o
`pip install` não está ativo, ou a pasta `Scripts`/`bin` dele não está no
`PATH`. `python -m quantum.cli.runner --version` funciona nos dois casos.

**Erros de parse do XML** — um arquivo `.q` é XML: toda tag fecha, os
atributos ficam entre aspas, e `<`, `>`, `&` no texto se escrevem `&lt;`,
`&gt;`, `&amp;`. O erro diz a linha e a coluna.

**`Port 8080 already in use`** — outro servidor está rodando. Use
`quantum stop`, ou `quantum start --port <outra>`.

**`Not stopping PID …`** — o `quantum stop` encontrou um `.quantum.pid` cujo
processo não é o servidor que o escreveu (o servidor terminou sem limpar, e o
número agora pertence a outro programa). Ele não mata nada e apaga o arquivo
velho; se um servidor Quantum ainda estiver rodando, pare-o à mão.

## Próximos passos

- [Início rápido](/pt/guide/quick-start) — construa sua primeira aplicação
- [Componentes](/guide/components) — o sistema de componentes (em inglês)
- [Ajuda e issues](https://github.com/danielgregorio/quantum/issues)
