<!-- Test Function Simple -->
<q:component name="TestFunctionSimple" xmlns:q="https://quantum.lang/ns">
  <!-- Função simples: adição -->
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />

    <q:set name="result" type="number" value="{a + b}" />
    <q:return value="{result}" />
  </q:function>

  <!-- Chamar função e retornar resultado -->
  <q:set name="sum" value="{add(5, 3)}" />
  <q:return value="Sum: {sum}" />
</q:component>
