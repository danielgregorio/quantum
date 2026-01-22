<q:component name="CompleteDemo">
  <!--
    🎉 COMPLETE QUANTUM DEMO

    This component demonstrates:
    - q:function - Reusable functions with parameters
    - q:call - Function invocation
    - q:on - Event handlers
    - q:dispatch - Event emission
    - REST API auto-generation
  -->

  <h1>🎉 Complete Quantum Feature Demo</h1>

  <!-- ============================================ -->
  <!-- FUNCTIONS -->
  <!-- ============================================ -->
  <section class="feature-section">
    <h2>1. Functions & Calling</h2>

    <!-- Define function -->
    <q:function name="calculateTotal">
      <q:param name="price" type="number" required="true" />
      <q:param name="quantity" type="number" default="1" />
      <q:param name="tax" type="number" default="0.1" />

      <q:set name="subtotal" value="{price * quantity}" />
      <q:set name="taxAmount" value="{subtotal * tax}" />
      <q:set name="total" value="{subtotal + taxAmount}" />

      <q:return value="{total}" />
    </q:function>

    <!-- Call function -->
    <div class="example">
      <p>Price: $100, Quantity: 2, Tax: 10%</p>
      <q:call function="calculateTotal" price="100" quantity="2" tax="0.1" result="finalPrice" />
      <p class="result">Total: ${finalPrice}</p>
    </div>
  </section>

  <!-- ============================================ -->
  <!-- REST API FUNCTIONS -->
  <!-- ============================================ -->
  <section class="feature-section">
    <h2>2. REST API Auto-Generation</h2>

    <!-- Function with REST endpoint -->
    <q:function name="getUserData"
                return="object"
                rest="/api/users/{id}"
                method="GET"
                auth="bearer">
      <q:param name="id" type="number" required="true" />

      <q:query name="user" datasource="db">
        SELECT id, name, email FROM users WHERE id = {id}
      </q:query>

      <q:return value="{user.records[0]}" />
    </q:function>

    <q:function name="createOrder"
                rest="/api/orders"
                method="POST"
                consumes="application/json"
                produces="application/json"
                status="201">
      <q:param name="userId" type="number" required="true" />
      <q:param name="items" type="array" required="true" />
      <q:param name="total" type="number" required="true" />

      <q:query name="order" datasource="db">
        INSERT INTO orders (user_id, items, total, created_at)
        VALUES ({userId}, {items}, {total}, NOW())
        RETURNING id
      </q:query>

      <!-- Dispatch event when order created -->
      <q:dispatch event="orderCreated" data="{order}" />

      <q:return value='{{"orderId": {order.id}, "status": "created"}}' />
    </q:function>

    <div class="api-docs">
      <h3>Auto-Generated Endpoints:</h3>
      <ul>
        <li><span class="method get">GET</span> /api/users/{id}</li>
        <li><span class="method post">POST</span> /api/orders</li>
      </ul>
      <p class="hint">These endpoints are automatically created from functions!</p>
    </div>
  </section>

  <!-- ============================================ -->
  <!-- EVENT SYSTEM -->
  <!-- ============================================ -->
  <section class="feature-section">
    <h2>3. Event System (q:on / q:dispatch)</h2>

    <!-- Event handler function -->
    <q:function name="handleOrderCreated">
      <q:param name="eventData" type="object" />

      <q:set name="orderId" value="{eventData.id}" />

      <!-- Send email notification -->
      <q:set name="emailSent" value="true" />

      <!-- Log order -->
      <q:log message="Order {orderId} created successfully" level="info" />

      <q:return value="Event handled" />
    </q:function>

    <!-- Register event handler -->
    <q:on event="orderCreated" function="handleOrderCreated" />

    <!-- Register inline event handler -->
    <q:on event="userLogin" once="true">
      <q:set name="loginCount" value="{loginCount + 1}" />
      <q:log message="User logged in (count: {loginCount})" />
    </q:on>

    <!-- Event handler with debounce -->
    <q:on event="searchInput" debounce="300">
      <q:set name="searchTerm" value="{eventData.value}" />
      <q:query name="results" datasource="db">
        SELECT * FROM products WHERE name LIKE '%{searchTerm}%'
      </q:query>
    </q:on>

    <!-- Demo: Dispatch events -->
    <div class="example">
      <button onclick="dispatchQuantumEvent('orderCreated', {id: 123})">
        Create Order (Dispatch Event)
      </button>

      <button onclick="dispatchQuantumEvent('userLogin', {userId: 456})">
        Login User
      </button>

      <input type="text"
             placeholder="Search..."
             oninput="dispatchQuantumEvent('searchInput', {value: this.value})" />
    </div>
  </section>

  <!-- ============================================ -->
  <!-- COMPLETE WORKFLOW: Functions + Events + REST -->
  <!-- ============================================ -->
  <section class="feature-section">
    <h2>4. Complete Workflow Example</h2>

    <!-- Workflow function -->
    <q:function name="processCheckout"
                rest="/api/checkout"
                method="POST"
                cache="false">
      <q:param name="userId" type="number" required="true" />
      <q:param name="items" type="array" required="true" />

      <!-- 1. Calculate total -->
      <q:set name="subtotal" value="0" />
      <q:loop type="array" var="item" array="{items}">
        <q:set name="itemTotal" value="{item.price * item.quantity}" />
        <q:set name="subtotal" operation="add" value="{itemTotal}" />
      </q:loop>

      <!-- 2. Call discount function -->
      <q:call function="calculateDiscount"
              userId="{userId}"
              total="{subtotal}"
              result="discount" />

      <!-- 3. Calculate final -->
      <q:call function="calculateTotal"
              price="{subtotal - discount}"
              tax="0.1"
              result="finalTotal" />

      <!-- 4. Create order -->
      <q:query name="order" datasource="db">
        INSERT INTO orders (user_id, subtotal, discount, total)
        VALUES ({userId}, {subtotal}, {discount}, {finalTotal})
        RETURNING id
      </q:query>

      <!-- 5. Dispatch event -->
      <q:dispatch event="checkoutCompleted"
                  bubbles="true"
                  cancelable="false">
        <data key="orderId" value="{order.id}" />
        <data key="total" value="{finalTotal}" />
        <data key="userId" value="{userId}" />
      </q:dispatch>

      <!-- 6. Return result -->
      <q:return value='{
        "success": true,
        "orderId": {order.id},
        "total": {finalTotal},
        "discount": {discount}
      }' />
    </q:function>

    <!-- Event handler for checkout completion -->
    <q:on event="checkoutCompleted" function="sendOrderConfirmation" />

    <q:function name="sendOrderConfirmation">
      <q:param name="eventData" type="object" />

      <q:set name="orderId" value="{eventData.orderId}" />
      <q:set name="userId" value="{eventData.userId}" />

      <!-- Send email (simplified) -->
      <q:log message="Sending confirmation for order {orderId} to user {userId}" />

      <q:return value="Confirmation sent" />
    </q:function>
  </section>

  <!-- ============================================ -->
  <!-- JavaScript Helper (for demo) -->
  <!-- ============================================ -->
  <q:script>
    function dispatchQuantumEvent(eventName, data) {
      // In real implementation, this would integrate with Quantum's EventBus
      console.log('Dispatching event:', eventName, data);

      // Simulate event dispatch
      const event = new CustomEvent(eventName, {
        detail: data,
        bubbles: true,
        cancelable: true
      });

      document.dispatchEvent(event);
    }
  </q:script>

  <!-- ============================================ -->
  <!-- STYLING -->
  <!-- ============================================ -->
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      max-width: 1400px;
      margin: 0 auto;
      padding: 20px;
      background: #f8f9fa;
    }

    h1 {
      color: #2c3e50;
      text-align: center;
      border-bottom: 4px solid #3498db;
      padding-bottom: 15px;
      margin-bottom: 40px;
    }

    .feature-section {
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      margin-bottom: 30px;
    }

    .feature-section h2 {
      color: #34495e;
      border-left: 4px solid #3498db;
      padding-left: 15px;
      margin-bottom: 25px;
    }

    .example {
      background: #f8f9fa;
      padding: 20px;
      border-radius: 8px;
      margin: 20px 0;
      border-left: 4px solid #2ecc71;
    }

    .result {
      font-size: 1.2em;
      font-weight: bold;
      color: #2ecc71;
    }

    .api-docs {
      background: #ecf0f1;
      padding: 20px;
      border-radius: 8px;
      margin-top: 20px;
    }

    .api-docs h3 {
      margin-top: 0;
      color: #34495e;
    }

    .api-docs ul {
      list-style: none;
      padding: 0;
    }

    .api-docs li {
      padding: 10px;
      margin: 8px 0;
      background: white;
      border-radius: 6px;
    }

    .method {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 4px;
      font-weight: bold;
      font-size: 0.85em;
      margin-right: 10px;
      min-width: 60px;
      text-align: center;
      color: white;
    }

    .method.get {
      background: #2ecc71;
    }

    .method.post {
      background: #3498db;
    }

    button {
      background: #3498db;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 1em;
      margin: 5px;
      transition: background 0.3s;
    }

    button:hover {
      background: #2980b9;
    }

    input[type="text"] {
      padding: 12px;
      border: 2px solid #ecf0f1;
      border-radius: 6px;
      font-size: 1em;
      width: 300px;
      margin: 5px;
    }

    input[type="text"]:focus {
      outline: none;
      border-color: #3498db;
    }

    .hint {
      color: #7f8c8d;
      font-style: italic;
      font-size: 0.9em;
      margin-top: 10px;
    }

    code {
      background: #282c34;
      color: #abb2bf;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 0.9em;
    }
  </style>
</q:component>
