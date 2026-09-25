<q:component name="Booking">
  <q:action name="book" method="POST">
    <q:param name="name" required="true" minlength="2" />
    <q:param name="nights" type="integer" required="true" min="1" max="14" />
    <q:param name="room" enum="single,double,suite" default="double" />
    <q:param name="breakfast" type="boolean" default="false" />
    <q:param name="arrival" enum="morning,afternoon,night" default="afternoon" />
    <q:param name="notes" maxlength="300" default="" />
    <q:redirect url="/" flash="{name}: {nights} nights, {room}, breakfast {'yes' if breakfast else 'no'}, {arrival}." />
  </q:action>

  <ui:window title="Book a room">
    <ui:vbox gap="md" padding="lg" width="480">
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
      </q:if>
      <!-- ui:formitem puts a label next to its field. The fields take their
           rules (and the lists of choices) from the action's q:params. -->
      <ui:form on-submit="book" submit="Book">
        <ui:formitem label="Name"><ui:input bind="name" /></ui:formitem>
        <ui:formitem label="Nights"><ui:input bind="nights" /></ui:formitem>
        <ui:formitem label="Room">
          <ui:select bind="room">
            <ui:option value="single">Single</ui:option>
            <ui:option value="double">Double</ui:option>
            <ui:option value="suite">Suite</ui:option>
          </ui:select>
        </ui:formitem>
        <ui:switch bind="breakfast" label="Breakfast" />
        <ui:formitem label="Arrival"><ui:radio bind="arrival" /></ui:formitem>
        <ui:formitem label="Notes"><ui:input bind="notes" rows="3" /></ui:formitem>
      </ui:form>
    </ui:vbox>
  </ui:window>
</q:component>
