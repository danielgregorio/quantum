<?xml version="1.0" encoding="UTF-8"?>
<!--
  Python Data Processing Example

  Demonstrates using Python scripting for complex data processing tasks
  that would be cumbersome in pure declarative syntax.
-->

<q:component name="DataProcessor">
    <!-- Import data processing modules -->
    <q:pyimport module="json" />
    <q:pyimport module="csv" />
    <q:pyimport module="collections" as="col" />
    <q:pyimport module="statistics" names="mean,median,stdev" />
    <q:pyimport module="functools" names="reduce" />

    <!-- Define a data transformer class -->
    <q:class name="DataTransformer">
        def __init__(self, data):
            self.data = data
            self.transformations = []

        def filter_by(self, key, value):
            """Filter records where key equals value"""
            self.data = [r for r in self.data if r.get(key) == value]
            self.transformations.append(f"filter({key}={value})")
            return self

        def filter_fn(self, fn):
            """Filter records using a function"""
            self.data = [r for r in self.data if fn(r)]
            self.transformations.append("filter(custom)")
            return self

        def map_field(self, key, fn):
            """Transform a field in each record"""
            for record in self.data:
                if key in record:
                    record[key] = fn(record[key])
            self.transformations.append(f"map({key})")
            return self

        def add_field(self, key, fn):
            """Add a computed field to each record"""
            for record in self.data:
                record[key] = fn(record)
            self.transformations.append(f"add({key})")
            return self

        def sort_by(self, key, reverse=False):
            """Sort records by a key"""
            self.data = sorted(self.data, key=lambda r: r.get(key, 0), reverse=reverse)
            self.transformations.append(f"sort({key})")
            return self

        def group_by(self, key):
            """Group records by a key"""
            groups = col.defaultdict(list)
            for record in self.data:
                groups[record.get(key, 'unknown')].append(record)
            return dict(groups)

        def result(self):
            """Return the transformed data"""
            return self.data

        def history(self):
            """Return transformation history"""
            return self.transformations
    </q:class>

    <!-- Define an aggregator class -->
    <q:class name="Aggregator">
        @staticmethod
        def sum_field(data, field):
            return sum(r.get(field, 0) for r in data)

        @staticmethod
        def avg_field(data, field):
            values = [r.get(field, 0) for r in data if field in r]
            return mean(values) if values else 0

        @staticmethod
        def count_by(data, field):
            counter = col.Counter(r.get(field) for r in data)
            return dict(counter)

        @staticmethod
        def top_n(data, field, n=10, reverse=True):
            sorted_data = sorted(data, key=lambda r: r.get(field, 0), reverse=reverse)
            return sorted_data[:n]
    </q:class>

    <!-- Sample sales data -->
    <q:set name="raw_data" value='[
        {"product": "Laptop", "category": "Electronics", "price": 999, "quantity": 5, "region": "North"},
        {"product": "Phone", "category": "Electronics", "price": 699, "quantity": 12, "region": "South"},
        {"product": "Tablet", "category": "Electronics", "price": 449, "quantity": 8, "region": "North"},
        {"product": "Chair", "category": "Furniture", "price": 199, "quantity": 20, "region": "East"},
        {"product": "Desk", "category": "Furniture", "price": 349, "quantity": 10, "region": "West"},
        {"product": "Monitor", "category": "Electronics", "price": 299, "quantity": 15, "region": "South"},
        {"product": "Keyboard", "category": "Electronics", "price": 79, "quantity": 50, "region": "North"},
        {"product": "Mouse", "category": "Electronics", "price": 49, "quantity": 75, "region": "East"},
        {"product": "Bookshelf", "category": "Furniture", "price": 129, "quantity": 12, "region": "West"},
        {"product": "Lamp", "category": "Furniture", "price": 59, "quantity": 30, "region": "South"}
    ]' />

    <!-- Process data with Python -->
    <q:python>
        # Parse the raw data from Quantum context
        data = json.loads(q.raw_data)

        q.info(f"Processing {len(data)} sales records...")

        # Create transformer and process electronics
        electronics = (
            DataTransformer(data.copy())
            .filter_by("category", "Electronics")
            .add_field("revenue", lambda r: r["price"] * r["quantity"])
            .sort_by("revenue", reverse=True)
            .result()
        )

        # Calculate aggregations
        q.electronics_count = len(electronics)
        q.total_revenue = Aggregator.sum_field(electronics, "revenue")
        q.avg_price = round(Aggregator.avg_field(electronics, "price"), 2)

        # Top 3 electronics by revenue
        q.top_electronics = [
            f"{e['product']}: ${e['revenue']:,}"
            for e in electronics[:3]
        ]

        # Group all data by region
        transformer = DataTransformer(data.copy())
        transformer.add_field("revenue", lambda r: r["price"] * r["quantity"])
        regional_data = transformer.group_by("region")

        q.regional_summary = {
            region: {
                "count": len(items),
                "revenue": sum(i["revenue"] for i in items)
            }
            for region, items in regional_data.items()
        }

        # Category breakdown
        q.category_counts = Aggregator.count_by(data, "category")

        # Statistical analysis
        all_prices = [r["price"] for r in data]
        q.price_stats = {
            "min": min(all_prices),
            "max": max(all_prices),
            "mean": round(mean(all_prices), 2),
            "median": median(all_prices),
            "stdev": round(stdev(all_prices), 2)
        }

        # High-value products (price > $200)
        high_value = (
            DataTransformer(data.copy())
            .filter_fn(lambda r: r["price"] > 200)
            .sort_by("price", reverse=True)
            .result()
        )
        q.high_value_products = [p["product"] for p in high_value]

        q.info("Data processing complete!")
    </q:python>

    <!-- Display results -->
    <ui:window title="Sales Data Analysis">
        <ui:vbox padding="lg" gap="md">
            <ui:text size="2xl" weight="bold">Sales Data Analysis</ui:text>

            <ui:grid cols="3" gap="md">
                <ui:card>
                    <ui:card-body align="center">
                        <ui:text size="3xl" weight="bold" color="primary">{electronics_count}</ui:text>
                        <ui:text color="muted">Electronics Products</ui:text>
                    </ui:card-body>
                </ui:card>

                <ui:card>
                    <ui:card-body align="center">
                        <ui:text size="3xl" weight="bold" color="success">${total_revenue}</ui:text>
                        <ui:text color="muted">Total Electronics Revenue</ui:text>
                    </ui:card-body>
                </ui:card>

                <ui:card>
                    <ui:card-body align="center">
                        <ui:text size="3xl" weight="bold" color="info">${avg_price}</ui:text>
                        <ui:text color="muted">Average Price</ui:text>
                    </ui:card-body>
                </ui:card>
            </ui:grid>

            <ui:card>
                <ui:card-header>
                    <ui:text weight="semibold">Top Electronics by Revenue</ui:text>
                </ui:card-header>
                <ui:card-body>
                    <q:loop items="{top_electronics}" as="item">
                        <ui:text>{item}</ui:text>
                    </q:loop>
                </ui:card-body>
            </ui:card>

            <ui:card>
                <ui:card-header>
                    <ui:text weight="semibold">Regional Summary</ui:text>
                </ui:card-header>
                <ui:card-body>
                    <ui:code language="json">{regional_summary}</ui:code>
                </ui:card-body>
            </ui:card>

            <ui:card>
                <ui:card-header>
                    <ui:text weight="semibold">Price Statistics</ui:text>
                </ui:card-header>
                <ui:card-body>
                    <ui:grid cols="5" gap="sm">
                        <ui:badge variant="info">Min: ${price_stats.min}</ui:badge>
                        <ui:badge variant="info">Max: ${price_stats.max}</ui:badge>
                        <ui:badge variant="success">Mean: ${price_stats.mean}</ui:badge>
                        <ui:badge variant="success">Median: ${price_stats.median}</ui:badge>
                        <ui:badge variant="warning">StdDev: ${price_stats.stdev}</ui:badge>
                    </ui:grid>
                </ui:card-body>
            </ui:card>

            <ui:card>
                <ui:card-header>
                    <ui:text weight="semibold">High-Value Products (> $200)</ui:text>
                </ui:card-header>
                <ui:card-body>
                    <q:loop items="{high_value_products}" as="product">
                        <ui:badge variant="primary">{product}</ui:badge>
                    </q:loop>
                </ui:card-body>
            </ui:card>
        </ui:vbox>
    </ui:window>
</q:component>
