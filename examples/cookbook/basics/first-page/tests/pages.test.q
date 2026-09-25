<q:test name="index.q answers /" page="/">
  <test:visit />
  <test:expect status="200" text="Hello from Quantum" />
</q:test>

<q:test name="about.q answers /about" page="/about">
  <test:visit />
  <test:expect text="A second page is a second file." />
</q:test>

<q:test name="a URL with no file is 404" page="/contact">
  <test:visit />
  <test:expect status="404" />
</q:test>
