---
source: targets/desktop.md
source_hash: 27a8d69fc37c
---

# Desktop (`quantum desktop`)

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/targets/desktop).
:::

O `quantum desktop` abre a sua aplicação numa janela nativa. Ele inicia o
servidor da aplicação numa porta local livre (`127.0.0.1`) e abre uma janela do
[pywebview](https://pywebview.flowrl.com/) apontando para ele: a janela é um
navegador sem a moldura do navegador, então as páginas, as `q:action`, as
sessões e o layout responsivo são exatamente os da web. Fechar a janela para o
servidor.

```bash
pip install "quantum-framework[desktop]"

quantum desktop                      # the home page
quantum desktop /reports             # another page
quantum desktop --width 800 --height 600
quantum desktop --config other.config.yaml
```

Sem o extra `[desktop]`, o comando diz o que instalar em vez de falhar com um
erro de importação.

O título da janela acompanha a página: o `title` da primeira `ui:window`, senão o
nome do componente — o mesmo título que a aba do navegador e o `quantum console`
mostram.

Observações de plataforma (do pywebview):

- **Windows**: usa o Edge WebView2, já presente no Windows 10/11.
- **macOS**: usa o WebKit, nada para instalar.
- **Linux**: precisa de GTK/WebKit, por exemplo `sudo apt install python3-gi gir1.2-webkit2-4.1`.

## Escreva páginas, não uma aplicação de desktop {#write-pages-not-a-desktop-app}
Não existe uma "versão desktop" separada de uma tela. Escreva a página uma vez,
com elementos `ui:*` — veja [Uma aplicação, muitas telas](/pt/guide/ui) — e abra-a
com `quantum start`, `quantum console` ou `quantum desktop`.

## O que aconteceu com o `--target desktop` {#what-happened-to-target-desktop}
Até a 0.15, `quantum run app.q --target desktop` gerava um arquivo Python com uma
ponte JavaScript que traduzia `q:set` e `q:function` para o seu próprio estado
reativo. Era uma segunda implementação da linguagem, e ela discordava da
primeira. Foi removido na 0.16 (SPEC `UI-8`); gerar com ele é um erro que aponta
para o `quantum desktop`.
