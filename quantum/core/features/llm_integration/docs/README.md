# q:llm - LLM Integration Component

## Overview

`<q:llm>` is Quantum's groundbreaking AI integration component that brings Large Language Models directly into your templates. Start with local models via LM Studio (no API costs, unlimited requests), then optionally migrate to cloud providers when needed.

## Philosophy

1. **AI-First Framework** - LLMs as first-class template citizens
2. **Local First, Cloud Optional** - Start free with LM Studio, scale to cloud later
3. **Declarative AI** - Describe what you want, not how to get it
4. **Type-Safe Outputs** - Structured responses with validation
5. **Observable Results** - Standard result objects like all Quantum components

## Key Innovation

**No other template language does this!** Quantum is the first to treat LLMs as native template components, enabling:
- Content generation in templates
- AI-powered classification
- Data extraction from unstructured text
- Sentiment analysis
- Translation with context
- Conversational UI

## Basic Usage

### Simple Completion
```xml
<q:llm name="summary"
       endpoint="http://localhost:1234/v1/completions"
       model="local-model">
    <q:prompt>
        Summarize this article in 3 sentences:

        {article.text}
    </q:prompt>
    <q:param name="max_tokens" value="150" />
    <q:param name="temperature" value="0.7" />
</q:llm>

<div class="summary">
    <h3>Summary</h3>
    <p>{summary}</p>
</div>
```

### Chat Completion
```xml
<q:llm name="response"
       endpoint="http://localhost:1234/v1/chat/completions"
       model="local-model">
    <q:message role="system">
        You are a helpful customer support agent.
    </q:message>
    <q:message role="user">
        {userQuestion}
    </q:message>
    <q:param name="temperature" value="0.8" />
</q:llm>

<div class="chat-response">
    {response}
</div>
```

### Structured Output (JSON)
```xml
<q:llm name="extracted"
       endpoint="http://localhost:1234/v1/completions"
       model="local-model"
       response_format="json">
    <q:prompt>
        Extract person information from this text:
        "{rawText}"

        Return JSON with this structure:
        {
            "name": "string",
            "email": "string",
            "phone": "string",
            "company": "string"
        }
    </q:prompt>
    <q:param name="temperature" value="0.3" />
</q:llm>

<!-- Access structured data -->
<div class="contact-card">
    <h3>{extracted.name}</h3>
    <p>{extracted.email}</p>
    <p>{extracted.phone}</p>
</div>
```

## Attributes

### Core Attributes

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `name` | string | Variable name for result | `name="summary"` |
| `endpoint` | string | LLM API endpoint URL | `endpoint="http://localhost:1234/v1/completions"` |
| `model` | string | Model identifier | `model="local-model"` |
| `response_format` | string | Output format | `response_format="json"` |

### Optional Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `temperature` | decimal | 0.7 | Randomness (0.0-2.0) |
| `max_tokens` | integer | 512 | Maximum response length |
| `top_p` | decimal | 1.0 | Nucleus sampling |
| `frequency_penalty` | decimal | 0.0 | Reduce repetition (-2.0 to 2.0) |
| `presence_penalty` | decimal | 0.0 | Encourage novelty (-2.0 to 2.0) |
| `stop` | array | null | Stop sequences |
| `cache` | boolean | false | Cache responses |
| `ttl` | integer | 3600 | Cache TTL in seconds |
| `timeout` | integer | 30000 | Request timeout in ms |

## Child Elements

### `<q:prompt>` - Completion Prompt
```xml
<q:llm name="result" endpoint="..." model="...">
    <q:prompt>
        Write a product description for: {product.name}

        Key features:
        {product.features}

        Target audience: {product.audience}
    </q:prompt>
</q:llm>
```

### `<q:message>` - Chat Messages
```xml
<q:llm name="chat" endpoint="..." model="...">
    <q:message role="system">
        You are a professional copywriter specializing in e-commerce.
    </q:message>
    <q:message role="user">
        Write a compelling product description for {product.name}
    </q:message>
    <q:message role="assistant">
        I'll create an engaging description that highlights the key benefits.
    </q:message>
    <q:message role="user">
        Make it more concise and add a call-to-action.
    </q:message>
</q:llm>
```

### `<q:param>` - Model Parameters
```xml
<q:llm name="creative" endpoint="..." model="...">
    <q:prompt>...</q:prompt>
    <q:param name="temperature" value="0.9" />
    <q:param name="max_tokens" value="500" />
    <q:param name="top_p" value="0.95" />
    <q:param name="frequency_penalty" value="0.3" />
    <q:param name="stop" value='["###", "END"]' />
</q:llm>
```

### `<q:schema>` - Output Schema (JSON mode)
```xml
<q:llm name="classified"
       endpoint="..."
       model="..."
       response_format="json">
    <q:prompt>
        Classify this support ticket: "{ticket.text}"
    </q:prompt>
    <q:schema>
        {
            "category": "string (billing|technical|general)",
            "priority": "string (low|medium|high)",
            "sentiment": "string (positive|negative|neutral)",
            "tags": "array of strings"
        }
    </q:schema>
</q:llm>
```

## LM Studio Setup

### 1. Install LM Studio
Download from: https://lmstudio.ai/

### 2. Download a Model
Recommended models:
- **Mistral 7B** - Great balance of quality and speed
- **Llama 2 7B** - Good general purpose
- **Phi-2** - Fast and efficient
- **CodeLlama** - For code generation

### 3. Start Local Server
In LM Studio:
- Click "Local Server" tab
- Select your model
- Click "Start Server"
- Server runs at: `http://localhost:1234`

### 4. Test in Quantum
```xml
<q:llm name="test"
       endpoint="http://localhost:1234/v1/completions"
       model="local-model">
    <q:prompt>Say "Hello from Quantum!"</q:prompt>
</q:llm>

<p>{test}</p>
```

## Result Object

All LLM calls return a result object accessible via `{name_result}`:

```xml
<q:llm name="generated" endpoint="..." model="...">
    <q:prompt>...</q:prompt>
</q:llm>

<q:if condition="{generated_result.success}">
    <div class="ai-content">
        {generated}
    </div>
    <p class="meta">
        Generated in {generated_result.executionTime}ms
        - {generated_result.tokenUsage.total_tokens} tokens
    </p>
<q:else>
    <p class="error">AI generation failed: {generated_result.error.message}</p>
</q:else>
</q:if>
```

### Result Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether call succeeded |
| `data` | string/object | Generated content |
| `error` | object | Error object (if failed) |
| `executionTime` | decimal | Time in milliseconds |
| `tokenUsage` | object | Token counts (prompt, completion, total) |
| `model` | string | Model used |
| `cached` | boolean | Whether response was cached |
| `finishReason` | string | Stop reason (stop, length, content_filter) |

## Common Use Cases

### 1. Product Descriptions
```xml
<q:component name="product-page">
    <q:param name="productId" type="integer" required="true" />

    <!-- Get product data -->
    <q:query name="product" datasource="db">
        SELECT * FROM products WHERE id = :id
        <q:param name="id" value="{productId}" type="integer" />
    </q:query>

    <!-- Generate AI description -->
    <q:llm name="description"
           endpoint="http://localhost:1234/v1/completions"
           model="local-model"
           cache="true"
           ttl="86400">
        <q:prompt>
            Write an engaging product description for:

            Name: {product[0].name}
            Category: {product[0].category}
            Features: {product[0].features}
            Price: ${product[0].price}

            Write 2-3 short paragraphs that highlight benefits.
            End with a call-to-action.
        </q:prompt>
        <q:param name="temperature" value="0.8" />
        <q:param name="max_tokens" value="300" />
    </q:llm>

    <div class="product-detail">
        <h1>{product[0].name}</h1>
        <div class="ai-description">{description}</div>
        <p class="price">${product[0].price}</p>
        <button>Add to Cart</button>
    </div>
</q:component>
```

### 2. Content Moderation
```xml
<q:component name="comment-moderator">
    <q:param name="commentText" type="string" required="true" />

    <!-- Classify comment -->
    <q:llm name="moderation"
           endpoint="http://localhost:1234/v1/completions"
           model="local-model"
           response_format="json">
        <q:prompt>
            Analyze this comment for moderation:
            "{commentText}"

            Return JSON:
            {
                "safe": true/false,
                "toxicity_score": 0.0-1.0,
                "issues": ["hate_speech", "spam", "harassment"],
                "reason": "explanation"
            }
        </q:prompt>
        <q:param name="temperature" value="0.2" />
    </q:llm>

    <q:if condition="{moderation.safe}">
        <!-- Approve comment -->
        <q:query name="approve" datasource="db">
            UPDATE comments SET status = 'approved' WHERE text = :text
            <q:param name="text" value="{commentText}" type="string" />
        </q:query>
        <p>Comment approved</p>
    <q:else>
        <!-- Flag for review -->
        <q:query name="flag" datasource="db">
            UPDATE comments
            SET status = 'flagged', flag_reason = :reason
            WHERE text = :text
            <q:param name="text" value="{commentText}" type="string" />
            <q:param name="reason" value="{moderation.reason}" type="string" />
        </q:query>
        <p>Comment flagged: {moderation.reason}</p>
    </q:else>
    </q:if>
</q:component>
```

### 3. Sentiment Analysis
```xml
<q:component name="review-dashboard">
    <!-- Get recent reviews -->
    <q:query name="reviews" datasource="db">
        SELECT id, product_id, user_id, text, rating, created_at
        FROM reviews
        WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
        ORDER BY created_at DESC
    </q:query>

    <!-- Analyze sentiment for each review -->
    <q:loop query="reviews">
        <q:llm name="sentiment_{reviews.id}"
               endpoint="http://localhost:1234/v1/completions"
               model="local-model"
               response_format="json">
            <q:prompt>
                Analyze sentiment of this product review:
                "{reviews.text}"

                Return JSON:
                {
                    "sentiment": "positive|negative|neutral",
                    "confidence": 0.0-1.0,
                    "key_topics": ["array", "of", "topics"]
                }
            </q:prompt>
            <q:param name="temperature" value="0.1" />
        </q:llm>

        <div class="review" data-sentiment="{sentiment_{reviews.id}.sentiment}">
            <p class="rating">Rating: {reviews.rating}/5</p>
            <p class="text">{reviews.text}</p>
            <p class="analysis">
                Sentiment: {sentiment_{reviews.id}.sentiment}
                (Confidence: {sentiment_{reviews.id}.confidence})
            </p>
        </div>
    </q:loop>
</q:component>
```

### 4. Data Extraction
```xml
<q:component name="resume-parser">
    <q:param name="resumeText" type="string" required="true" />

    <!-- Extract structured data from resume -->
    <q:llm name="parsed"
           endpoint="http://localhost:1234/v1/completions"
           model="local-model"
           response_format="json">
        <q:prompt>
            Extract information from this resume:

            {resumeText}

            Return JSON with this exact structure:
            {
                "name": "string",
                "email": "string",
                "phone": "string",
                "summary": "string",
                "skills": ["array", "of", "skills"],
                "experience": [
                    {
                        "company": "string",
                        "title": "string",
                        "duration": "string",
                        "description": "string"
                    }
                ],
                "education": [
                    {
                        "institution": "string",
                        "degree": "string",
                        "year": "string"
                    }
                ]
            }
        </q:prompt>
        <q:param name="temperature" value="0.1" />
        <q:param name="max_tokens" value="1000" />
    </q:llm>

    <!-- Store in database -->
    <q:query name="insertCandidate" datasource="db">
        INSERT INTO candidates (name, email, phone, skills, data)
        VALUES (:name, :email, :phone, :skills, :data)
        <q:param name="name" value="{parsed.name}" type="string" />
        <q:param name="email" value="{parsed.email}" type="string" />
        <q:param name="phone" value="{parsed.phone}" type="string" />
        <q:param name="skills" value="{JSON.stringify(parsed.skills)}" type="json" />
        <q:param name="data" value="{JSON.stringify(parsed)}" type="json" />
    </q:query>

    <p>Resume parsed successfully. Candidate ID: {insertCandidate[0].id}</p>
</q:component>
```

### 5. Translation with Context
```xml
<q:llm name="translated"
       endpoint="http://localhost:1234/v1/completions"
       model="local-model">
    <q:prompt>
        Translate this product title to Spanish.
        Keep it natural and marketing-friendly.

        Original: "{product.title}"
        Category: {product.category}
        Target audience: Young adults

        Return only the translated title, nothing else.
    </q:prompt>
    <q:param name="temperature" value="0.5" />
</q:llm>

<h1 class="spanish-title">{translated}</h1>
```

## Implementation Phases

### Phase 1: LM Studio Support ✅ Planned
- Completions API
- Chat completions API
- Basic parameters (temperature, max_tokens, top_p)
- JSON response format
- Result objects with metadata
- Error handling
- Basic caching

### Phase 2: Cloud Providers
- OpenAI API support
- Anthropic Claude API support
- Cohere API support
- Provider-agnostic configuration
- Automatic failover
- Cost tracking

### Phase 3: Advanced Features
- Streaming responses
- Function calling (tool use)
- Vision models (image understanding)
- Embeddings generation
- Fine-tuned model support

## Migration Path

### From LM Studio to OpenAI
```xml
<!-- Development: LM Studio (local, free) -->
<q:llm name="summary"
       endpoint="http://localhost:1234/v1/completions"
       model="local-model">
    <q:prompt>...</q:prompt>
</q:llm>

<!-- Production: OpenAI (cloud, costs money) -->
<q:llm name="summary"
       endpoint="https://api.openai.com/v1/completions"
       model="gpt-4"
       api_key="{env.OPENAI_API_KEY}">
    <q:prompt>...</q:prompt>
</q:llm>
```

**Just change 2 attributes!** All other code stays the same.

## Performance Considerations

### Caching Responses
```xml
<!-- Cache product descriptions for 24 hours -->
<q:llm name="description"
       endpoint="..."
       model="..."
       cache="true"
       ttl="86400">
    <q:prompt>...</q:prompt>
</q:llm>
```

### Temperature Settings
- **0.0-0.3**: Factual, deterministic (data extraction, classification)
- **0.4-0.7**: Balanced (general content, summaries)
- **0.8-1.0**: Creative (marketing copy, stories)
- **1.1-2.0**: Very creative, unpredictable

### Token Limits
- Set `max_tokens` appropriately
- Monitor `tokenUsage` in result objects
- Use `stop` sequences to control length

## Error Handling

### Result-Based Pattern
```xml
<q:llm name="content" endpoint="..." model="...">
    <q:prompt>...</q:prompt>
</q:llm>

<q:if condition="{content_result.success}">
    <div class="ai-content">{content}</div>
<q:else>
    <div class="error">
        <p>AI generation failed</p>
        <p>{content_result.error.message}</p>
        <!-- Use fallback content -->
        <div class="fallback">{product.defaultDescription}</div>
    </div>
</q:else>
</q:if>
```

## Integration with Other Features

### With q:query (Database + AI)
```xml
<q:query name="products" datasource="db">
    SELECT * FROM products WHERE description IS NULL LIMIT 10
</q:query>

<q:loop query="products">
    <q:llm name="desc_{products.id}" endpoint="..." model="...">
        <q:prompt>Write a description for {products.name}</q:prompt>
    </q:llm>

    <q:query name="update_{products.id}" datasource="db">
        UPDATE products SET description = :desc WHERE id = :id
        <q:param name="desc" value="{desc_{products.id}}" type="string" />
        <q:param name="id" value="{products.id}" type="integer" />
    </q:query>
</q:loop>
```

### With q:invoke (API + AI)
```xml
<q:invoke name="userReviews" url="https://api.com/reviews" />

<q:llm name="summary"
       endpoint="..."
       model="..."
       response_format="json">
    <q:prompt>
        Summarize these reviews:
        {JSON.stringify(userReviews)}

        Return JSON with: overall_sentiment, key_themes, summary
    </q:prompt>
</q:llm>

<div class="review-summary">
    <p><strong>Overall:</strong> {summary.overall_sentiment}</p>
    <p><strong>Key Themes:</strong> {summary.key_themes.join(', ')}</p>
    <p>{summary.summary}</p>
</div>
```

### With q:data (File + AI)
```xml
<q:data name="orders" source="orders.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="customer_notes" type="string" />
</q:data>

<q:loop items="{orders}" var="order">
    <q:llm name="category_{order.id}"
           endpoint="..."
           model="..."
           response_format="json">
        <q:prompt>
            Categorize this customer request:
            "{order.customer_notes}"

            Return JSON: {"category": "string", "urgency": "low|medium|high"}
        </q:prompt>
    </q:llm>
</q:loop>
```

## See Also

- [q:agent - AI Agents with Tool Use](../../agents/docs/README.md)
- [q:invoke - Universal Invocation](../../invocation/docs/README.md)
- [q:data - Data Import](../../data_import/docs/README.md)
- [LM Studio Documentation](https://lmstudio.ai/docs)
