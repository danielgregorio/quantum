<?xml version="1.0" encoding="UTF-8"?>
<!--
Positive Example: HTTP POST with JSON body
Tests: REST API invocation with body payload
-->
<q:component xmlns:q="https://quantum.lang/ns" name="invoke-http-post-json">
    <q:invoke name="newPost"
              url="https://jsonplaceholder.typicode.com/posts"
              method="POST"
              contentType="application/json">
        <q:body>
            {
                "title": "Test Post",
                "body": "Post content",
                "userId": 1
            }
        </q:body>
    </q:invoke>

    <q:return value="Post #{newPost.id} created" />
</q:component>
