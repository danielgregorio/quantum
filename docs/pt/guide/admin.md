---
source: guide/admin.md
source_hash: 94cd00f82477
---
# Quantum Admin

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/admin). O código é o mesmo do original.
:::

O admin é uma aplicação Quantum que gerencia as aplicações de uma pasta: ele
as lista e cria, inicia e para os servidores delas, edita a configuração e os
conectores delas, navega pelos componentes e roda os testes. As telas dele
são arquivos `.q` sobre [serviços declarados](/pt/guide/services).

## Instalar e iniciar {#install-and-start}

```bash
pip install "quantum-framework[admin]"
cd my-workspace
quantum admin
```

Abra `http://127.0.0.1:8090/admin` e entre como `admin`. Sem
`ADMIN_PASSWORD`, uma senha é gerada e mostrada quando o admin inicia; ela
muda a cada reinício. Defina-a para ter um login estável:

```bash
ADMIN_PASSWORD="a long password" quantum admin
```

O admin escuta só em `127.0.0.1`.

## Para onde vão os dados {#where-the-data-goes}

| Opção | Padrão | O que é |
|--------|---------|------------|
| `--data` | `./.quantum-admin` | O banco do admin, as configurações dele (conectores, configurações globais, PIDs dos processos), as chaves de sessão e o `quantum.config.yaml` gerado |
| `--root` | a pasta atual | A pasta à qual os caminhos das aplicações são relativos; o **Sync** registra cada pasta dentro de `<root>/projects` |
| `--port` | `8090` | |

A configuração gerada é reescrita a cada início; mude as opções, não o
arquivo. Mantenha a pasta de dados fora do controle de versão: ela guarda
segredos.

Sem o extra `[admin]`, o comando para e diz o que instalar.
