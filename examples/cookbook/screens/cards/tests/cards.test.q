<q:test name="one card per plan, with its three parts" page="/">
  <test:visit />
  <test:expect text="Free $0 a month Up to 1 people Choose Free" />
  <test:expect text="Company $40 a month Up to 100 people Choose Company" />
</q:test>

<q:test name="a card with a title only" page="/">
  <test:visit />
  <test:expect text="Not sure? Every plan starts with 30 free days." />
</q:test>
