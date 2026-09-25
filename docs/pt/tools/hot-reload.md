---
source: tools/hot-reload.md
source_hash: df2a54054261
---

# Hot Reload

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/tools/hot-reload).
:::

Enquanto você escreve uma aplicação, o `quantum start --hot-reload` recarrega as
páginas abertas no navegador sempre que você salva um componente ou um arquivo
estático. Você não reinicia o servidor nem aperta F5.

```bash
quantum start --hot-reload
```

O servidor mostra o seu endereço como de costume. Abra uma página, edite um
arquivo `.q` em `components/`, salve, e a página mostra a mudança.

## O que acontece numa mudança {#what-happens-on-a-change}
O servidor observa duas pastas do `quantum.config.yaml`: `paths.components` e
`paths.static`. Cada página que ele serve abre um WebSocket para o observador.

| Você salva | As páginas abertas |
|---|---|
| Um arquivo `.q`, `.html`, `.js`, `.yaml` ou `.yml` | Recarregam. O que foi digitado nos formulários é mantido |
| Só arquivos `.css` | Buscam as folhas de estilo de novo, sem recarregar |
| Um arquivo `.q` que não passa mais pelo parser | Não recarregam. Mostram o arquivo e o erro do parser por cima da página até você corrigir |

As mudanças são agrupadas: salvar vários arquivos de uma vez dá uma recarga.

As páginas são lidas de novo depois de uma mudança, mesmo com
`performance.cache_templates` ligado. Código Python (serviços, `q:python`) não é
recarregado: para isso, defina `server.reload: true`, que reinicia o servidor
quando um arquivo `.py` muda.

## Opções {#options}
| Flag | Significado |
|---|---|
| `--hot-reload` | Observa o projeto e recarrega as páginas abertas |
| `--hot-reload-port N` | Porta do WebSocket a que as páginas se conectam. Padrão `35729` |

Sem `--hot-reload`, nada é observado e nada é acrescentado às páginas. O hot
reload é para a sua máquina: as páginas se conectam a `localhost`.

## Solução de problemas {#troubleshooting}
**A página não recarrega.** Abra o console do navegador: o cliente registra
`[Hot Reload] Connected to dev server` quando se conecta. Se ele fica tentando
reconectar, outro programa pode estar usando a porta 35729. Inicie com
`--hot-reload-port` e uma porta livre.

**Uma mudança não é percebida.** Só os arquivos em `paths.components` e
`paths.static` são observados. Confira esses caminhos no `quantum.config.yaml`.

A regra por trás desta página é a DEV-4 da especificação.

## Relacionados {#related}
- [Comandos da CLI](/pt/tools/cli) - `quantum start` e os outros comandos
- [Painel de desenvolvimento](/pt/tools/dev-panel) - O que cada requisição fez (`server.debug: true`)
- [Estrutura do projeto](/pt/guide/project-structure) - Onde ficam os componentes e os arquivos estáticos
