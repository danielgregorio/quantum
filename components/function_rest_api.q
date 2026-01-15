<q:component name="FunctionRestAPI">
  <!--
    🚀 QUANTUM FUNCTIONS - REST API Example

    Shows how to create REST endpoints using q:function with rest attribute.

    Each function becomes an HTTP endpoint automatically!
  -->

  <h1>🚀 REST API with Functions</h1>

  <div class="info-box">
    <h2>API Endpoints Available:</h2>
    <ul>
      <li><span class="method get">GET</span> <code>/api/users/{id}</code> - Get user by ID</li>
      <li><span class="method post">POST</span> <code>/api/users</code> - Create new user</li>
      <li><span class="method put">PUT</span> <code>/api/users/{id}</code> - Update user</li>
      <li><span class="method delete">DELETE</span> <code>/api/users/{id}</code> - Delete user</li>
      <li><span class="method get">GET</span> <code>/api/products</code> - List products</li>
      <li><span class="method post">POST</span> <code>/api/calculate</code> - Calculate total</li>
    </ul>
  </div>

  <!-- ============================================ -->
  <!-- 1. GET ENDPOINT: Get User -->
  <!-- ============================================ -->
  <q:function name="getUser"
              return="object"
              rest="/api/users/{id}"
              method="GET"
              auth="bearer"
              produces="application/json">
    <q:param name="id" type="number" required="true" />

    <q:query name="user" datasource="db">
      SELECT id, name, email, created_at FROM users WHERE id = {id}
    </q:query>

    <q:if condition="{user.recordCount == 0}">
      <q:return value='{"error": "User not found", "status": 404}' />
    </q:if>

    <q:return value="{user.records[0]}" />
  </q:function>

  <!-- ============================================ -->
  <!-- 2. POST ENDPOINT: Create User -->
  <!-- ============================================ -->
  <q:function name="createUser"
              return="object"
              rest="/api/users"
              method="POST"
              consumes="application/json"
              produces="application/json"
              validate_params="true"
              status="201">
    <q:param name="name" type="string" required="true" />
    <q:param name="email" type="string" required="true" validation="email" />
    <q:param name="password" type="string" required="true" />

    <!-- Hash password (simplified) -->
    <q:set name="hashedPassword" value="{password}" />

    <!-- Insert into database -->
    <q:query name="result" datasource="db">
      INSERT INTO users (name, email, password, created_at)
      VALUES ({name}, {email}, {hashedPassword}, NOW())
      RETURNING id
    </q:query>

    <q:set name="newUserId" value="{result.records[0].id}" />

    <q:return value='{"id": {newUserId}, "name": "{name}", "email": "{email}", "message": "User created successfully"}' />
  </q:function>

  <!-- ============================================ -->
  <!-- 3. PUT ENDPOINT: Update User -->
  <!-- ============================================ -->
  <q:function name="updateUser"
              return="object"
              rest="/api/users/{id}"
              method="PUT"
              auth="bearer"
              validate_params="true">
    <q:param name="id" type="number" required="true" />
    <q:param name="name" type="string" />
    <q:param name="email" type="string" validation="email" />

    <!-- Check if user exists -->
    <q:query name="existing" datasource="db">
      SELECT id FROM users WHERE id = {id}
    </q:query>

    <q:if condition="{existing.recordCount == 0}">
      <q:return value='{"error": "User not found", "status": 404}' />
    </q:if>

    <!-- Update user -->
    <q:query name="update" datasource="db">
      UPDATE users
      SET name = COALESCE({name}, name),
          email = COALESCE({email}, email),
          updated_at = NOW()
      WHERE id = {id}
    </q:query>

    <q:return value='{"id": {id}, "message": "User updated successfully"}' />
  </q:function>

  <!-- ============================================ -->
  <!-- 4. DELETE ENDPOINT: Delete User -->
  <!-- ============================================ -->
  <q:function name="deleteUser"
              return="object"
              rest="/api/users/{id}"
              method="DELETE"
              auth="bearer"
              roles="admin"
              status="204">
    <q:param name="id" type="number" required="true" />

    <!-- Delete user (only admins can do this) -->
    <q:query name="delete" datasource="db">
      DELETE FROM users WHERE id = {id}
    </q:query>

    <q:return value='{"message": "User deleted successfully"}' />
  </q:function>

  <!-- ============================================ -->
  <!-- 5. GET ENDPOINT: List Products (with cache) -->
  <!-- ============================================ -->
  <q:function name="listProducts"
              return="array"
              rest="/api/products"
              method="GET"
              cache="true"
              cache_ttl="300">
    <q:param name="category" type="string" />
    <q:param name="limit" type="number" default="50" />
    <q:param name="offset" type="number" default="0" />

    <q:if condition="{category}">
      <q:query name="products" datasource="db">
        SELECT id, name, price, category, stock
        FROM products
        WHERE category = {category}
        LIMIT {limit} OFFSET {offset}
      </q:query>
    </q:if>
    <q:else>
      <q:query name="products" datasource="db">
        SELECT id, name, price, category, stock
        FROM products
        LIMIT {limit} OFFSET {offset}
      </q:query>
    </q:else>

    <q:return value="{products.records}" />
  </q:function>

  <!-- ============================================ -->
  <!-- 6. POST ENDPOINT: Calculate Total (no auth) -->
  <!-- ============================================ -->
  <q:function name="calculateTotal"
              return="object"
              rest="/api/calculate"
              method="POST"
              consumes="application/json">
    <q:param name="items" type="array" required="true" />
    <q:param name="taxRate" type="number" default="0.1" />

    <q:set name="subtotal" value="0" />

    <q:loop type="array" var="item" array="{items}">
      <q:set name="itemTotal" value="{item.price * item.quantity}" />
      <q:set name="subtotal" operation="add" value="{itemTotal}" />
    </q:loop>

    <q:set name="tax" value="{subtotal * taxRate}" />
    <q:set name="total" value="{subtotal + tax}" />

    <q:return value='{
      "subtotal": {subtotal},
      "tax": {tax},
      "total": {total},
      "itemCount": {items.length}
    }' />
  </q:function>

  <!-- ============================================ -->
  <!-- 7. GET ENDPOINT: Search (with RAG) -->
  <!-- ============================================ -->
  <q:function name="searchDocs"
              return="object"
              rest="/api/search"
              method="GET"
              cache="true"
              cache_ttl="600">
    <q:param name="q" type="string" required="true" />
    <q:param name="limit" type="number" default="5" />

    <!-- Semantic search in knowledge base -->
    <q:query name="results" datasource="knowledge_base" top_k="{limit}">
      {q}
    </q:query>

    <!-- Generate AI summary of results -->
    <q:query name="summary" datasource="ai">
      Based on these search results:
      {results}

      Question: {q}

      Provide a concise answer.
    </q:query>

    <q:return value='{
      "query": "{q}",
      "answer": "{summary}",
      "sources": {results.results},
      "count": {results.count}
    }' />
  </q:function>

  <!-- ============================================ -->
  <!-- 8. POST ENDPOINT: Rate Limited -->
  <!-- ============================================ -->
  <q:function name="sendEmail"
              return="object"
              rest="/api/email/send"
              method="POST"
              auth="apikey"
              rate_limit="10/minute"
              retry="3"
              timeout="10000">
    <q:param name="to" type="string" required="true" validation="email" />
    <q:param name="subject" type="string" required="true" />
    <q:param name="body" type="string" required="true" />

    <!-- Send email (would integrate with email service) -->
    <q:set name="emailId" value="123" />

    <q:return value='{
      "id": {emailId},
      "status": "sent",
      "to": "{to}",
      "message": "Email sent successfully"
    }' />
  </q:function>

  <!-- ============================================ -->
  <!-- Documentation Section -->
  <!-- ============================================ -->
  <div class="docs">
    <h2>📖 API Documentation</h2>

    <div class="endpoint-doc">
      <h3>Authentication</h3>
      <p>Most endpoints require authentication. Include your token in the Authorization header:</p>
      <pre>Authorization: Bearer your_token_here</pre>
    </div>

    <div class="endpoint-doc">
      <h3>Example Requests</h3>

      <h4>Get User:</h4>
      <pre>curl -X GET http://localhost:8000/api/users/123 \
  -H "Authorization: Bearer token"</pre>

      <h4>Create User:</h4>
      <pre>curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com", "password": "secret"}'</pre>

      <h4>Calculate Total:</h4>
      <pre>curl -X POST http://localhost:8000/api/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"price": 10.00, "quantity": 2},
      {"price": 5.50, "quantity": 3}
    ],
    "taxRate": 0.1
  }'</pre>

      <h4>Search Docs:</h4>
      <pre>curl -X GET "http://localhost:8000/api/search?q=authentication&limit=3"</pre>
    </div>

    <div class="endpoint-doc">
      <h3>Response Format</h3>
      <p>All endpoints return JSON:</p>
      <pre>{
  "data": { ... },
  "status": 200,
  "message": "Success"
}</pre>
    </div>

    <div class="endpoint-doc">
      <h3>Error Handling</h3>
      <p>Errors are returned with appropriate HTTP status codes:</p>
      <ul>
        <li><code>400</code> - Bad Request (validation failed)</li>
        <li><code>401</code> - Unauthorized (missing/invalid token)</li>
        <li><code>403</code> - Forbidden (insufficient permissions)</li>
        <li><code>404</code> - Not Found</li>
        <li><code>429</code> - Too Many Requests (rate limit exceeded)</li>
        <li><code>500</code> - Internal Server Error</li>
      </ul>
    </div>
  </div>

  <!-- ============================================ -->
  <!-- STYLING -->
  <!-- ============================================ -->
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      max-width: 1400px;
      margin: 0 auto;
      padding: 20px;
      background: #f5f5f5;
    }

    h1 {
      color: #2c3e50;
      border-bottom: 4px solid #3498db;
      padding-bottom: 10px;
    }

    h2 {
      color: #34495e;
      margin-top: 30px;
    }

    .info-box {
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      margin: 20px 0;
    }

    .info-box ul {
      list-style: none;
      padding: 0;
    }

    .info-box li {
      padding: 10px;
      margin: 8px 0;
      background: #f8f9fa;
      border-radius: 4px;
      border-left: 4px solid #3498db;
    }

    .method {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 3px;
      font-weight: bold;
      font-size: 0.85em;
      margin-right: 10px;
      min-width: 60px;
      text-align: center;
    }

    .method.get {
      background: #2ecc71;
      color: white;
    }

    .method.post {
      background: #3498db;
      color: white;
    }

    .method.put {
      background: #f39c12;
      color: white;
    }

    .method.delete {
      background: #e74c3c;
      color: white;
    }

    .docs {
      background: white;
      padding: 30px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      margin-top: 40px;
    }

    .endpoint-doc {
      margin: 30px 0;
      padding-bottom: 20px;
      border-bottom: 1px solid #ecf0f1;
    }

    .endpoint-doc:last-child {
      border-bottom: none;
    }

    pre {
      background: #282c34;
      color: #abb2bf;
      padding: 15px;
      border-radius: 6px;
      overflow-x: auto;
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 0.9em;
    }

    code {
      background: #282c34;
      color: #abb2bf;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 0.9em;
    }

    h4 {
      color: #7f8c8d;
      margin-top: 20px;
      margin-bottom: 10px;
    }
  </style>
</q:component>
