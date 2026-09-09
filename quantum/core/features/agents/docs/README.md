# q:agent - AI Agents with Tool Use

## Overview

`<q:agent>` enables autonomous AI agents that can use tools (functions, queries, APIs) to complete complex, multi-step tasks. Think AutoGPT or LangChain agents, but native to Quantum templates.

## Philosophy

1. **Autonomous Problem Solving** - Agent decides which tools to use and when
2. **Tool-Augmented AI** - Give agents access to your functions, queries, APIs
3. **Observable Actions** - See what the agent is doing and why
4. **Safe Execution** - Agents can only use explicitly provided tools
5. **Result-Based** - Standard result objects like all Quantum components

## Key Concept

**Traditional approach:** You write step-by-step code
**Agent approach:** You describe the goal, agent figures out the steps

## Basic Usage

### Simple Agent with Tools
```xml
<q:agent name="orderProcessor"
         model="local-model"
         endpoint="http://localhost:1234/v1/chat/completions">

    <q:instruction>
        You are a customer support agent. Help users with their orders.
        Use the available tools to look up information and take actions.
    </q:instruction>

    <!-- Tool 1: Get order details -->
    <q:tool name="getOrder" description="Get order details by ID">
        <q:param name="orderId" type="integer" required="true" />
        <q:function name="getOrderById">
            <q:query name="order" datasource="db">
                SELECT * FROM orders WHERE id = :orderId
                <q:param name="orderId" value="{orderId}" type="integer" />
            </q:query>
            <q:return value="{order[0]}" />
        </q:function>
    </q:tool>

    <!-- Tool 2: Update order status -->
    <q:tool name="updateStatus" description="Update order status">
        <q:param name="orderId" type="integer" required="true" />
        <q:param name="status" type="string" required="true" />
        <q:function name="updateOrderStatus">
            <q:query name="update" datasource="db">
                UPDATE orders SET status = :status WHERE id = :orderId
                <q:param name="orderId" value="{orderId}" type="integer" />
                <q:param name="status" value="{status}" type="string" />
            </q:query>
            <q:return value="Order {orderId} updated to {status}" />
        </q:function>
    </q:tool>

    <!-- Run the agent -->
    <q:execute task="Check status of order #1234 and mark it as shipped" />
</q:agent>

<!-- Agent's response -->
<div class="agent-result">
    <p>{orderProcessor.result}</p>
    <details>
        <summary>Agent actions ({orderProcessor_result.actionCount})</summary>
        <q:loop items="{orderProcessor_result.actions}" var="action">
            <p>{action.tool}: {action.args} → {action.result}</p>
        </q:loop>
    </details>
</div>
```

## How It Works

1. **Agent receives task**: "Check status of order #1234 and mark as shipped"
2. **Agent analyzes available tools**: getOrder, updateStatus
3. **Agent decides to use getOrder**: Calls `getOrder(orderId=1234)`
4. **Agent receives order data**: status="pending", customer="John"
5. **Agent decides to use updateStatus**: Calls `updateStatus(orderId=1234, status="shipped")`
6. **Agent synthesizes response**: "I've checked order #1234 for John. It was pending, and I've now marked it as shipped."
7. **User sees final response + action log**

## Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | string | Agent variable name |
| `model` | string | LLM model identifier |
| `endpoint` | string | LLM API endpoint |
| `max_iterations` | integer | Max tool calls (default: 10) |
| `timeout` | integer | Total timeout in ms (default: 60000) |

## Child Elements

### `<q:instruction>` - System Prompt
```xml
<q:instruction>
    You are a helpful data analyst. Use the tools to query data,
    perform calculations, and generate insights. Be concise and accurate.
</q:instruction>
```

### `<q:tool>` - Tool Definition
```xml
<q:tool name="searchProducts" description="Search products by keyword">
    <q:param name="keyword" type="string" required="true" />
    <q:param name="limit" type="integer" default="10" />

    <q:function name="doSearch">
        <q:query name="results" datasource="db">
            SELECT * FROM products
            WHERE name LIKE :keyword
            LIMIT :limit
            <q:param name="keyword" value="%{keyword}%" type="string" />
            <q:param name="limit" value="{limit}" type="integer" />
        </q:query>
        <q:return value="{results}" />
    </q:function>
</q:tool>
```

### `<q:execute>` - Run Agent
```xml
<q:execute task="Find the 5 most expensive products in the Electronics category" />
```

## Real-World Examples

### Example 1: Customer Support Agent
```xml
<q:component name="support-chat">
    <q:param name="userMessage" type="string" required="true" />
    <q:param name="userId" type="integer" required="true" />

    <q:agent name="support"
             model="local-model"
             endpoint="http://localhost:1234/v1/chat/completions">

        <q:instruction>
            You are a customer support agent for an e-commerce store.
            Help customers with order tracking, returns, and general questions.
            Always be polite and helpful.
        </q:instruction>

        <q:tool name="getUserOrders" description="Get customer's order history">
            <q:param name="userId" type="integer" required="true" />
            <q:function name="fetchOrders">
                <q:query name="orders" datasource="db">
                    SELECT id, created_at, status, total
                    FROM orders
                    WHERE user_id = :userId
                    ORDER BY created_at DESC
                    LIMIT 10
                    <q:param name="userId" value="{userId}" type="integer" />
                </q:query>
                <q:return value="{orders}" />
            </q:function>
        </q:tool>

        <q:tool name="trackOrder" description="Get tracking info for specific order">
            <q:param name="orderId" type="integer" required="true" />
            <q:function name="getTracking">
                <q:query name="tracking" datasource="db">
                    SELECT tracking_number, carrier, status, estimated_delivery
                    FROM shipments
                    WHERE order_id = :orderId
                    <q:param name="orderId" value="{orderId}" type="integer" />
                </q:query>
                <q:return value="{tracking[0]}" />
            </q:function>
        </q:tool>

        <q:tool name="initiateReturn" description="Start return process for an order">
            <q:param name="orderId" type="integer" required="true" />
            <q:param name="reason" type="string" required="true" />
            <q:function name="createReturn">
                <q:query name="newReturn" datasource="db">
                    INSERT INTO returns (order_id, reason, status, created_at)
                    VALUES (:orderId, :reason, 'pending', NOW())
                    RETURNING id
                    <q:param name="orderId" value="{orderId}" type="integer" />
                    <q:param name="reason" value="{reason}" type="string" />
                </q:query>
                <q:return value="Return #{newReturn[0].id} created successfully" />
            </q:function>
        </q:tool>

        <q:execute task="{userMessage}" context="User ID: {userId}" />
    </q:agent>

    <div class="chat-message agent">
        <p>{support.result}</p>
    </div>
</q:component>
```

### Example 2: Data Analysis Agent
```xml
<q:component name="sales-analyzer">
    <q:param name="analysisRequest" type="string" required="true" />

    <q:agent name="analyst"
             model="local-model"
             endpoint="http://localhost:1234/v1/chat/completions">

        <q:instruction>
            You are a data analyst. Use the available tools to query sales data,
            perform calculations, and generate insights. Present findings clearly.
        </q:instruction>

        <q:tool name="querySales" description="Query sales data with filters">
            <q:param name="startDate" type="date" required="true" />
            <q:param name="endDate" type="date" required="true" />
            <q:param name="region" type="string" default="all" />

            <q:function name="getSales">
                <q:query name="sales" datasource="db">
                    SELECT product_id, SUM(amount) as total, COUNT(*) as orders
                    FROM sales
                    WHERE sale_date BETWEEN :start AND :end
                    <q:if condition="{region != 'all'}">
                        AND region = :region
                    </q:if>
                    GROUP BY product_id
                    <q:param name="start" value="{startDate}" type="date" />
                    <q:param name="end" value="{endDate}" type="date" />
                    <q:param name="region" value="{region}" type="string" />
                </q:query>
                <q:return value="{sales}" />
            </q:function>
        </q:tool>

        <q:tool name="calculateGrowth" description="Calculate growth rate between periods">
            <q:param name="currentTotal" type="decimal" required="true" />
            <q:param name="previousTotal" type="decimal" required="true" />

            <q:function name="computeGrowth">
                <q:set name="growth"
                       value="(({currentTotal} - {previousTotal}) / {previousTotal}) * 100"
                       type="decimal" />
                <q:return value="{growth}" />
            </q:function>
        </q:tool>

        <q:execute task="{analysisRequest}" />
    </q:agent>

    <div class="analysis-result">
        <h2>Analysis Results</h2>
        <div class="answer">{analyst.result}</div>

        <h3>Agent Actions</h3>
        <ul>
            <q:loop items="{analyst_result.actions}" var="action">
                <li>
                    <strong>{action.tool}</strong>
                    <code>{JSON.stringify(action.args)}</code>
                    → {action.result}
                </li>
            </q:loop>
        </ul>
    </div>
</q:component>
```

### Example 3: Content Workflow Agent
```xml
<q:agent name="contentCreator"
         model="local-model"
         endpoint="http://localhost:1234/v1/chat/completions">

    <q:instruction>
        You are a content creation assistant. Use tools to fetch data,
        generate content, and save results. Follow best practices for SEO.
    </q:instruction>

    <q:tool name="getProductInfo" description="Get product details">
        <q:param name="productId" type="integer" required="true" />
        <q:function name="fetchProduct">
            <q:query name="product" datasource="db">
                SELECT * FROM products WHERE id = :id
                <q:param name="id" value="{productId}" type="integer" />
            </q:query>
            <q:return value="{product[0]}" />
        </q:function>
    </q:tool>

    <q:tool name="generateDescription" description="Generate AI product description">
        <q:param name="productName" type="string" required="true" />
        <q:param name="features" type="string" required="true" />

        <q:function name="createDesc">
            <q:llm name="desc"
                   endpoint="http://localhost:1234/v1/completions"
                   model="local-model">
                <q:prompt>
                    Write an engaging product description for: {productName}
                    Features: {features}
                    Keep it under 100 words.
                </q:prompt>
            </q:llm>
            <q:return value="{desc}" />
        </q:function>
    </q:tool>

    <q:tool name="saveDescription" description="Save description to database">
        <q:param name="productId" type="integer" required="true" />
        <q:param name="description" type="string" required="true" />

        <q:function name="updateDesc">
            <q:query name="update" datasource="db">
                UPDATE products
                SET description = :desc, updated_at = NOW()
                WHERE id = :id
                <q:param name="desc" value="{description}" type="string" />
                <q:param name="id" value="{productId}" type="integer" />
            </q:query>
            <q:return value="Description saved for product {productId}" />
        </q:function>
    </q:tool>

    <q:execute task="Generate and save descriptions for products 101, 102, and 103" />
</q:agent>

<p>{contentCreator.result}</p>
```

## Result Object

```xml
<q:agent name="myAgent" ...>...</q:agent>

<!-- Access results -->
<q:if condition="{myAgent_result.success}">
    <p>Agent completed in {myAgent_result.executionTime}ms</p>
    <p>Actions taken: {myAgent_result.actionCount}</p>
    <p>Iterations: {myAgent_result.iterations}</p>

    <q:loop items="{myAgent_result.actions}" var="action">
        <div class="action">
            <p><strong>{action.tool}</strong></p>
            <p>Args: {JSON.stringify(action.args)}</p>
            <p>Result: {action.result}</p>
        </div>
    </q:loop>
<q:else>
    <p>Agent failed: {myAgent_result.error.message}</p>
</q:else>
</q:if>
```

### Result Metadata

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether agent succeeded |
| `result` | string | Agent's final response |
| `error` | object | Error object (if failed) |
| `executionTime` | decimal | Total time in ms |
| `iterations` | integer | Number of reasoning loops |
| `actionCount` | integer | Total tools called |
| `actions` | array | Log of all tool calls |
| `tokenUsage` | object | LLM token counts |

## Implementation Phases

### Phase 1: Foundation ✅ Planned
- Basic agent loop (think → act → observe)
- Tool definition and calling
- Function tools (q:function)
- Query tools (q:query)
- Instruction/system prompts
- Action logging
- Max iterations safety limit

### Phase 2: Advanced Tools
- Invoke tools (q:invoke for APIs)
- LLM tools (agent can use other LLMs)
- Data tools (q:data)
- Tool approval (require user confirmation)
- Parallel tool execution

### Phase 3: Complex Agents
- Multi-agent systems (agents coordinating)
- Memory/context persistence
- Agent chaining (output of one → input of another)
- Hierarchical agents (supervisor + workers)

## Safety & Limits

### Max Iterations
```xml
<q:agent max_iterations="5" ...>
    <!-- Agent can call tools max 5 times -->
</q:agent>
```

### Timeout
```xml
<q:agent timeout="30000" ...>
    <!-- Agent must complete within 30 seconds -->
</q:agent>
```

### Tool Restrictions
Agents can ONLY use explicitly provided tools. They cannot:
- Execute arbitrary code
- Access files outside tool permissions
- Make network requests (unless you provide an invoke tool)
- Modify database (unless you provide an update tool)

## Best Practices

1. **Clear Instructions**: Be specific about agent's role and goals
2. **Well-Named Tools**: Tool names and descriptions help agent decide when to use them
3. **Typed Parameters**: Use strong types to prevent errors
4. **Limit Scope**: Don't give destructive tools to experimental agents
5. **Log Actions**: Always review what agents did
6. **Set Limits**: Use max_iterations and timeout

## Integration with Other Features

### With q:llm
```xml
<q:tool name="generateContent">
    <q:function>
        <q:llm name="content" ...>
            <q:prompt>...</q:prompt>
        </q:llm>
        <q:return value="{content}" />
    </q:function>
</q:tool>
```

### With q:invoke
```xml
<q:tool name="getWeather">
    <q:param name="city" type="string" />
    <q:function>
        <q:invoke name="weather" url="https://api.weather.com/...">
            <q:param name="q" value="{city}" />
        </q:invoke>
        <q:return value="{weather}" />
    </q:function>
</q:tool>
```

### With q:data
```xml
<q:tool name="analyzeCSV">
    <q:param name="filePath" type="string" />
    <q:function>
        <q:data name="data" source="{filePath}" type="csv">...</q:data>
        <q:data name="stats" source="{data}" type="transform">
            <q:group by="category" aggregate="count" />
        </q:data>
        <q:return value="{stats}" />
    </q:function>
</q:tool>
```

## See Also

- [q:llm - LLM Integration](../../llm_integration/docs/README.md)
- [q:function - Functions](../../../../docs/guide/functions.md)
- [q:invoke - Universal Invocation](../../invocation/docs/README.md)
