<!-- HTML Elements -->
<q:component name="HTMLElements">
  <q:set name="imageUrl" value="https://via.placeholder.com/150" />
  <q:set name="linkText" value="Visit Quantum Docs" />

  <style>
    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
    .card { background: #f5f5f5; border-radius: 8px; padding: 16px; margin: 12px 0; }
    .btn { background: #3b82f6; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }
    .btn:hover { background: #2563eb; }
  </style>

  <div class="container">
    <h1>HTML Elements Demo</h1>

    <div class="card">
      <h3>Image</h3>
      <img src="{imageUrl}" alt="Placeholder" />
    </div>

    <div class="card">
      <h3>Button</h3>
      <button class="btn">Click Me</button>
    </div>

    <div class="card">
      <h3>Link</h3>
      <a href="https://quantum.dev">{linkText}</a>
    </div>

    <div class="card">
      <h3>Form Elements</h3>
      <input type="text" placeholder="Enter your name" />
      <br /><br />
      <select>
        <option>Option 1</option>
        <option>Option 2</option>
        <option>Option 3</option>
      </select>
    </div>
  </div>
</q:component>
