---
source: tools/error-pages.md
source_hash: 0611f0033fe0
---

# Páginas de erro

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/tools/error-pages).
:::

Quando uma página falha durante o desenvolvimento (`server.debug: true`), a
página de erro mostra **onde**: o arquivo `.q`, as linhas em volta daquela que
falhou com essa linha marcada, a mensagem — que diz o que mudar — e links para as
regras da SPEC que a mensagem cita (`PARSE-2`, `ACT-9`…). O traceback do Python
também está lá, recolhido, para quando o problema está no próprio Quantum.

A linha é a mais interna que falhou:

- um erro de parser aponta para a tag (`<q:sett>` na linha 3);
- um erro de execução aponta para a instrução — o `q:set` dentro do `q:if`, não
  o `q:if`;
- um erro dentro de um componente que você chamou aponta para **o arquivo desse
  componente**, não para o `<Card />` que o chamou.

Erros de parser trazem a linha em todo lugar, não só na página: o `quantum run`
e os logs mostram `at line 3: <q:sett name="x" value="1"/>`.

Com `debug: false` a página diz apenas que ocorreu um erro — sem código, sem
detalhes da mensagem. Tudo numa página de erro é escapado: uma mensagem pode
trazer o que a requisição enviou.

## Recarregar mantém você logado {#reloading-keeps-you-logged-in}
Com `debug: true` e `reload: true`, salvar um arquivo reinicia o processo do
servidor. Sem um `security.secret_key` configurado, cada processo inventava a
sua própria chave de sessão, então cada salvamento deslogava todo mundo. No modo
de depuração a chave agora é guardada em `.quantum/dev-secret-key`, ao lado do
seu `quantum.config.yaml` (coloque `.quantum/` no git-ignore), e as sessões
sobrevivem às recargas. Em produção, defina `QUANTUM_SECRET_KEY` ou
`security.secret_key` — o arquivo nunca é usado com `debug: false`.
