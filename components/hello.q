<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:set name="greeting" value="Hello" />
  <q:set name="name" value="World" />
  <q:set name="timestamp" value="2025-11-05" />

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{greeting} {name}!</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        margin: 0;
        background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%);
      }
      .card {
        background: white;
        padding: 60px;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        text-align: center;
      }
      h1 {
        font-size: 4em;
        margin: 0;
        background: linear-gradient(45deg, #f093fb, #f5576c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      p {
        color: #666;
        font-size: 1.2em;
      }
      .home-link {
        display: inline-block;
        margin-top: 20px;
        padding: 10px 20px;
        background: #f5576c;
        color: white;
        text-decoration: none;
        border-radius: 5px;
        transition: transform 0.2s;
      }
      .home-link:hover {
        transform: translateY(-2px);
      }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>{greeting}, {name}!</h1>
      <p>This is a simple Quantum component.</p>
      <p><small>Rendered on: {timestamp}</small></p>
      <a href="/" class="home-link">← Back to Home</a>
    </div>
  </body>
  </html>
</q:component>
