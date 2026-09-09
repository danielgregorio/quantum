<q:component name="HTMXSearch">
  <!-- Phase B: HTMX Partial - Live search results -->

  <q:action name="search" method="POST">
    <q:param name="search" type="string" />
  </q:action>

  <q:set name="searchQuery" value="{form.search}" default="" />

  <q:if condition="{searchQuery} == ''">
    <p class="muted">Type something to search...</p>
  </q:if>

  <q:if condition="{searchQuery} != ''">
    <div class="search-result">
      <strong>🔍 Result 1:</strong> Found "{searchQuery}" in Product Database
    </div>

    <div class="search-result">
      <strong>🔍 Result 2:</strong> "{searchQuery}" matches in User Records
    </div>

    <div class="search-result">
      <strong>🔍 Result 3:</strong> Documentation for "{searchQuery}"
    </div>

    <p style="margin-top: 15px; color: #7f8c8d; font-size: 0.9rem;">
      Found 3 results for: <strong>{searchQuery}</strong>
    </p>
  </q:if>
</q:component>
