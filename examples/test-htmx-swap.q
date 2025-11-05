<q:component name="TestHtmxSwap">
  <!-- Test: HTMX swap strategies -->

  <q:set name="message" value="New item" />

  <!-- innerHTML: replace content -->
  <div hx-get="/_partial/TestHtmxSwap"
       hx-trigger="click"
       hx-swap="innerHTML">
    Click to replace content
  </div>

  <!-- outerHTML: replace element -->
  <div hx-get="/_partial/TestHtmxSwap"
       hx-trigger="click"
       hx-swap="outerHTML">
    Click to replace element
  </div>

  <!-- beforeend: append to end -->
  <ul id="list">
    <li hx-get="/_partial/TestHtmxSwap"
        hx-trigger="click"
        hx-target="#list"
        hx-swap="beforeend">
      Add item
    </li>
  </ul>

  <!-- Expected: Different swap strategies work -->
  {message}
</q:component>
