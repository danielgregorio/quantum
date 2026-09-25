---
source: guide/conditionals.md
source_hash: f186a35fba5d
---
# Condicionais (q:if, q:elseif, q:else)

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/conditionals). O código é o mesmo do original.
:::

O `q:if` roda o seu corpo quando a sua `condition` é verdadeira. `q:elseif` e
`q:else` acrescentam alternativas. Cada exemplo desta página com uma
**Saída** é executado pela suíte de testes.

## If, elseif, else {#if-elseif-else}

```xml
<q:component name="Grade" xmlns:q="https://quantum.lang/ns">
  <q:param name="score" type="number" default="85" />

  <q:if condition="score >= 90">
    <q:return value="A" />
  </q:if>
  <q:elseif condition="score >= 80">
    <q:return value="B" />
  </q:elseif>
  <q:else>
    <q:return value="C" />
  </q:else>
</q:component>
```

**Saída:** `"B"`

`q:elseif` e `q:else` também podem ser escritos **dentro** do `q:if`, depois
do seu corpo. As duas formas significam a mesma coisa, em qualquer lugar —
num componente, num loop, numa função, numa ação ou num template HTML:

```xml
<q:component name="EvenOdd" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="4">
    <q:if condition="i % 2 == 0">
      <q:return value="{i} even" />
      <q:else>
        <q:return value="{i} odd" />
      </q:else>
    </q:if>
  </q:loop>
</q:component>
```

**Saída:** `["1 odd", "2 even", "3 odd", "4 even"]`

Um `q:else` ou `q:elseif` sem um `q:if` logo antes é um erro de parse.

## Escrever condições {#writing-conditions}

Uma condição é uma [expressão](/pt/guide/databinding), com ou sem chaves:
`condition="age >= 18"` e `condition="{age >= 18}"` são a mesma coisa.

| | |
|---|---|
| Comparação | `==` `!=` `<` `<=` `>` `>=` `in` |
| Lógica | `and` `or` `not`, ou `&&` `\|\|` `!` |
| Texto | `status == 'active'` — aspas simples dentro do atributo |

```xml
<q:component name="Filter" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" type="array" value='[
    {"name": "Apple", "type": "fruit", "price": 1.50},
    {"name": "Carrot", "type": "vegetable", "price": 0.75},
    {"name": "Banana", "type": "fruit", "price": 0.45}
  ]' />

  <q:loop type="array" var="item" items="{items}">
    <q:if condition="item.type == 'fruit' && item.price < 1.00">
      <q:return value="{item.name}: {item.price}" />
    </q:if>
  </q:loop>
</q:component>
```

**Saída:** `["Banana: 0.45"]`

### Verdadeiro e falso {#true-and-false}

`false`, `0`, texto vazio, uma lista vazia e `null` são falsos; todo o resto
é verdadeiro. O **texto** `"false"` não está vazio, então é verdadeiro —
declare booleanos com `type="boolean"`:

```xml
<q:component name="Booleans" xmlns:q="https://quantum.lang/ns">
  <q:set name="as_text" value="false" />
  <q:set name="as_boolean" value="false" type="boolean" />
  <q:set name="r" value="" />
  <q:if condition="as_text"><q:set name="r" value="{r}text " /></q:if>
  <q:if condition="as_boolean"><q:set name="r" value="{r}boolean" /></q:if>
  <q:return value="[{r}]" />
</q:component>
```

**Saída:** `"[text ]"`

### Uma condição é um teste de presença {#a-condition-is-a-presence-test}

Um nome, chave ou atributo que não existe torna a condição **falsa** — é isso
que deixa uma página verificar um valor que só às vezes existe, como uma
mensagem flash:

```xml
<q:component name="Notice" xmlns:q="https://quantum.lang/ns">
  <q:if condition="flash">
    <q:return value="{flash}" />
  </q:if>
  <q:return value="no message" />
</q:component>
```

**Saída:** `"no message"`

Qualquer outra falha é um erro, nunca um falso silencioso — uma condição
inacabada para o componente:

```xml
<q:component name="Unfinished" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="20" type="number" />
  <q:if condition="age >">
    <q:return value="adult" />
  </q:if>
</q:component>
```

**Erro:** `condition 'age >' could not be evaluated`

## Retornar antes {#returning-early}

O primeiro `q:return` que roda termina o componente ou a função, então uma
cadeia de verificações não precisa de aninhamento:

```xml
<q:component name="Order" xmlns:q="https://quantum.lang/ns">
  <q:function name="process">
    <q:param name="order_id" type="string" default="" />
    <q:if condition="!order_id">
      <q:return value="order id required" />
    </q:if>
    <q:return value="order {order_id} processed" />
  </q:function>

  <q:return value="{process()} / {process('A7')}" />
</q:component>
```

**Saída:** `"order id required / order A7 processed"`

## Numa página {#in-a-page}

No HTML, o `q:if` decide o que é renderizado:

```xml
<q:component name="menu" xmlns:q="https://quantum.lang/ns">
  <nav>
    <q:if condition="session.authenticated">
      <span>Hello, {session.userName}</span>
      <a href="/logout">Logout</a>
    </q:if>
    <q:else>
      <a href="/login">Login</a>
    </q:else>
  </nav>
</q:component>
```

**Mostra:** `Login`

Antes do login, `session.authenticated` não existe, então a página mostra o
link Login. Veja [Autenticação](/pt/guide/authentication) para o login em si.

## Relacionados {#related}

- [Expressões e databinding](/pt/guide/databinding) — tudo o que uma condição pode usar
- [Loops](/pt/guide/loops)
- [Funções](/pt/guide/functions)
