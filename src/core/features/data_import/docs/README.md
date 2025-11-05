# q:data - Data Import & Transformation Component

## Overview

`<q:data>` is Quantum's ETL (Extract, Transform, Load) component for importing data from external sources (CSV, JSON, XML) and transforming it for use in components. It complements `<q:query>` (database data) and `<q:invoke>` (API data) by handling file-based and transformed data.

## Philosophy

1. **Declarative ETL** - Describe data shape, not transformation logic
2. **Multiple Sources** - Files, URLs, existing variables
3. **Type Safety** - Strong typing with automatic conversion
4. **Composability** - Chain transformations naturally
5. **Cached by Default** - Avoid redundant parsing

## Key Use Cases

1. **Static Data** - Import configuration, lookup tables, seed data
2. **File Processing** - Parse CSV/JSON/XML uploads
3. **Data Transformation** - Filter, sort, map, aggregate existing data
4. **API Response Processing** - Transform data from q:invoke
5. **Data Migration** - Import legacy data files

## Basic Usage

### Import CSV File
```xml
<q:data name="products" source="data/products.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
    <q:column name="price" type="decimal" />
    <q:column name="stock" type="integer" />
</q:data>

<!-- Use the data -->
<q:loop items="{products}" var="product">
    <div class="product">
        <h3>{product.name}</h3>
        <p>${product.price} - {product.stock} in stock</p>
    </div>
</q:loop>
```

### Import JSON from URL
```xml
<q:data name="countries"
        source="https://api.example.com/countries.json"
        type="json">
    <q:header name="Accept" value="application/json" />
</q:data>

<select name="country">
    <q:loop items="{countries}" var="country">
        <option value="{country.code}">{country.name}</option>
    </q:loop>
</select>
```

### Import XML
```xml
<q:data name="orders"
        source="orders.xml"
        type="xml"
        xpath="/orders/order">
    <q:field name="id" xpath="@id" type="integer" />
    <q:field name="customer" xpath="customer/text()" type="string" />
    <q:field name="total" xpath="total/text()" type="decimal" />
    <q:field name="date" xpath="@date" type="date" />
</q:data>
```

### Transform Existing Data
```xml
<!-- Filter and sort query results -->
<q:data name="activeUsers" source="{users}" type="transform">
    <q:filter condition="{status == 'active' && age >= 18}" />
    <q:sort by="lastName" order="asc" />
    <q:compute field="fullName" expression="{firstName} + ' ' + {lastName}" />
</q:data>
```

## Attributes

### Core Attributes

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `name` | string | Variable name for imported data | `name="products"` |
| `source` | string | File path, URL, or variable reference | `source="data.csv"` |
| `type` | string | Data format | `type="csv"` |
| `cache` | boolean | Cache parsed data | `cache="true"` (default) |
| `ttl` | integer | Cache TTL in seconds | `ttl="3600"` |

### Type Values

| Type | Description | Example Source |
|------|-------------|----------------|
| `csv` | Comma-separated values | `data/users.csv` |
| `json` | JSON data | `config/settings.json` |
| `xml` | XML document | `orders.xml` |
| `transform` | Transform existing data | `{users}` |

### CSV-Specific Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `delimiter` | string | `,` | Field delimiter |
| `quote` | string | `"` | Quote character |
| `header` | boolean | `true` | First row contains headers |
| `encoding` | string | `utf-8` | File encoding |
| `skip_rows` | integer | 0 | Rows to skip at start |

### XML-Specific Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `xpath` | string | XPath expression to select nodes |
| `namespace` | string | XML namespace URI |

## Child Elements

### `<q:column>` - CSV Column Definition
```xml
<q:data name="products" source="products.csv" type="csv">
    <q:column name="id" type="integer" required="true" />
    <q:column name="name" type="string" />
    <q:column name="price" type="decimal" min="0" />
    <q:column name="status" type="string" enum="['active','inactive']" />
</q:data>
```

### `<q:field>` - XML Field Mapping
```xml
<q:data name="books" source="library.xml" type="xml" xpath="/library/book">
    <q:field name="isbn" xpath="@isbn" type="string" />
    <q:field name="title" xpath="title/text()" type="string" />
    <q:field name="author" xpath="author/@name" type="string" />
    <q:field name="year" xpath="published/@year" type="integer" />
</q:data>
```

### `<q:transform>` - Data Transformation Operations

#### Filter
```xml
<q:data name="filtered" source="{products}" type="transform">
    <q:transform>
        <q:filter condition="{price < 100 && stock > 0}" />
    </q:transform>
</q:data>
```

#### Sort
```xml
<q:data name="sorted" source="{products}" type="transform">
    <q:transform>
        <q:sort by="price" order="desc" />
    </q:transform>
</q:data>
```

#### Map (Extract Field)
```xml
<q:data name="productNames" source="{products}" type="transform">
    <q:transform>
        <q:map field="name" />
    </q:transform>
</q:data>
<!-- Result: ["Product A", "Product B", "Product C"] -->
```

#### Group
```xml
<q:data name="byCategory" source="{products}" type="transform">
    <q:transform>
        <q:group by="category" aggregate="count" />
    </q:transform>
</q:data>
<!-- Result: [{"category": "Electronics", "count": 15}, ...] -->
```

#### Compute
```xml
<q:data name="enriched" source="{products}" type="transform">
    <q:transform>
        <q:compute field="discountPrice" expression="{price * 0.9}" type="decimal" />
        <q:compute field="inStock" expression="{stock > 0}" type="boolean" />
    </q:transform>
</q:data>
```

#### Rename
```xml
<q:data name="renamed" source="{users}" type="transform">
    <q:transform>
        <q:rename from="user_id" to="id" />
        <q:rename from="user_name" to="name" />
    </q:transform>
</q:data>
```

#### Limit
```xml
<q:data name="topTen" source="{products}" type="transform">
    <q:transform>
        <q:sort by="sales" order="desc" />
        <q:limit value="10" />
    </q:transform>
</q:data>
```

### `<q:header>` - HTTP Headers (for URL sources)
```xml
<q:data name="apiData" source="https://api.com/data.json" type="json">
    <q:header name="Authorization" value="Bearer {token}" />
    <q:header name="Accept" value="application/json" />
</q:data>
```

## Complex Transformations

### Chain Multiple Operations
```xml
<q:data name="processed" source="{rawData}" type="transform">
    <q:transform>
        <!-- Filter first -->
        <q:filter condition="{status == 'active'}" />

        <!-- Compute derived fields -->
        <q:compute field="fullName" expression="{firstName} + ' ' + {lastName}" />
        <q:compute field="age" expression="year(now()) - year({birthDate})" type="integer" />

        <!-- Rename for clarity -->
        <q:rename from="user_id" to="id" />

        <!-- Sort by computed field -->
        <q:sort by="age" order="desc" />

        <!-- Limit results -->
        <q:limit value="50" />
    </q:transform>
</q:data>
```

### Aggregate Data
```xml
<q:data name="salesByRegion" source="{sales}" type="transform">
    <q:transform>
        <q:group by="region" aggregate="sum" field="amount" />
        <q:sort by="total" order="desc" />
    </q:transform>
</q:data>

<table>
    <q:loop items="{salesByRegion}" var="region">
        <tr>
            <td>{region.region}</td>
            <td>${region.total}</td>
        </tr>
    </q:loop>
</table>
```

## Result Object

All data imports return a result object accessible via `{name_result}`:

```xml
<q:data name="products" source="products.csv" type="csv">...</q:data>

<q:if condition="{products_result.success}">
    <p>Loaded {products_result.recordCount} products in {products_result.loadTime}ms</p>
<q:else>
    <p>Error: {products_result.error.message}</p>
</q:else>
</q:if>
```

### Result Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether import succeeded |
| `data` | array | Imported/transformed data |
| `error` | object | Error object (if failed) |
| `recordCount` | integer | Number of records |
| `loadTime` | decimal | Load time in milliseconds |
| `cached` | boolean | Whether result was cached |
| `source` | string | Original source path/URL |

## Examples

### Example 1: Product Catalog from CSV
```xml
<q:component name="product-catalog">
    <!-- Import products from CSV -->
    <q:data name="products" source="data/products.csv" type="csv">
        <q:column name="id" type="integer" />
        <q:column name="name" type="string" />
        <q:column name="category" type="string" />
        <q:column name="price" type="decimal" />
        <q:column name="stock" type="integer" />
    </q:data>

    <!-- Filter to only show in-stock items -->
    <q:data name="available" source="{products}" type="transform">
        <q:transform>
            <q:filter condition="{stock > 0}" />
            <q:sort by="category" />
        </q:transform>
    </q:data>

    <div class="catalog">
        <q:loop items="{available}" var="product">
            <div class="product-card">
                <h3>{product.name}</h3>
                <p class="category">{product.category}</p>
                <p class="price">${product.price}</p>
                <p class="stock">{product.stock} available</p>
            </div>
        </q:loop>
    </div>
</q:component>
```

### Example 2: Configuration from JSON
```xml
<q:component name="app-settings">
    <!-- Load configuration -->
    <q:data name="config" source="config/app.json" type="json" cache="true" />

    <!-- Use configuration -->
    <header style="background: {config.theme.primaryColor}">
        <h1>{config.app.title}</h1>
    </header>

    <q:if condition="{config.features.darkMode}">
        <link rel="stylesheet" href="/css/dark-mode.css" />
    </q:if>
</q:component>
```

### Example 3: API Response Transformation
```xml
<q:component name="user-analytics">
    <!-- Fetch users from API -->
    <q:invoke name="allUsers" url="https://api.com/users" />

    <!-- Transform and analyze -->
    <q:data name="usersByCountry" source="{allUsers}" type="transform">
        <q:transform>
            <q:group by="country" aggregate="count" />
            <q:sort by="count" order="desc" />
            <q:limit value="10" />
        </q:transform>
    </q:data>

    <h2>Top 10 Countries by Users</h2>
    <ul>
        <q:loop items="{usersByCountry}" var="stat">
            <li>{stat.country}: {stat.count} users</li>
        </q:loop>
    </ul>
</q:component>
```

### Example 4: XML Order Processing
```xml
<q:component name="order-processor">
    <!-- Import orders from XML -->
    <q:data name="orders"
            source="uploads/orders.xml"
            type="xml"
            xpath="/orders/order">
        <q:field name="id" xpath="@id" type="integer" />
        <q:field name="customer" xpath="customer/@name" type="string" />
        <q:field name="total" xpath="total/text()" type="decimal" />
        <q:field name="status" xpath="status/text()" type="string" />
        <q:field name="date" xpath="@date" type="date" />
    </q:data>

    <!-- Filter pending orders -->
    <q:data name="pending" source="{orders}" type="transform">
        <q:transform>
            <q:filter condition="{status == 'pending'}" />
            <q:sort by="date" order="asc" />
        </q:transform>
    </q:data>

    <h2>Pending Orders: {pending_result.recordCount}</h2>
    <q:loop items="{pending}" var="order">
        <div class="order">
            <p>Order #{order.id} - {order.customer}</p>
            <p>Total: ${order.total} - Date: {order.date}</p>
        </div>
    </q:loop>
</q:component>
```

### Example 5: Multi-Source Data Combination
```xml
<q:component name="sales-dashboard">
    <!-- Import sales from CSV -->
    <q:data name="sales" source="data/sales.csv" type="csv">
        <q:column name="product_id" type="integer" />
        <q:column name="amount" type="decimal" />
        <q:column name="region" type="string" />
    </q:data>

    <!-- Import products from JSON -->
    <q:data name="products" source="data/products.json" type="json" />

    <!-- Calculate total sales -->
    <q:data name="totalSales" source="{sales}" type="transform">
        <q:transform>
            <q:group by="region" aggregate="sum" field="amount" />
        </q:transform>
    </q:data>

    <h1>Sales Dashboard</h1>
    <q:loop items="{totalSales}" var="regionSales">
        <div class="region-card">
            <h3>{regionSales.region}</h3>
            <p class="total">${regionSales.total}</p>
        </div>
    </q:loop>
</q:component>
```

## Implementation Phases

### Phase 1: Foundation ✅ Planned
- CSV import (files and URLs)
- JSON import (files and URLs)
- XML import (files and URLs)
- Basic transformations (filter, sort, limit)
- Type conversion and validation
- Result objects
- Caching

### Phase 2: Advanced Transformations
- Compute (derived fields)
- Group and aggregate (sum, avg, count, min, max)
- Rename fields
- Map (extract fields)
- Join operations (combine datasets)
- Pivot/unpivot

### Phase 3: Performance & Scale
- Streaming for large files
- Chunked processing
- Parallel transformations
- Memory optimization

## Integration with Other Features

### With q:invoke (Process API Data)
```xml
<q:invoke name="apiUsers" url="https://api.com/users" />

<q:data name="processedUsers" source="{apiUsers}" type="transform">
    <q:filter condition="{active == true}" />
    <q:compute field="fullName" expression="{first} + ' ' + {last}" />
    <q:sort by="fullName" />
</q:data>
```

### With q:query (Combine Database & File Data)
```xml
<q:query name="dbProducts" datasource="db">
    SELECT id, name, price FROM products WHERE active = true
</q:query>

<q:data name="csvProducts" source="new_products.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
    <q:column name="price" type="decimal" />
</q:data>

<!-- Both datasets now available for use -->
```

### With q:loop (Iterate Transformed Data)
```xml
<q:data name="topProducts" source="{products}" type="transform">
    <q:sort by="sales" order="desc" />
    <q:limit value="10" />
</q:data>

<q:loop items="{topProducts}" var="product" index="rank">
    <p>#{rank + 1}: {product.name} - {product.sales} sales</p>
</q:loop>
```

## Error Handling

### Result-Based Pattern
```xml
<q:data name="products" source="products.csv" type="csv">...</q:data>

<q:if condition="{products_result.success}">
    <!-- Success path -->
    <q:loop items="{products}" var="product">
        <p>{product.name}</p>
    </q:loop>
<q:else>
    <!-- Error path -->
    <div class="error">
        <p>Failed to load products</p>
        <p>{products_result.error.message}</p>
    </div>
</q:else>
</q:if>
```

### Fallback Data
```xml
<q:data name="config" source="https://api.com/config.json" type="json" />

<q:if condition="{config_result.error}">
    <!-- Use local fallback -->
    <q:data name="config" source="fallback/config.json" type="json" />
</q:if>
```

## Performance Considerations

### Caching
```xml
<!-- Cache for 1 hour -->
<q:data name="countries"
        source="https://api.com/countries.json"
        type="json"
        cache="true"
        ttl="3600" />
```

### Selective Loading
```xml
<!-- Only load first 100 rows from large CSV -->
<q:data name="preview" source="huge-file.csv" type="csv">
    <q:transform>
        <q:limit value="100" />
    </q:transform>
</q:data>
```

## See Also

- [q:invoke - Universal Invocation](../../invocation/docs/README.md)
- [q:query - Database Queries](../../../../docs/guide/query.md)
- [q:loop - Iteration](../../loops/docs/README.md)
- [Data Transformation Guide](../../../../docs/guide/data-transformation.md)
