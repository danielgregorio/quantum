# How a Page Runs

A `.q` page has two kinds of parts: **statements** (`q:set`, `q:query`,
`q:invoke`, `q:action`…) that do things, and **markup** (HTML, `ui:*`
elements, `{expressions}`) that shows things. Knowing the order in which they
run explains every rule that looks surprising at first — and the error
messages for those rules link here.

## A GET, in order

1. The **route** picks the component: `components/index.q` is `/`,
   `components/loja/[id].q` is `/loja/41`.
2. `require_auth` / `require_role` decide whether it opens at all.
3. **Guards** run: a top-level `q:if` whose branch has a `q:redirect`.
4. The page's **statements** run, top to bottom.
5. The **markup** is rendered with the variables the statements left behind:
   `{expressions}`, the `q:loop` and `q:if` inside the markup, `ui:*`
   elements, components called from it.

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

**Shows:** `Total: 3` · `Item a` · `Item c`

The markup only **renders**. It never runs a statement — so a statement placed
inside it would never run, and Quantum refuses it instead of ignoring it:

```xml
<q:component name="Wrong">
  <div>
    <q:set name="x" value="1" />
  </div>
</q:component>
```

**Error:** `never runs (PARSE-2): statements run before the page is rendered`

Move the `q:set` above the markup. For the same reason, a `q:set` inside a
`q:loop` of the markup whose value the rows read is an error: the loop runs for
every item before any row is drawn, so every row would show the last value.
Compute it in the expression instead: `{item.price * item.qty}`.

A page's `q:function`s are available on the whole page, and in its actions,
wherever they are written:

```xml
<q:set name="doubled" value="{double_it(21)}" type="number" />
<q:function name="double_it">
  <q:param name="n" type="number" />
  <q:return value="{n * 2}" />
</q:function>
<q:return value="{doubled}" />
```

**Output:** `42`

## A POST: the action, then a redirect

A form posts to the page with a field `action` that names one of its
`q:action`s. Steps 1–3 run as in a GET; then **only that action** runs — not
the page's statements. It validates its `q:param`s, does its work, and ends in
a `q:redirect`: the browser then asks for the page with a GET, which runs as
above.

Because the page's statements do not run in an action, a variable the page
sets does not exist there:

```xml
<q:component name="Order">
  <q:query name="order" datasource="db">SELECT * FROM orders WHERE id = 7</q:query>

  <q:action name="pay" method="POST">
    <!-- {order} does not exist here: the page's q:query did not run. -->
    <q:query name="order" datasource="db">SELECT * FROM orders WHERE id = 7</q:query>
    <q:query name="paid" datasource="db">UPDATE orders SET paid = 1 WHERE id = {order.id}</q:query>
    <q:redirect url="/order" flash="Paid." />
  </q:action>
  ...
</q:component>
```

The action queries or computes what it needs itself. Using a page variable in
an action is an error whose message says exactly this.

Guards are the exception: they run before the page **and** before each of its
actions, so a guard that redirects also stops the action. That is also why a
guard cannot read a variable the page sets — in the action, it would not exist,
and the guard would let the post through. Guards read scopes (`session.x`)
directly; `require_auth` and `require_role` do the common case for you.

An action that does not end in `q:redirect` answers with the page itself (its
statements run after the action, as in a GET). The response is a 200 to a POST,
and reloading it posts the form again — end actions with `q:redirect`.

## How long things live

| What | Lives | Seen by |
|---|---|---|
| a page variable (`q:set name="x"`) | one request | that request |
| `flash` | the next page, once | that visitor |
| `session.x` | across requests, in the signed session cookie | one visitor |
| `application.x` | while the server process runs | every visitor of that process |

Every request runs in its own runtime, so two requests never see each other's
variables. `application.x` is memory in the server process: it is gone after a
restart, and under `gunicorn --workers 4` each worker has its own. Keep
anything that must last or be shared in the database.
