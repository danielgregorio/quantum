<?xml version="1.0"?>
<!--
    Multi-Agent Customer Support Example

    Demonstrates a team of AI agents that collaborate to handle
    customer support requests through handoffs and shared context.

    Team Structure:
    - Router: Analyzes requests and routes to appropriate specialist
    - Billing: Handles payment, invoice, and subscription questions
    - Technical: Handles product and technical support questions

    Features Demonstrated:
    - q:team for multi-agent collaboration
    - Built-in handoff, readShared, writeShared, listAgents tools
    - Shared context between agents
    - Agent execution with handoff logging
-->
<q:component name="MultiAgentSupport" xmlns:q="urn:quantum">
    <!-- Customer question (would normally come from form input) -->
    <q:set name="userQuestion" value="I need help understanding my recent invoice" />
    <q:set name="userId" value="customer_12345" />

    <!-- Define the support team -->
    <q:team name="support" supervisor="router" max_handoffs="5">
        <!-- Shared context accessible by all agents -->
        <q:shared>
            <q:set name="customerId" value="{userId}" />
            <q:set name="customerName" value="John Doe" />
            <q:set name="accountType" value="Premium" />
            <q:set name="conversationNotes" value="" />
        </q:shared>

        <!-- Router Agent: Analyzes and routes requests -->
        <q:agent name="router" model="gpt-4">
            <q:instruction>
                You are a customer support router. Your job is to:
                1. Analyze the customer's question
                2. Determine which specialist can best help them
                3. Hand off to the appropriate specialist with context

                Available specialists:
                - "billing": For payment, invoice, subscription, pricing questions
                - "technical": For product usage, bugs, technical issues

                Use the handoff tool to transfer to the right specialist.
                Always include a brief summary of the issue in the handoff message.

                If the question is a simple greeting or doesn't need a specialist,
                you can respond directly.
            </q:instruction>

            <!-- Built-in tools for team coordination -->
            <q:tool name="handoff" builtin="true" />
            <q:tool name="listAgents" builtin="true" />
            <q:tool name="readShared" builtin="true" />
        </q:agent>

        <!-- Billing Agent: Handles payment and invoice questions -->
        <q:agent name="billing" model="gpt-4">
            <q:instruction>
                You are a billing specialist. You help customers with:
                - Invoice questions and explanations
                - Payment issues and refunds
                - Subscription changes
                - Pricing inquiries

                Always be polite and professional.
                Use readShared to get customer information.
                Use writeShared to add notes for other agents.

                If the issue requires technical support, use handoff to transfer
                to the "technical" agent.
            </q:instruction>

            <q:tool name="readShared" builtin="true" />
            <q:tool name="writeShared" builtin="true" />
            <q:tool name="handoff" builtin="true" />

            <!-- Custom tool to look up invoices -->
            <q:tool name="lookupInvoice" description="Look up invoice details by customer ID">
                <q:param name="customerId" type="string" required="true"
                         description="The customer ID to look up invoices for" />
                <q:body>
                    <!-- In a real app, this would query a database -->
                    <q:set name="invoiceData" value="{
                        'invoiceId': 'INV-2024-001',
                        'amount': 99.99,
                        'date': '2024-01-15',
                        'items': [
                            {'name': 'Premium Plan', 'amount': 79.99},
                            {'name': 'Add-on Service', 'amount': 20.00}
                        ],
                        'status': 'paid'
                    }" />
                    <q:return value="{invoiceData}" />
                </q:body>
            </q:tool>
        </q:agent>

        <!-- Technical Agent: Handles product and technical questions -->
        <q:agent name="technical" model="gpt-4">
            <q:instruction>
                You are a technical support specialist. You help customers with:
                - Product usage questions
                - Bug reports and troubleshooting
                - Feature requests
                - Integration help

                Use readShared to get customer context.
                Use writeShared to document the issue and resolution.

                If the issue involves billing, use handoff to transfer
                to the "billing" agent.
            </q:instruction>

            <q:tool name="readShared" builtin="true" />
            <q:tool name="writeShared" builtin="true" />
            <q:tool name="handoff" builtin="true" />

            <!-- Custom tool to search knowledge base -->
            <q:tool name="searchKnowledgeBase" description="Search the product knowledge base">
                <q:param name="query" type="string" required="true"
                         description="Search query for the knowledge base" />
                <q:body>
                    <!-- In a real app, this would search a KB -->
                    <q:set name="kbResults" value="[
                        {'title': 'Getting Started Guide', 'relevance': 0.9},
                        {'title': 'API Documentation', 'relevance': 0.7},
                        {'title': 'Troubleshooting FAQ', 'relevance': 0.8}
                    ]" />
                    <q:return value="{kbResults}" />
                </q:body>
            </q:tool>
        </q:agent>

        <!-- Execute the team with the user's question -->
        <q:execute task="{userQuestion}" entry="router" />
    </q:team>

    <!-- Display the result -->
    <div class="support-response">
        <h2>Support Response</h2>

        <div class="response-content">
            <p>{support}</p>
        </div>

        <!-- Show handoff history if any -->
        <q:if condition="{support_result.handoffs.length > 0}">
            <div class="handoff-log">
                <h3>Conversation Flow</h3>
                <q:loop var="handoff" type="array" items="{support_result.handoffs}">
                    <div class="handoff-item">
                        <span class="from-agent">{handoff.fromAgent}</span>
                        <span class="arrow">-></span>
                        <span class="to-agent">{handoff.toAgent}</span>
                        <q:if condition="{handoff.message}">
                            <span class="message">: {handoff.message}</span>
                        </q:if>
                    </div>
                </q:loop>
            </div>
        </q:if>

        <!-- Show execution details -->
        <div class="execution-details">
            <p>Final Agent: {support_result.finalAgent}</p>
            <p>Total Iterations: {support_result.totalIterations}</p>
            <p>Execution Time: {support_result.executionTime}ms</p>
        </div>
    </div>

    <style>
        .support-response {
            max-width: 800px;
            margin: 20px auto;
            padding: 20px;
            font-family: system-ui, sans-serif;
        }

        .response-content {
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .handoff-log {
            margin-top: 20px;
            padding: 15px;
            background: #e8f4fd;
            border-radius: 8px;
        }

        .handoff-item {
            padding: 8px 0;
            border-bottom: 1px solid #cde4f5;
        }

        .handoff-item:last-child {
            border-bottom: none;
        }

        .from-agent, .to-agent {
            font-weight: bold;
            color: #2563eb;
        }

        .arrow {
            margin: 0 8px;
            color: #666;
        }

        .message {
            color: #666;
            font-style: italic;
        }

        .execution-details {
            margin-top: 20px;
            padding: 15px;
            background: #f0f0f0;
            border-radius: 8px;
            font-size: 0.9em;
            color: #666;
        }

        .execution-details p {
            margin: 5px 0;
        }
    </style>
</q:component>
