<q:component name="LLMDemo">

    <!-- ============================== -->
    <!-- Test 1: Simple Completion      -->
    <!-- ============================== -->
    <q:llm name="greeting" model="phi3">
        <q:prompt>Say hello in one short sentence.</q:prompt>
    </q:llm>

    <h2>Test 1 - Simple Completion</h2>
    <p>{greeting}</p>

    <!-- ============================== -->
    <!-- Test 2: Chat Mode              -->
    <!-- ============================== -->
    <q:llm name="chat" model="phi3">
        <q:message role="system">You are a concise assistant. Answer in one sentence.</q:message>
        <q:message role="user">What is the Quantum Framework?</q:message>
    </q:llm>

    <h2>Test 2 - Chat Mode</h2>
    <p>{chat}</p>

    <!-- ============================== -->
    <!-- Test 3: JSON Response Format   -->
    <!-- ============================== -->
    <q:llm name="extracted" model="phi3" responseFormat="json" temperature="0.1">
        <q:prompt>Extract the name and age from this text and return as JSON with keys "name" and "age": "John Smith is 32 years old"</q:prompt>
    </q:llm>

    <h2>Test 3 - JSON Extraction</h2>
    <p>{extracted}</p>

    <!-- ============================== -->
    <!-- Test 4: Databinding in Prompt  -->
    <!-- ============================== -->
    <q:set name="product" value="Quantum Framework" />
    <q:set name="audience" value="web developers" />

    <q:llm name="tagline" model="phi3" temperature="0.8" maxTokens="50">
        <q:prompt>Write a one-line tagline for {product} targeting {audience}.</q:prompt>
    </q:llm>

    <h2>Test 4 - Databinding in Prompt</h2>
    <p>{tagline}</p>

</q:component>
