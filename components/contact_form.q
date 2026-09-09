<q:component name="ContactForm">
  <!-- Phase A: Forms & Actions Test -->

  <q:action name="submitContact" method="POST">
    <q:param name="name" type="string" minlength="3" required="true" />
    <q:param name="email" type="email" required="true" />
    <q:param name="message" type="string" minlength="10" required="true" />

    <!-- Simulate saving to database (would use q:query when Phase D is implemented) -->
    <q:set name="saved" value="true" />

    <q:redirect url="/contact_success" flash="Thank you {name}! Your message has been sent." />
  </q:action>

  <!-- Display flash message if present -->
  <q:param name="flash" type="string" default="" />
  <q:param name="flashType" type="string" default="info" />

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Contact Form - Quantum Phase A Test</title>
    <style>
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }

      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
      }

      .container {
        background: white;
        border-radius: 10px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        max-width: 500px;
        width: 100%;
        padding: 40px;
      }

      h1 {
        color: #333;
        margin-bottom: 10px;
        font-size: 28px;
      }

      .subtitle {
        color: #666;
        margin-bottom: 30px;
        font-size: 14px;
      }

      .alert {
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        font-weight: 500;
      }

      .alert-success {
        background: #d4edda;
        border-left: 4px solid #28a745;
        color: #155724;
      }

      .alert-error {
        background: #f8d7da;
        border-left: 4px solid #dc3545;
        color: #721c24;
      }

      .alert-warning {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        color: #856404;
      }

      .alert-info {
        background: #d1ecf1;
        border-left: 4px solid #17a2b8;
        color: #0c5460;
      }

      .form-group {
        margin-bottom: 20px;
      }

      label {
        display: block;
        margin-bottom: 8px;
        color: #333;
        font-weight: 500;
        font-size: 14px;
      }

      input, textarea {
        width: 100%;
        padding: 12px;
        border: 2px solid #e0e0e0;
        border-radius: 5px;
        font-size: 14px;
        font-family: inherit;
        transition: border-color 0.3s;
      }

      input:focus, textarea:focus {
        outline: none;
        border-color: #667eea;
      }

      textarea {
        resize: vertical;
        min-height: 120px;
      }

      button {
        width: 100%;
        padding: 14px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 5px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
      }

      button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
      }

      button:active {
        transform: translateY(0);
      }

      .required {
        color: #dc3545;
      }

      .footer {
        margin-top: 30px;
        text-align: center;
        color: #999;
        font-size: 12px;
      }

      .badge {
        display: inline-block;
        padding: 4px 8px;
        background: #667eea;
        color: white;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        margin-left: 10px;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Contact Us <span class="badge">Phase A Test</span></h1>
      <p class="subtitle">Testing Forms & Actions with server-side validation</p>

      <!-- Display flash message -->
      <q:if condition="{flash} != ''">
        <div class="alert alert-{flashType}">
          {flash}
        </div>
      </q:if>

      <form method="POST" action="/contact_form">
        <div class="form-group">
          <label for="name">Name <span class="required">*</span></label>
          <input type="text" id="name" name="name" placeholder="Your full name" required />
          <small style="color: #666; font-size: 12px;">Minimum 3 characters</small>
        </div>

        <div class="form-group">
          <label for="email">Email <span class="required">*</span></label>
          <input type="email" id="email" name="email" placeholder="your@email.com" required />
        </div>

        <div class="form-group">
          <label for="message">Message <span class="required">*</span></label>
          <textarea id="message" name="message" placeholder="Write your message here..." required></textarea>
          <small style="color: #666; font-size: 12px;">Minimum 10 characters</small>
        </div>

        <button type="submit">Send Message ✉️</button>
      </form>

      <div class="footer">
        <p>Powered by Quantum Framework</p>
        <p>Server-side validation, flash messages, and redirects working!</p>
      </div>
    </div>
  </body>
  </html>
</q:component>
