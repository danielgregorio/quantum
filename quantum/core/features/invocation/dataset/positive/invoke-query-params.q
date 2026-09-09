<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: HTTP GET with query parameters
Tests: Query parameter binding in URL
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-query-params">
    <q:invoke name="userPosts"
              url="https://jsonplaceholder.typicode.com/posts"
              method="GET">
        <q:param name="userId" default="1" />
        <q:param name="_limit" default="5" />
    </q:invoke>

    <q:return value="Found {userPosts.length} posts for user 1" />
</q:component>
