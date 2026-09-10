# State Management (`q:set`)

O `q:set` é a tag fundamental para gerenciamento de estado no Quantum, permitindo criar, modificar e validar variáveis de forma declarativa e type-safe.

## 🎯 Conceitos Básicos

### Sintaxe Simples

```xml
<q:set name="variableName" type="string" value="initialValue" />
```

### Atributos Obrigatórios

| Atributo | Descrição | Exemplo |
|----------|-----------|---------|
| `name` | Nome da variável | `name="counter"` |

### Atributos Opcionais

| Atributo | Descrição | Padrão | Exemplo |
|----------|-----------|--------|---------|
| `type` | Tipo de dados | `string` | `type="number"` |
| `value` | Valor inicial | `null` | `value="10"` |
| `default` | Valor padrão | `null` | `default="0"` |
| `scope` | Escopo da variável | `local` | `scope="component"` |
| `operation` | Operação a realizar | `assign` | `operation="increment"` |

## 📦 Tipos de Dados

### Tipos Primitivos

```xml
<!-- String (padrão) -->
<q:set name="message" type="string" value="Hello World" />

<!-- Number (inteiro ou float) -->
<q:set name="age" type="number" value="25" />

<!-- Decimal (float) -->
<q:set name="price" type="decimal" value="19.99" />

<!-- Boolean -->
<q:set name="isActive" type="boolean" value="true" />

<!-- Date -->
<q:set name="birthdate" type="date" value="1990-01-01" />

<!-- DateTime -->
<q:set name="created" type="datetime" value="2025-01-01T12:00:00Z" />
```

### Tipos Estruturados

```xml
<!-- Array -->
<q:set name="fruits" type="array" value='["apple", "banana", "orange"]' />

<!-- Object -->
<q:set name="user" type="object" value='{"name": "Daniel", "age": 30}' />

<!-- JSON -->
<q:set name="config" type="json" value='{"debug":true,"port":8080}' />
```

## 🔧 Operações

### Atribuição Básica

```xml
<q:component name="BasicAssignment" xmlns:q="https://quantum.lang/ns">
  <q:set name="x" type="number" value="10" />
  <q:return value="x = {x}" />
</q:component>
```

**Resultado:** `x = 10`

### Expressões Aritméticas

```xml
<q:component name="ArithmeticExpressions" xmlns:q="https://quantum.lang/ns">
  <q:set name="a" type="number" value="5" />
  <q:set name="b" type="number" value="3" />
  <q:set name="sum" type="number" value="{a + b}" />
  <q:return value="Sum: {sum}" />
</q:component>
```

**Resultado:** `Sum: 8`

### Increment/Decrement

```xml
<q:component name="Counter" xmlns:q="https://quantum.lang/ns">
  <q:set name="counter" type="number" value="0" />

  <!-- Incrementa em 1 -->
  <q:set name="counter" operation="increment" />
  <q:set name="counter" operation="increment" />
  <q:set name="counter" operation="increment" />

  <q:return value="Counter: {counter}" />
</q:component>
```

**Resultado:** `Counter: 3`

#### Increment com Step

```xml
<q:set name="counter" value="0" />
<q:set name="counter" operation="increment" step="5" />
<q:return value="counter = {counter}" />
```

**Resultado:** `counter = 5`

### Operações Aritméticas

```xml
<q:component name="ArithmeticOps" xmlns:q="https://quantum.lang/ns">
  <q:set name="total" type="number" value="10" />

  <!-- Adiciona 5 -->
  <q:set name="total" operation="add" value="5" />

  <!-- Multiplica por 2 -->
  <q:set name="total" operation="multiply" value="2" />

  <q:return value="Total: {total}" />
</q:component>
```

**Resultado:** `Total: 30` (10 + 5 = 15, 15 * 2 = 30)

## 📚 Operações em Arrays

### Append/Prepend

```xml
<q:component name="ArrayOperations" xmlns:q="https://quantum.lang/ns">
  <q:set name="list" type="array" value="[]" />

  <!-- Adiciona no final -->
  <q:set name="list" operation="append" value="apple" />
  <q:set name="list" operation="append" value="banana" />

  <!-- Adiciona no início -->
  <q:set name="list" operation="prepend" value="orange" />

  <q:return value="{list}" />
</q:component>
```

**Resultado:** `['orange', 'apple', 'banana']`

### Remove/RemoveAt

```xml
<q:set name="list" type="array" value='["a", "b", "c", "d"]' />

<!-- Remove por valor -->
<q:set name="list" operation="remove" value="b" />

<!-- Remove por índice -->
<q:set name="list" operation="removeAt" index="2" />
```

### Outras Operações

```xml
<!-- Limpar array -->
<q:set name="list" operation="clear" />

<!-- Ordenar -->
<q:set name="list" operation="sort" />

<!-- Reverter -->
<q:set name="list" operation="reverse" />

<!-- Remover duplicatas -->
<q:set name="list" operation="unique" />
```

## 🗂️ Operações em Objects

### Merge

```xml
<q:component name="ObjectMerge" xmlns:q="https://quantum.lang/ns">
  <q:set name="user" type="object" value="{}" />

  <q:set name="user" operation="merge" value='{"name":"Daniel"}' />
  <q:set name="user" operation="merge" value='{"age":30}' />
  <q:set name="user" operation="merge" value='{"email":"daniel@example.com"}' />

  <q:return value="{user}" />
</q:component>
```

**Resultado:** `{'name': 'Daniel', 'age': 30, 'email': 'daniel@example.com'}`

### SetProperty/DeleteProperty

```xml
<q:set name="config" type="object" value="{}" />

<!-- Definir propriedade -->
<q:set name="config" operation="setProperty" key="debug" value="true" />

<!-- Deletar propriedade -->
<q:set name="config" operation="deleteProperty" key="debug" />
```

### Clone

```xml
<q:set name="original" type="object" value='{"x":1}' />
<q:set name="copy" operation="clone" source="original" />
```

## 🔤 Transformações de String

```xml
<q:set name="text" value="Hello World" />

<!-- Uppercase -->
<q:set name="text" operation="uppercase" />
<!-- Resultado: HELLO WORLD -->

<!-- Lowercase -->
<q:set name="text" operation="lowercase" />
<!-- Resultado: hello world -->

<!-- Trim -->
<q:set name="text" value="  spaces  " />
<q:set name="text" operation="trim" />
<!-- Resultado: spaces -->
```

## 🔄 Uso com Loops

```xml
<q:component name="LoopAccumulator" xmlns:q="https://quantum.lang/ns">
  <q:set name="total" type="number" value="0" />

  <q:loop type="range" var="i" from="1" to="5">
    <q:set name="total" operation="add" value="{i}" />
  </q:loop>

  <q:return value="Total: {total}" />
</q:component>
```

**Resultado:** `Total: 15` (1+2+3+4+5)

### Array Builder com Loop

```xml
<q:component name="ArrayBuilder" xmlns:q="https://quantum.lang/ns">
  <q:set name="results" type="array" value="[]" />

  <q:loop type="range" var="i" from="1" to="3">
    <q:set name="results" operation="append" value="{i * 2}" />
  </q:loop>

  <q:return value="{results}" />
</q:component>
```

**Resultado:** `[2, 4, 6]`

## ✅ Validação

### Required & Nullable

```xml
<!-- Campo obrigatório -->
<q:set name="email" type="string" required="true" />

<!-- Não aceita null -->
<q:set name="age" type="number" nullable="false" />
```

### Validadores Built-in

```xml
<!-- Email -->
<q:set name="email" type="string" value="daniel@example.com" validate="email" />

<!-- URL -->
<q:set name="website" type="string" validate="url" />

<!-- CPF (com verificação de dígitos) -->
<q:set name="cpf" type="string" value="123.456.789-09" validate="cpf" />

<!-- CNPJ (com verificação de dígitos) -->
<q:set name="cnpj" type="string" validate="cnpj" />

<!-- Telefone BR -->
<q:set name="phone" type="string" validate="phone" />

<!-- CEP -->
<q:set name="cep" type="string" validate="cep" />

<!-- UUID -->
<q:set name="id" type="string" validate="uuid" />

<!-- Cartão de crédito -->
<q:set name="card" type="string" validate="creditcard" />

<!-- IP v4 -->
<q:set name="ip" type="string" validate="ipv4" />

<!-- IP v6 -->
<q:set name="ip" type="string" validate="ipv6" />
```

### Regex Pattern

```xml
<!-- Pattern customizado -->
<q:set name="code" type="string" pattern="^[A-Z]{3}\d{4}$" />
```

### Range

```xml
<!-- Range numérico -->
<q:set name="age" type="number" value="25" range="18..120" />

<!-- Range de datas -->
<q:set name="date" type="date" range="2024-01-01..2025-12-31" />
```

### Enum

```xml
<q:set name="status" type="string" value="active" enum="pending,active,inactive" />
```

### Min/Max

```xml
<!-- Números -->
<q:set name="score" type="number" min="0" max="100" />

<!-- String length -->
<q:set name="username" type="string" minlength="3" maxlength="20" />
```

## 🔐 Exemplo Completo: Formulário de Cadastro

```xml
<q:component name="UserRegistration" xmlns:q="https://quantum.lang/ns">
  <!-- Email com validação -->
  <q:set
    name="email"
    type="string"
    value="daniel@example.com"
    required="true"
    validate="email"
    maxlength="255"
  />

  <!-- Senha com validação de força -->
  <q:set
    name="password"
    type="string"
    value="Segura123"
    required="true"
    minlength="8"
    pattern="^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)"
  />

  <!-- CPF -->
  <q:set
    name="cpf"
    type="string"
    value="123.456.789-09"
    required="true"
    validate="cpf"
  />

  <!-- Idade -->
  <q:set
    name="age"
    type="number"
    value="25"
    required="true"
    range="18..120"
  />

  <!-- Plano -->
  <q:set
    name="plan"
    type="string"
    value="basic"
    enum="free,basic,premium,enterprise"
    default="free"
  />

  <q:return value="Cadastro válido para {email}" />
</q:component>
```

**Resultado:** `Cadastro válido para daniel@example.com`

## 🌐 Escopos

### Local (padrão)

```xml
<q:set name="temp" value="123" scope="local" />
```

Variável existe apenas no bloco atual.

### Function

```xml
<q:function name="calculate">
  <q:set name="result" value="0" scope="function" />
</q:function>
```

Variável visível dentro da função.

### Component

```xml
<q:set name="globalCounter" value="0" scope="component" />
```

Variável visível em todo o componente.

### Session

```xml
<q:set name="userData" value="{}" scope="session" />
```

Variável compartilhada na sessão (futuro).

## 🎯 Exemplos Práticos

### Calculadora de Carrinho

```xml
<q:component name="ShoppingCart" xmlns:q="https://quantum.lang/ns">
  <q:param name="price" type="number" default="10" />
  <q:param name="quantity" type="number" default="2" />

  <q:set name="subtotal" type="number" value="{price * quantity}" />
  <q:set name="tax" type="number" value="{subtotal * 0.1}" />
  <q:set name="total" type="number" value="{subtotal + tax}" />

  <q:return value="Total: R$ {total}" />
</q:component>
```

### Construtor de Objeto Progressivo

```xml
<q:component name="BuildUser" xmlns:q="https://quantum.lang/ns">
  <q:set name="user" type="object" value="{}" />

  <q:set name="user" operation="merge" value='{"name":"Daniel"}' />
  <q:set name="user" operation="merge" value='{"age":30}' />
  <q:set name="user" operation="merge" value='{"role":"admin"}' />

  <q:return value="{user}" />
</q:component>
```

### Filtro e Processamento de Lista

```xml
<q:component name="ProcessList" xmlns:q="https://quantum.lang/ns">
  <q:set name="numbers" type="array" value="[5,2,8,1,9]" />

  <!-- Ordenar -->
  <q:set name="numbers" operation="sort" />

  <!-- Reverter -->
  <q:set name="numbers" operation="reverse" />

  <q:return value="Sorted (desc): {numbers}" />
</q:component>
```

## ⚠️ Tratamento de Erros

Quando uma validação falha, o Quantum lança um erro descritivo:

```xml
<q:set name="email" value="invalid" validate="email" />
```

**Erro:** `Set execution error for 'email': Invalid email format`

```xml
<q:set name="age" type="number" value="15" range="18..120" />
```

**Erro:** `Set execution error for 'age': Value must be between 18 and 120`

## 📋 Resumo de Operações

| Operação | Descrição | Exemplo |
|----------|-----------|---------|
| `assign` | Atribuição (padrão) | `value="10"` |
| `increment` | Incremento | `operation="increment"` |
| `decrement` | Decremento | `operation="decrement"` |
| `add` | Adição | `operation="add" value="5"` |
| `multiply` | Multiplicação | `operation="multiply" value="2"` |
| `append` | Adiciona no fim (array) | `operation="append" value="item"` |
| `prepend` | Adiciona no início (array) | `operation="prepend" value="item"` |
| `remove` | Remove por valor (array) | `operation="remove" value="item"` |
| `removeAt` | Remove por índice (array) | `operation="removeAt" index="2"` |
| `clear` | Limpa array | `operation="clear"` |
| `sort` | Ordena array | `operation="sort"` |
| `reverse` | Reverte array | `operation="reverse"` |
| `unique` | Remove duplicatas | `operation="unique"` |
| `merge` | Mescla objetos | `operation="merge" value='{...}'` |
| `setProperty` | Define propriedade | `operation="setProperty" key="x" value="1"` |
| `deleteProperty` | Remove propriedade | `operation="deleteProperty" key="x"` |
| `clone` | Clona objeto | `operation="clone" source="original"` |
| `uppercase` | Maiúsculas | `operation="uppercase"` |
| `lowercase` | Minúsculas | `operation="lowercase"` |
| `trim` | Remove espaços | `operation="trim"` |

## 🔗 Ver Também

- [Loops (`q:loop`)](./loops.md)
- [Databinding](./databinding.md)
- [Components (`q:component`)](./components.md)
