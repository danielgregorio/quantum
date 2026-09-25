<q:component name="Search">
  <!-- query.<name> is the address's ?name=; a missing one is empty. -->
  <q:set name="q" value="{query.q}" default="" />
  <q:set name="order" value="{query.order}" default="az" />
  <q:set name="words" type="array" value='["pear", "apple", "plum", "peach", "fig"]' />
  <q:set name="words" value="{sort(words, order == 'za')}" />

  <html>
  <body>
    <form method="GET">
      <input name="q" value="{q}" />
      <button>Search</button>
    </form>
    <p>Results for "{q}", sorted {order}:</p>
    <ul>
      <q:loop type="array" var="w" items="{words}">
        <q:if condition="contains(w, lower(q))">
          <li>{w}</li>
        </q:if>
      </q:loop>
    </ul>
    <!-- urlencode keeps a typed value safe inside a link. -->
    <a href="/?q={urlencode(q)}&amp;order=za">Z to A</a>
  </body>
  </html>
</q:component>
