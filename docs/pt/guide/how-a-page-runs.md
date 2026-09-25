---
source: guide/how-a-page-runs.md
source_hash: ac6cc77dd1e5
---
# Como uma página roda

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/how-a-page-runs). O código é o mesmo do original.
:::

Uma página `.q` tem dois tipos de partes: **instruções** (`q:set`, `q:query`,
`q:invoke`, `q:action`…) que fazem coisas, e **marcação** (HTML, elementos
`ui:*`, `{expressions}`) que mostra coisas. Saber a ordem em que elas rodam
explica cada regra que parece surpreendente no começo — e as mensagens de
erro dessas regras apontam para cá.

## Um GET, em ordem

1. A **rota** escolhe o componente: `components/index.q` é `/`,
   `components/loja/[id].q` é `/loja/41`.
2. `require_auth` / `require_role` decidem se ela abre ou não.
3. As **guardas** rodam: um `q:if` no topo cujo ramo tem um `q:redirect`.
4. As **instruções** da página rodam, de cima para baixo.
5. A **marcação** é renderizada com as variáveis que as instruções deixaram:
   `{expressions}`, os `q:loop` e `q:if` dentro da marcação, os elementos
   `ui:*`, os componentes chamados a partir dela.

```xml
<q:component name="InOrder">
  <q:set name="items" type="array" value='["a", "b", "c"]' />
  <q:set name="total" value="{len(items)}" type="number" />
  <p>Total: {total}</p>
  <q:loop type="array" items="{items}" var="i">
    <p>Item {i}</p>
  </q:loop>
</q:component>
```

**Mostra:** `Total: 3` · `Item a` · `Item c`

A marcação só **renderiza**. Ela nunca roda uma instrução — então uma
instrução colocada dentro dela nunca rodaria, e o Quantum a recusa em vez de
ignorá-la:

```xml
<q:component name="Wrong">
  <div>
    <q:set name="x" value="1" />
  </div>
</q:component>
```

**Erro:** `never runs (PARSE-2): statements run before the page is rendered`

Mova o `q:set` para cima da marcação. Pelo mesmo motivo, um `q:set` dentro de
um `q:loop` da marcação cujo valor as linhas leem é um erro: o loop roda para
cada item antes de qualquer linha ser desenhada, então todas as linhas
mostrariam o último valor. Calcule na expressão: `{item.price * item.qty}`.

As `q:function` de uma página estão disponíveis na página inteira, e nas
ações dela, onde quer que estejam escritas:

```xml
<q:set name="doubled" value="{double_it(21)}" type="number" />
<q:function name="double_it">
  <q:param name="n" type="number" />
  <q:return value="{n * 2}" />
</q:function>
<q:return value="{doubled}" />
```

**Saída:** `42`

## Um POST: a ação, depois um redirecionamento

Um formulário envia para a página com um campo `action` que nomeia uma das
suas `q:action`. Os passos 1–3 rodam como num GET; depois **só aquela ação**
roda — não as instruções da página. Ela valida os seus `q:param`, faz o seu
trabalho e termina num `q:redirect`: o navegador então pede a página com um
GET, que roda como acima.

Como as instruções da página não rodam numa ação, uma variável que a página
define não existe ali:

```xml
<q:component name="Order">
  <q:set name="total" value="42" type="number" />

  <q:action name="pay" method="POST">
    <!-- {total} does not exist here: the page's q:set did not run. -->
    <q:redirect url="/order" flash="Paid {total}." />
  </q:action>

  <p>Total: {total}</p>
</q:component>
```

A página mostra `Total: 42`; enviar `pay` é um erro, e a mensagem diz
exatamente isto:

```text
q:action 'pay' failed: {total} could not be evaluated: variable 'total' is not defined (in scope: form). A q:action does not run the page's statements (ACT-9): query or compute what it needs inside the action.
```

A ação consulta ou calcula ela mesma o que precisa.

As guardas são a exceção: elas rodam antes da página **e** antes de cada uma
das ações dela, então uma guarda que redireciona também barra a ação. É
também por isso que uma guarda não pode ler uma variável que a página define
— na ação, ela não existiria, e a guarda deixaria o envio passar. As guardas
leem os escopos (`session.x`) diretamente; `require_auth` e `require_role`
cuidam do caso comum para você.

Uma ação que não termina em `q:redirect` responde com a própria página (as
instruções dela rodam depois da ação, como num GET). A resposta é um 200 a um
POST, e recarregá-la envia o formulário de novo — termine as ações com
`q:redirect`.

## Quanto tempo as coisas vivem

| O quê | Vive | Visto por |
|---|---|---|
| uma variável da página (`q:set name="x"`) | uma requisição | aquela requisição |
| `flash` | a próxima página, uma vez | aquele visitante |
| `session.x` | entre requisições, no cookie de sessão assinado | um visitante |
| `application.x` | enquanto o processo do servidor roda | todo visitante daquele processo |

Cada requisição roda no seu próprio runtime, então duas requisições nunca
veem as variáveis uma da outra. `application.x` é memória no processo do
servidor: some depois de um reinício, e com `gunicorn --workers 4` cada
worker tem a sua. Guarde no banco tudo o que precisa durar ou ser
compartilhado.
