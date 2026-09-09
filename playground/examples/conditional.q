<!-- Conditionals -->
<q:component name="Conditionals">
  <q:set name="score" type="number" value="85" />
  <q:set name="name" value="Alice" />

  <h2>Grade Report for {name}</h2>
  <p>Score: {score}</p>

  <q:if condition="score >= 90">
    <p class="grade-a">Grade: A - Excellent!</p>
  </q:if>

  <q:if condition="score >= 80">
    <q:if condition="score < 90">
      <p class="grade-b">Grade: B - Good job!</p>
    </q:if>
  </q:if>

  <q:if condition="score < 80">
    <p class="grade-c">Grade: C or below - Keep practicing!</p>
  </q:if>
</q:component>
