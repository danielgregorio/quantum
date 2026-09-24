<q:component name="EmailDemo">
  <!-- Phase I: Email Sending Demo -->

  <q:param name="flash" type="string" default="" />
  <q:param name="flashType" type="string" default="info" />

  <q:action name="sendEmail" method="POST">
    <q:param name="recipientEmail" type="email" required="true" />
    <q:param name="recipientName" type="string" required="true" />
    <q:param name="emailSubject" type="string" required="true" />
    <q:param name="emailMessage" type="string" required="true" minlength="10" />

    <!-- Send email using q:mail -->
    <q:mail to="{recipientEmail}"
            from="noreply@quantum.dev"
            subject="{emailSubject}">
      <h1>Hello {recipientName}!</h1>
      <p>{emailMessage}</p>
      <hr />
      <p style="color: #666; font-size: 12px;">
        This email was sent from Quantum Framework - Phase I Email Demo
      </p>
    </q:mail>

    <!-- Redirect with success message -->
    <q:redirect url="/email_demo"
                flash="Email sent successfully to {recipientEmail}!"
                flashType="success" />
  </q:action>

  <html>
  <head>
    <title>Email Demo - Phase I</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        max-width: 800px;
        margin: 50px auto;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
      }
      .container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 40px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      }
      .alert {
        padding: 15px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        font-size: 14px;
      }
      .alert-success {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
      }
      .email-form {
        background: rgba(255, 255, 255, 0.2);
        padding: 30px;
        border-radius: 10px;
        margin: 20px 0;
      }
      .form-group {
        margin-bottom: 20px;
      }
      label {
        display: block;
        margin-bottom: 8px;
        font-weight: 600;
      }
      input[type="email"],
      input[type="text"],
      textarea {
        width: 100%;
        padding: 12px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.9);
        font-size: 14px;
        box-sizing: border-box;
      }
      textarea {
        min-height: 120px;
        resize: vertical;
      }
      button {
        background: #4caf50;
        color: white;
        border: none;
        padding: 12px 30px;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        margin-top: 10px;
      }
      button:hover {
        background: #45a049;
      }
      .info-box {
        background: rgba(33, 150, 243, 0.2);
        border-left: 4px solid #2196f3;
        padding: 15px;
        border-radius: 5px;
        margin: 20px 0;
      }
      ul {
        margin: 10px 0;
        padding-left: 20px;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>📧 Phase I - Email Sending Demo</h1>

      <q:if condition="{flash} != ''">
        <div class="alert alert-{flashType}">
          {flash}
        </div>
      </q:if>

      <div class="info-box">
        <strong>Where the mail goes</strong><br />
        <code>mail:</code> in quantum.config.yaml says which server sends it (MAIL-1).<br />
        With <code>host: log</code> each message is written to the log instead.
      </div>

      <div class="email-form">
        <h2>Send Test Email</h2>
        <form method="POST" action="/email_demo">
          <div class="form-group">
            <label for="recipientEmail">Recipient Email *</label>
            <input
              type="email"
              id="recipientEmail"
              name="recipientEmail"
              placeholder="user@example.com"
              required="required"
            />
          </div>

          <div class="form-group">
            <label for="recipientName">Recipient Name *</label>
            <input
              type="text"
              id="recipientName"
              name="recipientName"
              placeholder="John Doe"
              required="required"
            />
          </div>

          <div class="form-group">
            <label for="emailSubject">Subject *</label>
            <input
              type="text"
              id="emailSubject"
              name="emailSubject"
              placeholder="Welcome to Quantum!"
              required="required"
            />
          </div>

          <div class="form-group">
            <label for="emailMessage">Message *</label>
            <textarea
              id="emailMessage"
              name="emailMessage"
              placeholder="Enter your email message here..."
              required="required"
              minlength="10"
            ></textarea>
          </div>

          <button type="submit">📤 Send Email</button>
        </form>
      </div>

      <div class="info-box">
        <h3>✅ Phase I Features Demonstrated:</h3>
        <ul>
          <li><code>&lt;q:mail to="{email}" subject="{subject}"&gt;</code> - Email sending tag</li>
          <li>HTML email body with databinding</li>
          <li>From address configuration</li>
          <li><code>host: log</code> for development: messages go to the log</li>
          <li>Flash message feedback</li>
        </ul>
      </div>

      <div class="info-box">
        <h3>🔧 SMTP Configuration (quantum.config.yaml):</h3>
        <pre>mail:
  host: smtp.example.com   (or: log)
  port: 587
  username: you@example.com
  password: (from the environment, see CFG-1)
  from: noreply@example.com</pre>
      </div>

      <a href="/" style="color: white;">← Back to Home</a>
    </div>
  </body>
  </html>
</q:component>
