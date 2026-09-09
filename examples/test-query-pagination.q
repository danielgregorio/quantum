<?xml version="1.0" encoding="UTF-8"?>
<q:component name="test-query-pagination" xmlns:q="https://quantum.lang/ns">
    <!--
    Test: Automatic pagination with COUNT(*) and LIMIT/OFFSET
    Expected: Query auto-paginates, provides pagination metadata
    -->

    <!-- Paginated query - page 1, 5 records per page -->
    <q:query name="paginatedUsers" datasource="test-sqlite"
             paginate="true" page="1" page_size="5">
        SELECT id, name, email, status, created_at
        FROM users
        WHERE status = 'active'
        ORDER BY created_at DESC
    </q:query>

    <!-- Return pagination summary -->
    <q:return value="Page {paginatedUsers_result.pagination.currentPage} of {paginatedUsers_result.pagination.totalPages} | Records {paginatedUsers_result.pagination.startRecord}-{paginatedUsers_result.pagination.endRecord} of {paginatedUsers_result.pagination.totalRecords} | Next: {paginatedUsers_result.pagination.hasNextPage}" />
</q:component>
