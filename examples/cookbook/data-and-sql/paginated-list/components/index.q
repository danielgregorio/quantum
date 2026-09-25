<q:component name="Posts">
  <!-- paginate: the page is the URL's ?page= (page 1 without it). -->
  <q:query name="posts" datasource="db" paginate="true" page_size="10">
    SELECT id, title FROM posts ORDER BY id DESC
  </q:query>

  <ui:window title="Posts">
    <ui:text>
      {posts_result.pagination.startRecord}–{posts_result.pagination.endRecord}
      of {posts_result.pagination.totalRecords}
    </ui:text>
    <ui:list source="{posts}" as="p">
      <ui:item><ui:text>{p.title}</ui:text></ui:item>
    </ui:list>
    <!-- Previous, the page numbers, next — keeping the URL's other parameters. -->
    <ui:pager for="posts" />
  </ui:window>
</q:component>
