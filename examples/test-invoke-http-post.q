<?xml version="1.0" encoding="UTF-8"?>
<q:component xmlns:q="https://quantum.lang/ns" name="test-invoke-http-post">

    <!-- Test: HTTP POST with JSON body -->
    <q:invoke name="newPost"
              url="https://jsonplaceholder.typicode.com/posts"
              method="POST"
              contentType="application/json">
        <q:body>
            {
                "title": "Quantum Test Post",
                "body": "This is a test post created by Quantum",
                "userId": 1
            }
        </q:body>
    </q:invoke>

    <q:return value="Created post #{newPost.id}: {newPost.title}" />
</q:component>
