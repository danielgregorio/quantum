<q:component name="Card">
  <!-- Props are q:params; the caller's content goes where q:slot is. -->
  <q:param name="title" type="string" required="true" />
  <q:param name="tone" type="string" default="plain" />

  <section class="card card-{tone}">
    <h2>{title}</h2>
    <div class="card-body">
      <q:slot />
    </div>
  </section>
</q:component>
