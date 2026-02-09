---
layout: doc
title: Data Import Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/data-import.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Data Import Examples

Loading data from CSV, JSON, and XML files.

<div class="related-links">
  <a href="/guide/data-import" class="related-link">Documentation</a>
  <a href="/api/tags-reference#q-data" class="related-link">API Reference</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Data Import Patterns

### CSV Import

```xml
<q:data name="products" source="/data/products.csv" format="csv">
  <q:columns>
    <q:column name="id" type="number" />
    <q:column name="name" type="string" />
    <q:column name="price" type="number" />
  </q:columns>
</q:data>

<q:loop items="{products}" var="product">
  <p>{product.name}: ${product.price}</p>
</q:loop>
```

### JSON Import

```xml
<q:data name="config" source="/data/config.json" format="json" />

<p>App Name: {config.appName}</p>
<p>Version: {config.version}</p>
```

### XML Import

```xml
<q:data name="catalog" source="/data/catalog.xml" format="xml">
  <q:xpath select="//product" />
</q:data>

<q:loop items="{catalog}" var="item">
  <div class="product">
    <h3>{item.title}</h3>
    <p>{item.description}</p>
  </div>
</q:loop>
```

### Data Transformations

#### Filter

```xml
<q:data name="products" source="/data/products.csv" format="csv">
  <q:transform type="filter" condition="{price > 100}" />
</q:data>
```

#### Sort

```xml
<q:data name="products" source="/data/products.csv" format="csv">
  <q:transform type="sort" field="price" order="desc" />
</q:data>
```

#### Limit

```xml
<q:data name="topProducts" source="/data/products.csv" format="csv">
  <q:transform type="sort" field="sales" order="desc" />
  <q:transform type="limit" count="10" />
</q:data>
```

#### Compute

```xml
<q:data name="products" source="/data/products.csv" format="csv">
  <q:transform type="compute" field="total" expression="{price * quantity}" />
</q:data>
```

### Remote Data

```xml
<q:data name="users"
        source="https://api.example.com/users"
        format="json"
        cache="300" />
```

## Related Categories

- [State Management](/examples/state-management) - Store imported data
- [Loops](/examples/loops) - Iterate over data
- [Database Queries](/examples/queries) - Import to database
