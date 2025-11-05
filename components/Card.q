<q:component name="Card">
  <q:param name="title" type="string" required />
  <q:param name="subtitle" type="string" default="" />

  <div class="card">
    <div class="card-header">
      <h3>{title}</h3>
      <q:if condition="{subtitle != ''}">
        <p class="subtitle">{subtitle}</p>
      </q:if>
    </div>
    <div class="card-body">
      <q:slot />
    </div>
  </div>
</q:component>
