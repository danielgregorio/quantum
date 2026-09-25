<q:test name="no ?q= shows everything, sorted by the default" page="/">
  <test:visit />
  <test:expect text="Results for &quot;&quot;, sorted az: apple fig peach pear plum" />
  <test:expect var="order" value="az" />
</q:test>

<q:test name="?q= filters" page="/?q=PE">
  <test:visit />
  <test:expect text="peach pear" />
  <test:expect no-text="plum" />
</q:test>

<q:test name="two parameters at once" page="/?q=p&amp;order=za">
  <test:visit />
  <test:expect text="plum pear peach apple" />
</q:test>
