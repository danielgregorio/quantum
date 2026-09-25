---
source: tools/cli.md
source_hash: 12afaadf1bf6
---

# Comandos da CLI

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/tools/cli).
:::

`pip install quantum-framework` instala o comando `quantum`.

```bash
quantum <command>
python -m quantum.cli.runner <command>   # the same, without the script on PATH
```

Todo comando aceita `-h` / `--help`. Esta página trata dos comandos do dia a dia;
a [referência da linha de comando](/reference/cli), gerada a partir do código,
lista todos os comandos e opções.

## Visão geral dos comandos {#commands-overview}
| Comando | Descrição |
|---------|-------------|
| `run` | Executa um arquivo `.q` |
| `start` | Serve as páginas da aplicação |
| `stop` | Para o servidor que o `quantum start` iniciou |
| `console` | As páginas da aplicação no terminal |
| `desktop` | As páginas da aplicação numa janela de desktop |
| `check` | As páginas são analisadas, o SQL compila, os campos das consultas existem |
| `test` | Executa os testes `*.test.q` da aplicação |
| `migrate` | Aplica, desfaz e planeja migrações do banco de dados |

## quantum run {#quantum-run}
Executa um arquivo Quantum (`.q`).

```bash
quantum run <file.q> [options]
```

| Opção | Descrição | Padrão |
|--------|-------------|---------|
| `--debug` | Mostra o que é analisado e executado | desligado |
| `--config` | Caminho do arquivo de configuração | `quantum.config.yaml` |
| `--target` | Build de UI independente (`type="ui"`): `html`, `textual` (só o layout), `mobile` (Laboratório) | `html` |

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

O que o `run` faz depende do arquivo:

| Arquivo | Comportamento |
|------|----------|
| `q:component` | Executa e mostra o resultado |
| `q:application type="ui"` | Gera a UI independente (Experimental) |
| `q:application type="terminal"` | Gera a aplicação de terminal (Experimental) |
| `q:application type="game"` | Gera o jogo (Laboratório) |
| `q:job` | Executa o job (Experimental) |

Uma aplicação web não é uma `q:application`: são páginas em `components/`,
servidas pelo `quantum start` (APP-1).

Um arquivo que não existe, não é analisado ou falha termina com `1`.

## quantum start {#quantum-start}
Serve as páginas de `components/` na porta definida em `quantum.config.yaml`
(8080 por padrão).

```bash
quantum start                  # in the application's folder
quantum start --port 3000
quantum start --hot-reload     # reload the open pages on every save
```

O modo de depuração — o [painel /_dev](/pt/tools/dev-panel) e as
[páginas de erro](/pt/tools/error-pages) detalhadas — é `server.debug: true` no
`quantum.config.yaml`. A flag `--debug` só mostra o traceback quando o servidor
não consegue iniciar. Veja também [Hot Reload](/pt/tools/hot-reload).

## quantum stop {#quantum-stop}
Para o servidor que o `quantum start` iniciou a partir desta pasta (ele registra
o processo em `.quantum.pid`). Um processo que ele não tem certeza de ser esse
servidor não é encerrado: o comando avisa e termina com `1` (RUN-3).

## quantum console {#quantum-console}
As mesmas páginas no terminal:

```bash
quantum console              # the home page
quantum console /reports     # another page
quantum console --config other.config.yaml
```

## quantum desktop {#quantum-desktop}
As mesmas páginas numa janela de desktop ([Desktop](/pt/targets/desktop)):

```bash
quantum desktop
quantum desktop /reports --width 800 --height 600
```

## quantum check {#quantum-check}
Analisa todas as páginas e compila todas as consultas contra o banco de dados,
sem executá-las ([quantum check](/pt/tools/check)):

```bash
quantum check
quantum check --config other.config.yaml
```

## quantum test {#quantum-test}
Executa os arquivos `*.test.q` da aplicação ([Testando uma aplicação](/pt/guide/testing)):

```bash
quantum test                   # every *.test.q under the current folder
quantum test tests/            # a folder, or files
```

Termina com `1` quando um teste falha, então cabe no CI.

## quantum migrate {#quantum-migrate}
Migrações do banco de dados em `migrations/` ([Consultas ao banco de dados](/pt/guide/query)):

```bash
quantum migrate status
quantum migrate up
quantum migrate down           # the last one
quantum migrate create add_due_date
quantum migrate plan           # compare schema.sql with the migrations
```

## Outros comandos {#other-commands}
`quantum admin` inicia o [Quantum Admin](/pt/guide/admin). `quantum jobs` e
`quantum mq` pertencem a jobs e mensageria, que são Experimentais (veja
[Estabilidade](/pt/stability/)). `quantum pkg` empacota e instala pastas de
componentes, mas uma página ainda não consegue importar um componente de um
pacote instalado: `q:import from=` é uma pasta dentro de `paths.components`. As
opções deles estão na [referência da linha de comando](/reference/cli).

## Relacionados {#related}
- [Hot Reload](/pt/tools/hot-reload) - `quantum start --hot-reload`
- [Extensão do VS Code](/pt/tools/vscode-extension) - Suporte no editor
- [Estrutura do projeto](/pt/guide/project-structure) - Organização dos arquivos
