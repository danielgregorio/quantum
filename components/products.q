<!-- Products List - Loop + Databinding Example -->
<q:component name="ProductsList" xmlns:q="https://quantum.lang/ns">
  <!-- Create sample product data using q:set -->
  <q:set name="storeName" value="Quantum Shop" />
  <q:set name="tagline" value="Buy amazing products powered by Quantum!" />

  <!-- Note: In real app, this would come from q:query -->
  <q:set name="products" type="array" value="[
    {'id': 1, 'name': 'Quantum T-Shirt', 'price': 29.99, 'stock': 15, 'image': '👕'},
    {'id': 2, 'name': 'Magic Mug', 'price': 12.99, 'stock': 30, 'image': '☕'},
    {'id': 3, 'name': 'Code Notebook', 'price': 9.99, 'stock': 0, 'image': '📓'},
    {'id': 4, 'name': 'Pixel Stickers', 'price': 4.99, 'stock': 100, 'image': '✨'},
    {'id': 5, 'name': 'Developer Hoodie', 'price': 49.99, 'stock': 8, 'image': '🧥'}
  ]" />

  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{storeName}</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        margin: 0;
        padding: 20px;
        background: #f5f5f5;
      }
      .header {
        text-align: center;
        margin-bottom: 40px;
        padding: 40px 20px;
        background: white;
        border-radius: 10px;
      }
      .header h1 {
        margin: 0;
        color: #333;
        font-size: 2.5em;
      }
      .header p {
        color: #666;
        font-size: 1.2em;
      }
      .products-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 20px;
        max-width: 1200px;
        margin: 0 auto;
      }
      .product-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        transition: transform 0.2s;
      }
      .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 20px rgba(0,0,0,0.15);
      }
      .product-image {
        font-size: 4em;
        text-align: center;
        margin: 20px 0;
      }
      .product-name {
        font-size: 1.3em;
        font-weight: bold;
        margin: 10px 0;
        color: #333;
      }
      .product-price {
        font-size: 1.5em;
        color: #4caf50;
        font-weight: bold;
      }
      .product-stock {
        margin: 10px 0;
        font-size: 0.9em;
      }
      .in-stock {
        color: #4caf50;
      }
      .out-of-stock {
        color: #f44336;
      }
      .btn {
        display: block;
        width: 100%;
        padding: 12px;
        margin-top: 15px;
        border: none;
        border-radius: 5px;
        font-size: 1em;
        cursor: pointer;
        transition: background 0.2s;
      }
      .btn-primary {
        background: #667eea;
        color: white;
      }
      .btn-primary:hover {
        background: #5568d3;
      }
      .btn-disabled {
        background: #ccc;
        color: #666;
        cursor: not-allowed;
      }
      .home-link {
        display: block;
        text-align: center;
        margin: 40px auto 20px;
        max-width: 1200px;
      }
      .home-link a {
        color: #667eea;
        text-decoration: none;
        font-size: 1.1em;
      }
    </style>
  </head>
  <body>
    <div class="header">
      <h1>🛍️ {storeName}</h1>
      <p>{tagline}</p>
    </div>

    <div class="products-grid">
      <!-- Loop through products array -->
      <q:loop items="{products}" var="product" type="array">
        <div class="product-card">
          <div class="product-image">{product.image}</div>
          <div class="product-name">{product.name}</div>
          <div class="product-price">${product.price}</div>

          <!-- Conditional rendering based on stock -->
          <q:if condition="{product.stock > 0}">
            <div class="product-stock in-stock">
              ✅ In Stock ({product.stock} available)
            </div>
            <button class="btn btn-primary">Add to Cart</button>
          <q:else>
            <div class="product-stock out-of-stock">
              ❌ Out of Stock
            </div>
            <button class="btn btn-disabled" disabled>Unavailable</button>
          </q:if>
        </div>
      </q:loop>
    </div>

    <div class="home-link">
      <a href="/">← Back to Home</a>
    </div>
  </body>
  </html>
</q:component>
