# Recursive Intent System: `<q:intent>` Tag

**Date:** 2025-01-01
**Status:** 🎯 Vision Document
**Implementation:** Future Phase (After Core Stabilization)

---

## 🌟 The Vision

### Revolutionary Concept

**Traditional Development:**
```
Write code → Find bugs → Refactor → Add features → Repeat
```

**Quantum Recursive Intent System:**
```
Describe what you want → System generates/adapts everything
```

### The `<q:intent>` Tag

A special Quantum tag that allows developers to **describe improvements, fixes, or new capabilities in natural language**, and the system **automatically generates and integrates** the necessary code.

---

## 📝 Core Concept

### Inline Intent Declaration

```xml
<q:function name="login" restEndpoint="POST /auth/login">
  <q:param name="email" type="string" required="true" />
  <q:param name="password" type="string" required="true" />

  <!-- Existing implementation -->
  <q:database-query table="users" where="email = {email}" var="user" />

  <q:if condition="{user == null}">
    <q:return status="401" value="Invalid credentials" />
  </q:if>

  <!-- ✨ INTENT: Developer describes desired improvement -->
  <q:intent>
    After 3 failed login attempts from the same IP,
    block that IP for 15 minutes and send an alert email to the user
  </q:intent>

  <!-- System automatically generates and integrates the necessary features -->

  <q:verify-password hash="{user.password}" input="{password}" var="isValid" />

  <q:if condition="{!isValid}">
    <q:return status="401" value="Invalid credentials" />
  </q:if>

  <q:generate-token user="{user}" var="token" />
  <q:return value="{token}" status="200" />
</q:function>
```

---

## 🔄 How It Works

### Processing Pipeline

```
┌─────────────────────────────────────────────────┐
│  1. Developer Writes <q:intent>                 │
│     Natural language description of desire      │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  2. Context Analysis                            │
│     - What function is this in?                 │
│     - What variables are available?             │
│     - What database tables exist?               │
│     - What features are already available?      │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  3. Intent Decomposition (LLM)                  │
│     Break down intent into capabilities:        │
│     - Track failed login attempts               │
│     - Identify user by IP address               │
│     - Count attempts per IP                     │
│     - Block IP temporarily                      │
│     - Send email notification                   │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  4. Capability Gap Analysis                     │
│     Check feature registry:                     │
│     ✅ rate_limiting → Missing (generate)       │
│     ✅ email_notifications → Missing (generate) │
│     ✅ ip_tracking → Missing (generate)         │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  5. Feature Generation                          │
│     Generate complete features:                 │
│     - AST nodes                                 │
│     - Parser logic                              │
│     - Runtime execution                         │
│     - Database schemas                          │
│     - Tests                                     │
│     - Documentation                             │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  6. Code Integration                            │
│     Insert generated code into function:        │
│     - Add IP extraction                         │
│     - Add rate limit checks                     │
│     - Add email sending                         │
│     - Maintain code flow logic                  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  7. Validation                                  │
│     - Run tests (existing + generated)          │
│     - Check syntax correctness                  │
│     - Verify intent fulfillment                 │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  8. Apply or Review                             │
│     - Auto-apply if confidence high             │
│     - Present for review if complex             │
│     - Show diff of changes                      │
└─────────────────────────────────────────────────┘
```

---

## 🎯 Use Cases

### Use Case 1: Security Enhancement

**Scenario:** Developer realizes login needs brute-force protection

```xml
<q:function name="login">
  <q:param name="email" type="string" required="true" />
  <q:param name="password" type="string" required="true" />

  <q:intent>
    Add rate limiting: max 5 login attempts per hour per IP.
    After limit, return 429 status with retry-after header.
  </q:intent>

  <!-- System generates rate_limiting feature if doesn't exist -->
  <!-- Auto-integrates rate limit checks before authentication -->
</q:function>
```

**Generated Output:**
```xml
<q:function name="login">
  <q:param name="email" type="string" required="true" />
  <q:param name="password" type="string" required="true" />

  <!-- ✨ AUTO-GENERATED -->
  <q:set name="clientIP" value="{request.ip}" />
  <q:rate-limit
    key="{clientIP}:login"
    max="5"
    window="1h"
    var="rateLimitStatus"
  />

  <q:if condition="{rateLimitStatus.exceeded}">
    <q:return
      status="429"
      headers="{retry-after: {rateLimitStatus.retryAfter}}"
      value="Too many login attempts"
    />
  </q:if>

  <!-- Original authentication logic continues -->
  <q:database-query table="users" where="email = {email}" var="user" />
  <!-- ... -->
</q:function>
```

---

### Use Case 2: Performance Optimization

**Scenario:** Developer notices slow database query

```xml
<q:function name="getUserOrders">
  <q:param name="userId" type="string" />

  <q:database-query
    table="orders"
    where="user_id = {userId}"
    var="orders"
  />

  <q:intent>
    This query is slow when users have 1000+ orders.
    Add pagination (page size 50) and cache results for 5 minutes.
  </q:intent>

  <q:return value="{orders}" />
</q:function>
```

**Generated Output:**
```xml
<q:function name="getUserOrders">
  <q:param name="userId" type="string" required="true" />
  <q:param name="page" type="number" default="1" />
  <q:param name="pageSize" type="number" default="50" />

  <!-- ✨ AUTO-GENERATED: Cache check -->
  <q:cache-get
    key="user_orders:{userId}:page:{page}"
    var="cachedOrders"
  />

  <q:if condition="{cachedOrders != null}">
    <q:return value="{cachedOrders}" />
  </q:if>

  <!-- ✨ AUTO-GENERATED: Paginated query -->
  <q:set name="offset" value="{(page - 1) * pageSize}" />
  <q:database-query
    table="orders"
    where="user_id = {userId}"
    limit="{pageSize}"
    offset="{offset}"
    var="orders"
  />

  <!-- ✨ AUTO-GENERATED: Cache set -->
  <q:cache-set
    key="user_orders:{userId}:page:{page}"
    value="{orders}"
    ttl="5m"
  />

  <q:return value="{orders}" />
</q:function>
```

---

### Use Case 3: Bug Fix

**Scenario:** Developer discovers rounding error

```xml
<q:function name="calculateDiscount">
  <q:param name="price" type="number" />
  <q:param name="discountPercent" type="number" />

  <q:set name="discountAmount" value="{price * (discountPercent / 100)}" />
  <q:set name="finalPrice" value="{price - discountAmount}" />

  <q:intent>
    Bug: Final price shows too many decimals (e.g., 19.999999).
    Round to 2 decimal places for currency.
  </q:intent>

  <q:return value="{finalPrice}" />
</q:function>
```

**Generated Output:**
```xml
<q:function name="calculateDiscount">
  <q:param name="price" type="number" />
  <q:param name="discountPercent" type="number" />

  <q:set name="discountAmount" value="{price * (discountPercent / 100)}" />
  <!-- ✨ AUTO-FIXED: Added round() -->
  <q:set name="finalPrice" value="{round(price - discountAmount, 2)}" />

  <q:return value="{finalPrice}" />
</q:function>
```

---

### Use Case 4: Feature Addition

**Scenario:** Product manager requests audit logging

```xml
<q:function name="deleteUser">
  <q:param name="userId" type="string" />

  <q:database-delete table="users" where="id = {userId}" />

  <q:intent>
    For compliance, log all user deletions with timestamp,
    admin who performed action, and reason.
  </q:intent>

  <q:return status="204" />
</q:function>
```

**Generated Output:**
```xml
<q:function name="deleteUser">
  <q:param name="userId" type="string" required="true" />
  <q:param name="reason" type="string" required="true" />

  <!-- ✨ AUTO-GENERATED: Get admin context -->
  <q:set name="adminId" value="{session.user.id}" />
  <q:set name="timestamp" value="{now()}" />

  <!-- ✨ AUTO-GENERATED: Fetch user data for audit -->
  <q:database-query table="users" where="id = {userId}" var="user" />

  <q:database-delete table="users" where="id = {userId}" />

  <!-- ✨ AUTO-GENERATED: Audit log -->
  <q:audit-log
    action="user_deletion"
    entity="{user}"
    performedBy="{adminId}"
    timestamp="{timestamp}"
    reason="{reason}"
    metadata="{userId: {userId}, email: {user.email}}"
  />

  <q:return status="204" />
</q:function>
```

---

### Use Case 5: Database-Driven Intent

**Scenario:** System analyzes database and suggests improvements

```xml
<q:function name="createOrder">
  <q:param name="customerId" type="string" />
  <q:param name="items" type="array" />

  <q:intent>
    Create microservices to insert, retrieve, and delete orders.
    Look at the orders table schema and generate appropriate validations.
  </q:intent>
</q:function>
```

**What Happens:**
1. LLM connects to database
2. Reads `orders` table schema:
   ```sql
   CREATE TABLE orders (
     id UUID PRIMARY KEY,
     customer_id UUID REFERENCES customers(id),
     total_amount DECIMAL(10,2) NOT NULL,
     status VARCHAR(20) DEFAULT 'pending',
     created_at TIMESTAMP DEFAULT NOW()
   )
   ```
3. Generates 3 functions:
   - `createOrder` with validation (total_amount > 0, customer exists)
   - `getOrder` (GET /orders/:id)
   - `deleteOrder` (DELETE /orders/:id with status check)

---

## 🏗️ Technical Specification

### AST Node Definition

```python
@dataclass
class IntentNode(QuantumNode):
    """
    Represents a <q:intent> tag

    This node triggers LLM-based code generation/modification
    """

    # Required attributes
    description: str              # Natural language intent

    # Optional attributes
    scope: str = "local"          # local | function | component | global
    priority: str = "normal"      # low | normal | high | critical
    auto_apply: bool = True       # Auto-integrate or show for review?
    confidence_threshold: float = 0.8  # Min confidence to auto-apply

    # Processing metadata (populated during execution)
    analyzed_context: dict = None
    required_capabilities: List[str] = None
    missing_features: List[str] = None
    generated_code: str = None
    integration_plan: dict = None

    def to_dict(self) -> dict:
        return {
            "type": "IntentNode",
            "description": self.description,
            "scope": self.scope,
            "priority": self.priority,
            "auto_apply": self.auto_apply
        }
```

### Syntax

```xml
<q:intent
  scope="local|function|component|global"
  priority="low|normal|high|critical"
  auto-apply="true|false"
  confidence-threshold="0.0-1.0"
>
  Natural language description of intent
</q:intent>
```

**Attributes:**

- **scope** (optional, default: "local")
  - `local` - Intent applies to immediate code block
  - `function` - Intent applies to entire function
  - `component` - Intent applies to entire component
  - `global` - Intent may generate system-wide features

- **priority** (optional, default: "normal")
  - Affects processing order when multiple intents exist

- **auto-apply** (optional, default: "true")
  - `true` - Automatically integrate generated code
  - `false` - Show diff for manual review

- **confidence-threshold** (optional, default: "0.8")
  - Minimum LLM confidence score to auto-apply
  - Below threshold → always request review

---

## 🔍 Context Analysis

### What LLM Needs To Know

When processing an intent, the LLM receives:

```json
{
  "intent": {
    "description": "After 3 failed login attempts...",
    "scope": "function",
    "location": {
      "file": "components/auth/login.q",
      "function": "login",
      "line": 15
    }
  },

  "context": {
    "function": {
      "name": "login",
      "parameters": [
        {"name": "email", "type": "string"},
        {"name": "password", "type": "string"}
      ],
      "rest_endpoint": "POST /auth/login"
    },

    "available_variables": [
      "email", "password", "user", "isValid", "token"
    ],

    "database": {
      "tables": [
        {
          "name": "users",
          "columns": [
            {"name": "id", "type": "uuid"},
            {"name": "email", "type": "string"},
            {"name": "password", "type": "string"}
          ]
        }
      ]
    },

    "existing_features": [
      "databinding",
      "state_management",
      "conditionals",
      "loops",
      "functions",
      "validation"
    ],

    "request_context": {
      "available_properties": ["ip", "headers", "body", "method"]
    }
  }
}
```

---

## 🎨 Generation Strategies

### Strategy 1: Use Existing Features

**Intent:** "Validate email format"

**LLM Response:**
```xml
<!-- Feature 'validation' exists with email validator -->
<q:set name="email" value="{userInput}" validate="email" />
```

### Strategy 2: Generate New Feature

**Intent:** "Block IP after 3 failed attempts"

**LLM Response:**
```
No existing 'rate_limiting' feature found.

Generating new feature:
- src/core/features/rate_limiting/
  - src/ast_node.py (RateLimitNode)
  - src/parser.py
  - src/runtime.py
  - tests/
  - docs/

Integrating into function:
<q:rate-limit key="{clientIP}:login" max="3" window="15m" />
```

### Strategy 3: Modify Existing Code

**Intent:** "Round to 2 decimal places"

**LLM Response:**
```xml
<!-- Original -->
<q:set name="total" value="{price * quantity}" />

<!-- Modified -->
<q:set name="total" value="{round(price * quantity, 2)}" />
```

### Strategy 4: Add Database Schema

**Intent:** "Track failed login attempts"

**LLM Response:**
```sql
-- Generated migration
CREATE TABLE login_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ip VARCHAR(45) NOT NULL,
  email VARCHAR(255),
  attempted_at TIMESTAMP DEFAULT NOW(),
  success BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_login_attempts_ip ON login_attempts(ip);
```

---

## 🔒 Safety & Validation

### Before Auto-Applying

The system MUST validate:

1. **Syntax Correctness**
   - Generated code is valid Quantum XML
   - All tags are properly closed
   - Attributes are valid

2. **Type Safety**
   - Variables have correct types
   - Operations match types
   - Return values match function signature

3. **Logic Correctness**
   - No infinite loops created
   - No unreachable code
   - Proper error handling

4. **Test Validation**
   - All existing tests still pass
   - New tests for generated functionality pass

5. **Security Checks**
   - No SQL injection vulnerabilities
   - No exposed sensitive data
   - Proper authorization checks

### Confidence Scoring

LLM assigns confidence score based on:

```python
confidence_score = weighted_average([
    ("intent_clarity", 0.2),          # Is intent unambiguous?
    ("context_completeness", 0.15),   # Do we have all needed info?
    ("feature_availability", 0.15),   # Do required features exist?
    ("implementation_complexity", 0.2), # How complex is the solution?
    ("test_coverage", 0.15),          # Can we validate it?
    ("similar_examples", 0.15)        # Have we done this before?
])

if confidence_score >= threshold:
    auto_apply()
else:
    request_review()
```

---

## 📊 Review Mode

### When Confidence is Low

System presents diff for manual review:

```diff
Function: login

+ Generated Features:
+   - rate_limiting (new)
+   - email_notifications (new)

+ Database Changes:
+   - Table: login_attempts
+   - Table: blocked_ips

+ Code Changes:
  <q:function name="login">
    <q:param name="email" type="string" required="true" />
    <q:param name="password" type="string" required="true" />

+   <!-- Rate limiting check -->
+   <q:set name="clientIP" value="{request.ip}" />
+   <q:rate-limit ip="{clientIP}" action="check" var="isBlocked" />
+   <q:if condition="{isBlocked}">
+     <q:return status="429" value="Too many attempts" />
+   </q:if>

    <q:database-query table="users" where="email = {email}" var="user" />

+   <!-- Track failed attempt -->
    <q:if condition="{user == null}">
+     <q:rate-limit ip="{clientIP}" action="increment" threshold="3" window="15min">
+       <q:on-threshold-exceeded>
+         <q:send-email to="{email}" template="security-alert" />
+       </q:on-threshold-exceeded>
+     </q:rate-limit>
      <q:return status="401" value="Invalid credentials" />
    </q:if>

    <!-- ... rest unchanged ... -->
  </q:function>

? Accept changes? (yes/no/edit)
```

---

## 🔄 Self-Improvement Loop

### Training Data Generation

Every successfully processed intent becomes training data:

```json
{
  "intent": "After 3 failed login attempts from same IP, block for 15 minutes",
  "context": {
    "function": "login",
    "available_features": ["databinding", "conditionals"]
  },
  "generated_solution": {
    "new_features": ["rate_limiting", "email_notifications"],
    "integration_code": "...",
    "tests": "..."
  },
  "validation": {
    "tests_passed": true,
    "user_accepted": true,
    "confidence_score": 0.92
  },
  "metadata": {
    "timestamp": "2025-01-15T10:30:00Z",
    "processing_time": "8.3s"
  }
}
```

This data is added to:
- LLM fine-tuning dataset
- Semantic search index
- Pattern library

**Result:** Next time someone writes similar intent, LLM recognizes pattern and generates solution faster/better.

---

## 🎯 Scope Levels Explained

### Local Scope

```xml
<q:loop items="{products}" var="product">
  <q:set name="price" value="{product.price}" />

  <q:intent scope="local">
    Apply 10% discount if product is on sale
  </q:intent>

  <!-- Intent affects only this loop iteration -->
</q:loop>
```

### Function Scope

```xml
<q:function name="processOrder">
  <q:intent scope="function">
    Add audit logging for all database operations in this function
  </q:intent>

  <!-- All db operations in this function get logging -->
  <q:database-insert table="orders" data="{orderData}" />
  <q:database-update table="inventory" ... />
</q:function>
```

### Component Scope

```xml
<q:component name="UserProfile">
  <q:intent scope="component">
    Make all functions in this component require authentication
  </q:intent>

  <!-- All functions in component get auth checks -->
  <q:function name="updateProfile">...</q:function>
  <q:function name="deleteAccount">...</q:function>
</q:component>
```

### Global Scope

```xml
<q:intent scope="global">
  Add GDPR compliance across entire application:
  - User data export functionality
  - Right to be forgotten (delete all user data)
  - Consent management
</q:intent>

<!-- Generates system-wide features affecting all components -->
```

---

## 💡 Advanced Use Cases

### Intent Chaining

Multiple intents build on each other:

```xml
<q:function name="checkout">
  <q:intent priority="high">
    Calculate order total with tax
  </q:intent>

  <q:intent>
    Apply discount codes
  </q:intent>

  <q:intent>
    Validate payment method
  </q:intent>

  <q:intent>
    Send confirmation email
  </q:intent>

  <!-- LLM processes in priority order -->
  <!-- Each intent builds on previous -->
</q:function>
```

### Conditional Intents

```xml
<q:if condition="{environment == 'production'}">
  <q:intent>
    Enable detailed error logging and monitoring
  </q:intent>
</q:if>

<q:if condition="{user.role == 'admin'}">
  <q:intent>
    Add admin-only analytics dashboard
  </q:intent>
</q:if>
```

### Cross-Feature Intents

```xml
<q:intent scope="global">
  Refactor all database queries to use connection pooling.
  Generate migration script to optimize indexes.
  Add query performance monitoring.
</q:intent>

<!-- Affects multiple components system-wide -->
```

---

## 🚫 Limitations & Constraints

### What Intents CANNOT Do

1. **Change Core Architecture**
   - Cannot modify parser/runtime fundamentals
   - Cannot break existing APIs

2. **Violate Type Safety**
   - Cannot ignore type constraints
   - Must maintain type consistency

3. **Remove Required Features**
   - Cannot delete features other code depends on

4. **Bypass Security**
   - Cannot generate code that skips validation
   - Cannot expose sensitive data

### Error Handling

```xml
<q:intent>
  Make this function process 10,000 requests per second
</q:intent>

<!-- LLM Response: -->
<q:intent-error>
  Cannot guarantee performance without knowing:
  - Current bottlenecks
  - Database capacity
  - Server resources

  Suggestion: Provide more context or use profiling tools first.
</q:intent-error>
```

---

## 📈 Metrics & Monitoring

### Track Intent Success

```yaml
metrics:
  total_intents_processed: 1247
  auto_applied: 892 (71.5%)
  reviewed: 355 (28.5%)

  average_confidence: 0.87

  success_rate:
    auto_applied: 96.3%  # Tests passed after auto-apply
    reviewed: 99.1%      # Tests passed after human review

  generated_features: 45
  code_modifications: 623

  average_processing_time: 6.2s

  top_intent_patterns:
    - "Add validation" (187 occurrences)
    - "Cache results" (134 occurrences)
    - "Log to audit" (98 occurrences)
```

---

## 🎯 Implementation Priority

### ⚠️ IMPORTANT: This is Future Work

As Daniel wisely noted:
> "This layer will come much later. We shouldn't concern ourselves much about this feature or it might hold us down in development."

### Current Phase: Data Collection

**Right now, we should:**
1. ✅ Document the vision (this document)
2. ✅ Design intention file format
3. ✅ Build dataset structure
4. ✅ Collect examples as we develop features
5. ✅ Focus on core feature implementation

**DO NOT implement yet:**
- ❌ Intent processing pipeline
- ❌ LLM integration for intent parsing
- ❌ Auto-code generation from intents
- ❌ Feature auto-generation

### When To Implement

**Prerequisites before starting:**
1. Core features stable (loops, conditionals, functions, etc.)
2. Dataset has 500+ examples
3. Local LLM integration working
4. Feature registry operational
5. Test coverage >90%

**Estimated Timeline:** 6-12 months after core stabilization

---

## 🔮 Future Vision

### Self-Evolving Codebase

```
Year 1: Manual feature development + dataset collection
        → 50 features, 1000+ intention examples

Year 2: LLM integration + intent processing
        → Generate simple features from intents

Year 3: Recursive intent system operational
        → Codebase evolves through conversation

Year 5: Community-driven intent library
        → Thousands of developers contributing patterns
        → AI agents autonomously improving code
        → Self-healing, self-optimizing system
```

### The Ultimate Goal

```
Human: "Build me a CRM system"

Quantum:
  ✓ Analyzed 50 existing CRM patterns
  ✓ Generated 147 components
  ✓ Created database schema (12 tables)
  ✓ Generated REST APIs (89 endpoints)
  ✓ Added authentication & authorization
  ✓ Created admin dashboard
  ✓ Wrote 1,247 tests (all passing)
  ✓ Generated complete documentation

  Your CRM is ready. Would you like to customize anything?