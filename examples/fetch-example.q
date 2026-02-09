<?xml version="1.0" encoding="UTF-8"?>
<!--
Example: Data Fetching with q:fetch
Demonstrates loading states, error handling, and data display
-->
<q:component xmlns:q="https://quantum.lang/ns" name="FetchExample">
    <!-- Basic GET request with loading states -->
    <q:fetch name="users"
             url="https://jsonplaceholder.typicode.com/users"
             method="GET" />

    <!-- POST request with headers -->
    <q:fetch name="newPost"
             url="https://jsonplaceholder.typicode.com/posts"
             method="POST"
             auto="false">
        <q:header name="Content-Type" value="application/json" />
        <q:body>{postData}</q:body>
    </q:fetch>

    <!-- Fetch with polling (refresh every 30 seconds) -->
    <q:fetch name="liveData"
             url="https://api.example.com/live"
             method="GET"
             poll="30000" />

    <!-- Fetch with cache -->
    <q:fetch name="cachedData"
             url="https://api.example.com/static"
             method="GET"
             cache="300" />

    <div class="container">
        <h1>Data Fetching Examples</h1>

        <!-- Example 1: Basic fetch with loading states -->
        <section>
            <h2>Users List</h2>

            <q:if condition="{users.isLoading}">
                <div class="loading">
                    <span class="spinner"></span>
                    Loading users...
                </div>
            </q:if>

            <q:if condition="{users.error}">
                <div class="error">
                    Error loading users: {users.error}
                </div>
            </q:if>

            <q:if condition="{users.data}">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Company</th>
                        </tr>
                    </thead>
                    <tbody>
                        <q:loop type="array" var="user" items="{users.data}">
                            <tr>
                                <td>{user.name}</td>
                                <td>{user.email}</td>
                                <td>{user.company.name}</td>
                            </tr>
                        </q:loop>
                    </tbody>
                </table>
                <p>Total: {users.data.length} users</p>
            </q:if>
        </section>

        <!-- Example 2: Conditional fetch (POST) -->
        <section>
            <h2>Create Post</h2>

            <form>
                <input type="text" name="title" placeholder="Title" />
                <textarea name="body" placeholder="Content"></textarea>
                <button type="button" onclick="submitPost()">
                    Create Post
                </button>
            </form>

            <q:if condition="{newPost.data}">
                <div class="success">
                    Post created with ID: {newPost.data.id}
                </div>
            </q:if>
        </section>

        <!-- Example 3: Fetch with authentication -->
        <section>
            <h2>Authenticated Request</h2>

            <q:fetch name="profile"
                     url="https://api.example.com/me"
                     method="GET">
                <q:header name="Authorization" value="Bearer {authToken}" />
            </q:fetch>

            <q:if condition="{profile.data}">
                <p>Welcome, {profile.data.name}!</p>
            </q:if>
        </section>
    </div>

    <!-- State for POST request -->
    <q:set name="postData" value="{}" />
    <q:set name="authToken" value="" />

    <!-- Function to handle form submission -->
    <q:function name="submitPost">
        <q:set name="postData" value="{
            'title': form.title,
            'body': form.body,
            'userId': 1
        }" />
        <!-- Trigger the fetch -->
        <q:invoke function="newPost.execute" />
    </q:function>
</q:component>
