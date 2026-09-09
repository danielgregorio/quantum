<?xml version="1.0" encoding="UTF-8"?>
<q:component xmlns:q="https://quantum.lang/ns" name="test-invoke-http-get">

    <!-- Test 1: Simple HTTP GET request -->
    <q:invoke name="users"
              url="https://jsonplaceholder.typicode.com/users/1"
              method="GET" />

    <!-- Test 2: HTTP GET with query parameters -->
    <q:invoke name="posts"
              url="https://jsonplaceholder.typicode.com/posts"
              method="GET">
        <q:param name="userId" default="1" />
    </q:invoke>

    <!-- Test 3: HTTP GET with custom headers -->
    <q:invoke name="todos"
              url="https://jsonplaceholder.typicode.com/todos/1"
              method="GET">
        <q:header name="Accept" value="application/json" />
        <q:header name="User-Agent" value="QuantumTest/1.0" />
    </q:invoke>

    <q:return value="{users.name} | {posts[0].title} | {todos.title}" />
</q:component>
