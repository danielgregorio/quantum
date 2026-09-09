<q:component name="ContactSuccess">
  <!-- Success page after form submission -->

  <q:param name="flash" type="string" default="" />
  <q:param name="flashType" type="string" default="success" />

  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Success!</title>
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
        padding: 60px 40px;
        text-align: center;
      }

      .success-icon {
        font-size: 80px;
        margin-bottom: 20px;
      }

      h1 {
        color: #28a745;
        margin-bottom: 20px;
        font-size: 32px;
      }

      .message {
        padding: 20px;
        background: #d4edda;
        border-left: 4px solid #28a745;
        border-radius: 5px;
        color: #155724;
        margin-bottom: 30px;
        text-align: left;
      }

      .button {
        display: inline-block;
        padding: 14px 30px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        text-decoration: none;
        border-radius: 5px;
        font-weight: 600;
        transition: transform 0.2s;
      }

      .button:hover {
        transform: translateY(-2px);
      }

      .footer {
        margin-top: 30px;
        color: #999;
        font-size: 12px;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="success-icon">✅</div>
      <h1>Success!</h1>

      <q:if condition="{flash} != ''">
        <div class="message">
          {flash}
        </div>
      </q:if>

      <p style="color: #666; margin-bottom: 30px;">
        We've received your message and will get back to you soon.
      </p>

      <a href="/contact_form" class="button">← Send Another Message</a>

      <div class="footer">
        <p>Phase A: Forms & Actions ✅</p>
        <p>Flash messages working perfectly!</p>
      </div>
    </div>
  </body>
  </html>
</q:component>
