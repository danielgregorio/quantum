<q:component name="Sales">
  <!-- The database is asked once. -->
  <q:query name="sales" datasource="db">
    SELECT region, amount FROM sales ORDER BY id
  </q:query>

  <!-- source="sales": SQL over that result, in memory — the table is
       named after the query. -->
  <q:query name="totals" source="sales">
    SELECT region, SUM(amount) AS total, COUNT(*) AS n
    FROM sales GROUP BY region ORDER BY total DESC
  </q:query>

  <ui:window title="Sales">
    <ui:table source="{totals}">
      <ui:column key="region" label="Region" />
      <ui:column key="total" label="Total" />
      <ui:column key="n" label="Sales" />
    </ui:table>
    <ui:text>{sales_result.recordCount} sales</ui:text>
  </ui:window>
</q:component>
