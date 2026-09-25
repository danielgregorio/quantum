---
source: guide/why-quantum.md
source_hash: b3e57fbe210d
---

# Por que Quantum

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/why-quantum).
:::

**Quantum constrói aplicações web a partir de páginas XML declarativas — com o
banco de dados, os formulários, as sessões e a IA na própria linguagem. Sem
cadeia de build, sem JavaScript, sem framework de front-end.**

É para quem desenvolve sozinho ou em equipe pequena e faz ferramentas
internas, dashboards, telas de administração e aplicações que usam um modelo
de linguagem — o tipo de software em que uma cadeia de build de front-end
custa mais do que o produto.

## Como é uma página

O código está em inglês, como no original.

```xml
<q:component name="Tasks">
  <q:action name="add" method="POST">
    <q:param name="title" required="true" minlength="3" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title) VALUES (:title)
      <q:param name="title" value="{title}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Added: {title}" />
  </q:action>

  <q:query name="tasks" datasource="db">SELECT id, title FROM tasks ORDER BY id</q:query>

  <ui:window title="Tasks">
    <q:if condition="flash"><ui:alert variant="info">{flash}</ui:alert></q:if>
    <ui:form on-submit="add" submit="Add" />
    <ui:table source="{tasks}" />
  </ui:window>
</q:component>
```

Essa é a funcionalidade inteira: o formulário desenha seu campo a partir do
`q:param` da ação (com `required` e `minlength` verificados no navegador e no
servidor), a consulta é parametrizada por construção, e a mesma página roda
num navegador (`quantum start`), num terminal (`quantum console`) e numa
janela de desktop (`quantum desktop`).

## O que é diferente

- **Um arquivo por página, de cima a baixo.** Guardas, ações, consultas e a
  tela ficam na ordem em que rodam
  ([como uma página roda](/guide/how-a-page-runs), em inglês).
- **As regras ficam num lugar só.** Um `q:param` diz o que um campo precisa
  ser; o formulário, o servidor e o `quantum check` leem dele.
- **A IA faz parte da linguagem.** `q:llm` responde a partir de uma base
  `q:knowledge` e cita as fontes, transmite a resposta enquanto escreve, e
  `q:agent` chama ferramentas que você escreve como funções Quantum — cada uma
  com um contrato de falha que a página pode tratar
  ([IA](/guide/ai), em inglês).
- **Não finge.** Um e-mail sem servidor, uma fonte de conhecimento que não
  pode ser lida, um atributo que uma tag `q:` não tem: cada um é um erro que
  diz o que fazer, não um sucesso silencioso.

## Como sabemos que funciona

- Uma [especificação](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)
  com regras numeradas; a suíte de testes falha quando uma regra não tem
  teste.
- Aplicações de verdade em `projects/`, cada uma testada de ponta a ponta no
  CI: uma lista de tarefas (navegador, console, desktop), um blog, um
  dashboard, um helpdesk com uploads e e-mail, um assistente de documentação
  (RAG) e um agente sobre um banco SQLite. As aplicações de IA também são
  testadas contra um servidor de modelos de verdade.
- Uma versão só é gerada depois que a suíte de testes inteira passa no commit
  marcado, e o exemplo desta página roda no CI como está.

## O que não é

- **Não é um framework mobile.** Celulares ficam fora da 1.0; o alvo React
  Native é um experimento.
- **Não é um framework de SPA.** As páginas são renderizadas no servidor; o
  navegador recebe HTML, mais pequenos scripts onde uma página precisa deles
  (busca enquanto você digita, respostas transmitidas aos poucos).
- **Não depende de um fornecedor de modelos, mas também não é mágica.** Um
  modelo local pequeno responde pior que um grande; Quantum mostra as fontes
  para que quem lê possa conferir.
- **SQLite primeiro.** Existem drivers para PostgreSQL e MySQL, mas são menos
  exercitados; migrações, planos de esquema e o `quantum check` estão
  provados no SQLite.

O que cada parte promete está em
[SUPPORT_TIERS.md](https://github.com/danielgregorio/quantum/blob/main/SUPPORT_TIERS.md)
e em [Estabilidade](/pt/stability/): Núcleo (Core) e IA são estáveis;
Experimental funciona sem promessa de estabilidade; o Laboratório (jogos,
Godot, AS4) vive no repositório para puxar a linguagem adiante.
