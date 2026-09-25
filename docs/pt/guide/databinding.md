---
source: guide/databinding.md
source_hash: 68dae0629ce9
---
# Expressões e databinding

::: info Tradução automática
Esta página foi traduzida automaticamente do inglês e ainda não foi revisada
por um falante nativo; correções são bem-vindas no GitHub. Se algo não bater,
vale o [original em inglês](/guide/databinding). O código é o mesmo do original.
:::

Tudo o que está entre chaves é uma expressão: `{total * 2}`. O Quantum a
avalia com as variáveis do escopo e põe o resultado no lugar.

Cada exemplo desta página roda como aparece — `tests/docs` executa cada bloco
e o compara com a **Saída** abaixo dele.

## Um valor, ou um texto com valores dentro {#a-value-or-text-with-values-in-it}

Quando um atributo é **exatamente uma expressão**, você recebe o valor com o
seu tipo. Quando há qualquer outra coisa em volta, você recebe texto:

```xml
<q:component name="Order" xmlns:q="https://quantum.lang/ns">
  <q:set name="price" value="9.5" type="number" />
  <q:set name="qty" value="3" type="number" />
  <q:return value="{price * qty}" />
</q:component>
```

**Saída:** `28.5`

```xml
<q:component name="Summary" xmlns:q="https://quantum.lang/ns">
  <q:set name="price" value="9.5" type="number" />
  <q:set name="qty" value="3" type="number" />
  <q:return value="{qty} items, total {price * qty}" />
</q:component>
```

**Saída:** `"3 items, total 28.5"`

## Operadores {#operators}

| Tipo | Operadores |
|------|-----------|
| Aritméticos | `+` `-` `*` `/` `//` (divisão inteira) `%` `**` |
| Comparação | `==` `!=` `<` `<=` `>` `>=` `in` `not in` |
| Lógicos | `and` `or` `not` — ou `&&` `\|\|` `!` |
| Escolha | `value if condition else other` |

Valores que chegam como texto — um campo de formulário, um parâmetro de
consulta, um argumento de ferramenta vindo de um LLM — são tratados como
números quando parecem números, então `+` soma:

```xml
<q:component name="Sum" xmlns:q="https://quantum.lang/ns">
  <q:set name="a" value="17" />
  <q:set name="b" value="25" />
  <q:return value="{a + b}" />
</q:component>
```

**Saída:** `42`

```xml
<q:component name="Age" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="20" type="number" />
  <q:set name="invited" value="false" type="boolean" />
  <q:return value="{'enters' if age >= 18 && !invited else 'waits'}" />
</q:component>
```

**Saída:** `"enters"`

`in` compara do jeito que `==` compara, então um valor que chegou como texto
ainda acha o seu número numa lista:

```xml
<q:component name="Member" xmlns:q="https://quantum.lang/ns">
  <q:set name="chosen" value="5" />
  <q:set name="allowed" value="[1, 5, 10]" type="array" />
  <q:return value="{chosen in allowed}" />
</q:component>
```

**Saída:** `true`

## Ler listas e registros {#reading-lists-and-records}

```xml
<q:component name="Reading" xmlns:q="https://quantum.lang/ns">
  <q:set name="user" type="object" value='{"name": "Ana", "tags": ["admin", "dev"]}' />
  <q:return value="{user.name} has {user.tags.length} tags, first {user.tags[0]}, last {user.tags[-1]}" />
</q:component>
```

**Saída:** `"Ana has 2 tags, first admin, last dev"`

`true`, `false` e `null` são literais. Os textos usam aspas simples dentro de
um atributo entre aspas duplas: `{status == 'active'}`.

## Funções {#functions}

| Função | Exemplo | Resultado |
|----------|---------|--------|
| `upper(s)`, `lower(s)`, `trim(s)` | `upper('ana')` | `ANA` |
| `replace(s, old, new)` | `replace('a-b', '-', '+')` | `a+b` |
| `split(s, sep=',')` | `split('a,b')` | `['a', 'b']` |
| `contains(s, part)` | `contains('quantum', 'ant')` | `true` |
| `len(x)`, `first(x)`, `last(x)` | `len(items)` | o número de itens |
| `get(x, key, default=null)` — uma chave ou índice opcional | `get(prefs, 'theme', 'light')` | o valor, ou `default` quando falta |
| `join(list, sep=', ')`, `sort(list)` | `join(sort(tags), ' / ')` | texto |
| `round(n, digits=0)` — metades para longe do zero | `round(2.5)` | `3` |
| `ceil(n)`, `floor(n)`, `abs`, `min`, `max` | `ceil(7 / 3)` | `3` |
| `int(x)`, `float(x)`, `str(x)` | `int('42')` | `42` |
| `now()` | `now()` | a data e hora atuais |
| `dateAdd(unit, n, start=now)` | `dateAdd('d', 7)` | daqui a uma semana |
| `dateDiff(unit, start, end)` | `dateDiff('h', a, b)` | horas inteiras |
| `dateFormat(date, pattern)` | `dateFormat(now(), '%d/%m/%Y')` | `10/09/2026` |
| `hashPassword(s)`, `verifyPassword(s, hash)` | veja [Autenticação](/pt/guide/authentication) | |
| `random()`, `random(a, b)` | `random(1, 6)` | um número de 0 até 1; um inteiro de `a` a `b` |
| `chance(p)`, `pick(list)` | `pick(tips)` | verdadeiro com probabilidade `p`; um elemento |

Unidades das funções de data: `s`, `n` (minutos), `h`, `d`, `w`. Uma
`q:function` declarada no componente é chamada do mesmo jeito:
`{twice(price)}`.

As funções são chamadas pelo nome, nunca como métodos: `split(title, ' ')`,
não `title.split(' ')`; `ceil(n)`, não `Math.ceil(n)`. O erro para um hábito
de JavaScript nomeia a função a usar. `.length` funciona em texto e em listas.

```xml
<q:component name="Functions" xmlns:q="https://quantum.lang/ns">
  <q:function name="twice">
    <q:param name="x" type="number" />
    <q:return value="{x * 2}" />
  </q:function>
  <q:set name="tags" value='["dev", "admin"]' type="array" />
  <q:return value="{upper(join(sort(tags), ' / '))} {twice(21)}" />
</q:component>
```

**Saída:** `"ADMIN / DEV 42"`

## Variáveis de escopo {#scoped-variables}

`session.`, `application.`, `request.`, `form.`, `query.` e `cookie.` leem do
seu escopo. Uma página muitas vezes renderiza antes de o valor existir — antes
do login, por exemplo — então ler um que não está definido dá texto vazio:

```xml
<q:component name="Hello" xmlns:q="https://quantum.lang/ns">
  <q:return value="[{session.name}]" />
</q:component>
```

**Saída:** `"[]"`

Fazer contas com um valor que não está definido é um erro, não um resultado
vazio. Para um contador, use `operation="increment"`, que começa do zero:

```xml
<q:component name="Visits" xmlns:q="https://quantum.lang/ns">
  <q:set name="session.visits" operation="increment" />
  <q:return value="{session.visits}" />
</q:component>
```

**Saída:** `1`

## Quando uma expressão falha {#when-an-expression-fails}

Num atributo `q:`, uma expressão que não pode ser avaliada para o componente
com um erro que a nomeia — nada é substituído em silêncio:

```xml
<q:component name="Broken" xmlns:q="https://quantum.lang/ns">
  <q:set name="total" value="3" type="number" />
  <q:return value="{totl + 1}" />
</q:component>
```

**Erro:** `{totl + 1} could not be evaluated: variable 'totl' is not defined, did you mean 'total'?`

O mesmo vale para uma avaliação que falha (`{10 / zero}`) e para contas com um
valor de escopo que não está definido.

Dois lugares são mais tolerantes de propósito:

- **As condições testam presença.** Um nome, chave ou atributo que não existe
  torna uma `condition` falsa, então `<q:if condition="flash">` funciona antes
  de existir uma mensagem flash. Qualquer outra coisa — um erro de sintaxe,
  uma função que não existe — continua sendo um erro.
- **O conteúdo HTML mantém o texto.** Uma expressão no conteúdo da página que
  não resolve é renderizada como foi escrita e registrada no log uma vez. O
  conteúdo da página também traz exemplos de código e chaves soltas, e isso
  não pode quebrar a página.

```xml
<q:component name="Presence" xmlns:q="https://quantum.lang/ns">
  <q:if condition="flash">
    <q:return value="there is one" />
  </q:if>
  <q:return value="there is none" />
</q:component>
```

**Saída:** `"there is none"`

## Chaves que não são expressões {#braces-that-are-not-expressions}

Um objeto JSON e um quantificador de expressão regular ficam como estão:

```xml
<q:component name="Literals" xmlns:q="https://quantum.lang/ns">
  <q:set name="pattern" value="[0-9]{10,11}" />
  <q:set name="rows" value='[{"a": 1}, {"b": 2}]' type="array" />
  <q:return value="{pattern} {len(rows)}" />
</q:component>
```

**Saída:** `"[0-9]{10,11} 2"`

## Referência {#reference}

As regras desta página são `EXPR-1` a `EXPR-5` no
[SPEC.md](https://github.com/danielgregorio/quantum/blob/main/SPEC.md).
