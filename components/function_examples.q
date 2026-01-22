<q:component name="FunctionExamples">
  <!--
    🎯 QUANTUM FUNCTIONS - Examples

    This component demonstrates all features of q:function:
    - Basic functions with parameters
    - Functions with default values
    - Cached functions
    - Memoized functions
    - Functions with REST API
    - Functions with conditional logic
    - Functions with loops
    - Functions calling queries
  -->

  <h1>🎯 Quantum Functions Demo</h1>

  <!-- ============================================ -->
  <!-- 1. BASIC FUNCTION WITH PARAMETERS -->
  <!-- ============================================ -->
  <h2>1. Basic Function: Greet</h2>

  <q:function name="greet">
    <q:param name="name" type="string" required="true" />
    <q:param name="greeting" type="string" default="Hello" />
    <q:return value="{greeting}, {name}!" />
  </q:function>

  <div class="example">
    <p>Calling greet("Alice"): <q:call function="greet" name="Alice" /></p>
    <p>Calling greet("Bob", "Hi"): <q:call function="greet" name="Bob" greeting="Hi" /></p>
  </div>

  <!-- ============================================ -->
  <!-- 2. FUNCTION WITH LOGIC: Discount Calculator -->
  <!-- ============================================ -->
  <h2>2. Function with Logic: Calculate Discount</h2>

  <q:function name="calculateDiscount" return="number">
    <q:param name="price" type="number" required="true" />
    <q:param name="percentage" type="number" default="10" />

    <q:set name="discount" value="{price * percentage / 100}" />
    <q:set name="finalPrice" value="{price - discount}" />

    <q:return value="{finalPrice}" />
  </q:function>

  <div class="example">
    <p>$100 with 20% off: $<q:call function="calculateDiscount" price="100" percentage="20" /></p>
    <p>$50 with default 10% off: $<q:call function="calculateDiscount" price="50" /></p>
  </div>

  <!-- ============================================ -->
  <!-- 3. CACHED FUNCTION: Expensive Calculation -->
  <!-- ============================================ -->
  <h2>3. Cached Function (5 min TTL)</h2>

  <q:function name="expensiveCalculation" cache="true" cache_ttl="300">
    <q:param name="n" type="number" required="true" />

    <!-- Simulate expensive operation -->
    <q:set name="result" value="{n * n * n}" />

    <q:return value="Result: {result} (cached for 5 minutes)" />
  </q:function>

  <div class="example">
    <p>First call (slow): <q:call function="expensiveCalculation" n="10" /></p>
    <p>Second call (instant from cache): <q:call function="expensiveCalculation" n="10" /></p>
  </div>

  <!-- ============================================ -->
  <!-- 4. CONDITIONAL FUNCTION: Age Checker -->
  <!-- ============================================ -->
  <h2>4. Function with Conditionals</h2>

  <q:function name="checkAge" return="string">
    <q:param name="age" type="number" required="true" />

    <q:if condition="{age >= 18}">
      <q:return value="Adult" />
    </q:if>
    <q:elseif condition="{age >= 13}">
      <q:return value="Teenager" />
    </q:elseif>
    <q:else>
      <q:return value="Child" />
    </q:else>
  </q:function>

  <div class="example">
    <p>Age 25: <q:call function="checkAge" age="25" /></p>
    <p>Age 15: <q:call function="checkAge" age="15" /></p>
    <p>Age 8: <q:call function="checkAge" age="8" /></p>
  </div>

  <!-- ============================================ -->
  <!-- 5. FUNCTION WITH LOOP: Sum Array -->
  <!-- ============================================ -->
  <h2>5. Function with Loop</h2>

  <q:function name="sumArray" return="number">
    <q:param name="numbers" type="array" required="true" />

    <q:set name="total" value="0" />
    <q:loop type="array" var="num" array="{numbers}">
      <q:set name="total" operation="add" value="{num}" />
    </q:loop>

    <q:return value="{total}" />
  </q:function>

  <div class="example">
    <q:set name="myNumbers" value="[10, 20, 30, 40]" />
    <p>Sum of [10, 20, 30, 40]: <q:call function="sumArray" numbers="{myNumbers}" /></p>
  </div>

  <!-- ============================================ -->
  <!-- 6. MEMOIZED FUNCTION: Fibonacci -->
  <!-- ============================================ -->
  <h2>6. Memoized Function: Fibonacci</h2>

  <q:function name="fibonacci" memoize="true" return="number">
    <q:param name="n" type="number" required="true" />

    <q:if condition="{n <= 1}">
      <q:return value="{n}" />
    </q:if>

    <!-- In real implementation, would call itself recursively -->
    <!-- For demo, just return n * 2 -->
    <q:set name="result" value="{n * 2}" />
    <q:return value="{result}" />
  </q:function>

  <div class="example">
    <p>Fibonacci(10): <q:call function="fibonacci" n="10" /></p>
    <p class="hint">Result is memoized permanently - subsequent calls are instant!</p>
  </div>

  <!-- ============================================ -->
  <!-- 7. PURE FUNCTION: String Formatter -->
  <!-- ============================================ -->
  <h2>7. Pure Function (no side effects)</h2>

  <q:function name="formatName" pure="true">
    <q:param name="firstName" type="string" required="true" />
    <q:param name="lastName" type="string" required="true" />

    <q:set name="formatted" value="{lastName}, {firstName}" />
    <q:return value="{formatted}" />
  </q:function>

  <div class="example">
    <p>Format "John Doe": <q:call function="formatName" firstName="John" lastName="Doe" /></p>
  </div>

  <!-- ============================================ -->
  <!-- 8. FUNCTION WITH QUERY: Get User -->
  <!-- ============================================ -->
  <h2>8. Function with Database Query</h2>

  <q:function name="getUserById" return="object">
    <q:param name="userId" type="number" required="true" />

    <q:query name="user" datasource="db">
      SELECT id, name, email FROM users WHERE id = {userId}
    </q:query>

    <q:if condition="{user.recordCount > 0}">
      <q:return value="{user.records[0]}" />
    </q:if>

    <q:return value="User not found" />
  </q:function>

  <!-- ============================================ -->
  <!-- 9. FUNCTION WITH AI: Smart Summary -->
  <!-- ============================================ -->
  <h2>9. Function with AI/LLM</h2>

  <q:function name="summarizeText" cache="true" cache_ttl="600">
    <q:param name="text" type="string" required="true" />
    <q:param name="maxWords" type="number" default="50" />

    <q:query name="summary" datasource="ai">
      Summarize this text in maximum {maxWords} words:

      {text}
    </q:query>

    <q:return value="{summary}" />
  </q:function>

  <div class="example">
    <q:set name="longText" value="Quantum is a declarative language..." />
    <p>Summary: <q:call function="summarizeText" text="{longText}" maxWords="20" /></p>
  </div>

  <!-- ============================================ -->
  <!-- 10. FUNCTION WITH VALIDATION -->
  <!-- ============================================ -->
  <h2>10. Function with Parameter Validation</h2>

  <q:function name="validateEmail" validate_params="true">
    <q:param name="email" type="string" required="true" validation="email" />

    <!-- If we got here, email is valid -->
    <q:return value="✅ Valid email: {email}" />
  </q:function>

  <div class="example">
    <p>Validate "user@example.com": <q:call function="validateEmail" email="user@example.com" /></p>
  </div>

  <!-- ============================================ -->
  <!-- 11. ASYNC FUNCTION (future feature) -->
  <!-- ============================================ -->
  <h2>11. Async Function (Future)</h2>

  <q:function name="fetchData" async="true" timeout="5000">
    <q:param name="url" type="string" required="true" />

    <!-- Would fetch from external API -->
    <q:return value="Data from {url}" />
  </q:function>

  <!-- ============================================ -->
  <!-- 12. FUNCTION WITH RETRY -->
  <!-- ============================================ -->
  <h2>12. Function with Retry Logic</h2>

  <q:function name="reliableOperation" retry="3" timeout="2000">
    <q:param name="operation" type="string" />

    <!-- If operation fails, will retry up to 3 times -->
    <q:return value="Operation completed: {operation}" />
  </q:function>

  <!-- ============================================ -->
  <!-- STYLING -->
  <!-- ============================================ -->
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      max-width: 1200px;
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
      margin-top: 40px;
      padding: 10px;
      background: #ecf0f1;
      border-left: 4px solid #3498db;
    }

    .example {
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      margin: 20px 0;
    }

    .example p {
      margin: 10px 0;
      padding: 10px;
      background: #f8f9fa;
      border-radius: 4px;
    }

    .hint {
      color: #7f8c8d;
      font-size: 0.9em;
      font-style: italic;
    }

    code {
      background: #282c34;
      color: #abb2bf;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Monaco', 'Menlo', monospace;
    }

    .api-endpoint {
      background: #2ecc71;
      color: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-weight: bold;
      font-size: 0.85em;
    }
  </style>
</q:component>
