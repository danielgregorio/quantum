<q:component name="Plans">
  <q:set name="plans" type="array"
         value='[{"name": "Free", "price": 0, "seats": 1}, {"name": "Team", "price": 12, "seats": 10}, {"name": "Company", "price": 40, "seats": 100}]' />

  <ui:window title="Plans">
    <!-- Three columns; the grid wraps on a narrow screen. -->
    <ui:grid columns="3" gap="md" padding="lg">
      <q:loop type="array" var="plan" items="{plans}">
        <ui:card>
          <ui:card-header>
            <ui:text weight="bold">{plan.name}</ui:text>
          </ui:card-header>
          <ui:card-body>
            <ui:text>${plan.price} a month</ui:text>
            <ui:text>Up to {plan.seats} people</ui:text>
          </ui:card-body>
          <ui:card-footer>
            <ui:link to="/signup?plan={plan.name}">Choose {plan.name}</ui:link>
          </ui:card-footer>
        </ui:card>
      </q:loop>
    </ui:grid>
    <!-- A card with only a title and text needs no parts. -->
    <ui:card title="Not sure?" padding="lg">
      <ui:text>Every plan starts with 30 free days.</ui:text>
    </ui:card>
  </ui:window>
</q:component>
