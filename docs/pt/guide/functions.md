---
source: guide/functions.md
source_hash: 7d723be16710
---
# Funções (`q:function`)

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/functions). O código é o mesmo do original.
:::

Uma `q:function` é um trecho de lógica com nome dentro de um componente. Ela
recebe parâmetros, roda o seu corpo e devolve o valor do seu `q:return`. Cada
exemplo com uma **Saída** nesta página é executado pela suíte de testes.

## Declarar e chamar {#declaring-and-calling}

```xml
<q:component name="Sum" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:return value="{a + b}" />
  </q:function>

  <q:return value="Sum: {add(10, 20)}" />
</q:component>
```

**Saída:** `"Sum: 30"`

Uma função é chamada de qualquer expressão do seu componente — um atributo
`q:` ou o HTML da página: `<p>Total: {add(price, tax)}</p>`.

## Parâmetros {#parameters}

Os argumentos se ligam **pela posição** ou **pelo nome**, e o `default`
preenche o que falta:

```xml
<q:component name="Name" xmlns:q="https://quantum.lang/ns">
  <q:function name="formatName" returnType="string">
    <q:param name="firstName" type="string" required="true" />
    <q:param name="lastName" type="string" required="true" />
    <q:param name="title" type="string" default="Mr." />
    <q:return value="{title} {firstName} {lastName}" />
  </q:function>

  <q:return value="{formatName('John', 'Doe', 'Dr.')} / {formatName(lastName='Lee', firstName='Ann')}" />
</q:component>
```

**Saída:** `"Dr. John Doe / Mr. Ann Lee"`

Cada argumento é convertido para o seu `type` e verificado contra as suas
regras a cada chamada — o mesmo `q:param` das [ações](/pt/guide/actions):

| Atributo | Verifica |
|-----------|--------|
| `required="true"` | que o argumento foi passado |
| `type` | `string`, `number`, `integer`, `boolean`, `email`, `url`, `array`, `object` |
| `min` / `max` | intervalo numérico |
| `minlength` / `maxlength` / `pattern` | texto |
| `enum` | um de uma lista separada por vírgulas |
| `range="1..10"` | entre os dois, ambos incluídos |

```xml
<q:component name="SignUp" xmlns:q="https://quantum.lang/ns">
  <q:function name="register">
    <q:param name="email" type="email" required="true" />
    <q:param name="age" type="number" min="18" max="120" />
    <q:return value="{email} ({age})" />
  </q:function>

  <q:return value="{register('ann@example.com', '30')}" />
</q:component>
```

**Saída:** `"ann@example.com (30)"`

Um argumento que não passa interrompe a chamada com um erro que nomeia o
parâmetro:

```xml
<q:component name="Smallest" xmlns:q="https://quantum.lang/ns">
  <q:function name="register">
    <q:param name="email" type="email" required="true" />
    <q:param name="age" type="number" min="18" max="120" />
    <q:return value="{email} ({age})" />
  </q:function>

  <q:return value="{register('ann@example.com', 15)}" />
</q:component>
```

**Erro:** `Parameter 'age' must be at least 18 (got 15)`

## Retornar {#returning}

O primeiro `q:return` que roda termina a função, então as verificações podem
retornar antes:

```xml
<q:component name="Grade" xmlns:q="https://quantum.lang/ns">
  <q:function name="grade" returnType="string">
    <q:param name="score" type="number" required="true" />
    <q:if condition="score >= 90"><q:return value="A" /></q:if>
    <q:if condition="score >= 80"><q:return value="B" /></q:if>
    <q:return value="C" />
  </q:function>

  <q:return value="{grade(95)} {grade(85)} {grade(50)}" />
</q:component>
```

**Saída:** `"A B C"`

O `returnType` é verificado a cada retorno: o valor é convertido para o tipo
(`"7"` vira `7` para `number`), e um valor que não é do tipo é um erro que
nomeia a função. `any` (o padrão) aceita qualquer coisa; `void` quer dizer
que a função não retorna nada.

## Loops e recursão {#loops-and-recursion}

O corpo de uma função pode usar tudo o que um componente pode — `q:set`,
`q:loop`, `q:query`, outras funções, e ela mesma:

```xml
<q:component name="Maths" xmlns:q="https://quantum.lang/ns">
  <q:function name="sumArray" returnType="number">
    <q:param name="numbers" type="array" required="true" />
    <q:set name="total" type="number" value="0" />
    <q:loop type="array" items="{numbers}" var="n">
      <q:set name="total" operation="add" value="{n}" />
    </q:loop>
    <q:return value="{total}" />
  </q:function>

  <q:function name="factorial" returnType="number">
    <q:param name="n" type="number" required="true" />
    <q:if condition="n <= 1"><q:return value="{1}" /></q:if>
    <q:return value="{n * factorial(n - 1)}" />
  </q:function>

  <q:set name="numbers" type="array" value="[10, 20, 30, 40]" />
  <q:return value="{sumArray(numbers)} {factorial(5)}" />
</q:component>
```

**Saída:** `"100 120"`

## O que a `q:function` não tem {#what-q-function-does-not-have}

Versões antigas desta página descreviam `cache`, `memoize`, `pure`, `async`,
`retry`, `timeout`, `access`, `scope="global"`, endpoints REST e um sistema de
eventos. Eles eram aceitos e nunca fizeram nada, e foram removidos na 0.11: o
parser agora recusa esses atributos e diz isso.

Uma função pertence ao seu componente. Para compartilhar lógica entre
páginas, coloque-a num componente e use-o com [`q:import`](/pt/guide/components).

## Relacionados {#related}

- [Expressões e databinding](/pt/guide/databinding)
- [Condicionais](/pt/guide/conditionals) · [Loops](/pt/guide/loops)
- [Gerenciamento de estado (`q:set`)](/pt/guide/state-management)
