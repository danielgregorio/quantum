<q:component name="Button">
  <q:param name="label" type="string" required />
  <q:param name="color" type="string" default="blue" />
  <q:param name="size" type="string" default="medium" />

  <button class="btn btn-{color} btn-{size}">
    {label}
  </button>
</q:component>
