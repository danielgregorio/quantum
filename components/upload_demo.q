<q:component name="UploadDemo">
  <!-- Phase H: File Upload Demo -->

  <q:param name="flash" type="string" default="" />
  <q:param name="flashType" type="string" default="info" />

  <q:action name="uploadFile" method="POST">
    <q:param name="avatar" type="file" required="true" />

    <!-- Upload file -->
    <q:file action="upload"
            file="{avatar}"
            destination="./uploads/avatars/"
            nameConflict="makeUnique"
            result="uploadResult" />

    <!-- Redirect with success message -->
    <q:redirect url="/upload_demo"
                flash="File uploaded successfully: {uploadResult.filename}"
                flashType="success" />
  </q:action>

  <html>
  <head>
    <title>File Upload Demo - Phase H</title>
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
      .alert-error {
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
      }
      .upload-form {
        background: rgba(255, 255, 255, 0.2);
        padding: 30px;
        border-radius: 10px;
        margin: 20px 0;
      }
      input[type="file"] {
        width: 100%;
        padding: 12px;
        border: 2px dashed rgba(255, 255, 255, 0.5);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.1);
        color: white;
        cursor: pointer;
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
        margin-top: 20px;
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
      <h1>📁 Phase H - File Upload Demo</h1>

      <q:if condition="{flash} != ''">
        <div class="alert alert-{flashType}">
          {flash}
        </div>
      </q:if>

      <div class="upload-form">
        <h2>Upload Avatar</h2>
        <form method="POST" action="/upload_demo" enctype="multipart/form-data">
          <input
            type="file"
            name="avatar"
            accept="image/*"
            required="required"
          />
          <button type="submit">📤 Upload File</button>
        </form>
      </div>

      <div class="info-box">
        <h3>✅ Phase H Features Demonstrated:</h3>
        <ul>
          <li><code>&lt;q:param type="file" /&gt;</code> - File parameter in actions</li>
          <li><code>&lt;q:file action="upload" /&gt;</code> - File upload handling</li>
          <li><code>nameConflict="makeUnique"</code> - Auto-generate unique filenames</li>
          <li><code>destination="./uploads/avatars/"</code> - Custom upload directory</li>
          <li>File validation (size, type, extension)</li>
          <li>Flash messages for upload feedback</li>
        </ul>
      </div>

      <div class="info-box">
        <h3>🧪 How It Works:</h3>
        <ul>
          <li><strong>Select a file</strong> - Browser file picker</li>
          <li><strong>Submit form</strong> - POST to action</li>
          <li><strong>File validation</strong> - Size/type checks</li>
          <li><strong>Unique naming</strong> - UUID added if file exists</li>
          <li><strong>Secure storage</strong> - Saved to ./uploads/avatars/</li>
          <li><strong>Flash message</strong> - Success confirmation</li>
        </ul>
      </div>

      <a href="/" style="color: white;">← Back to Home</a>
    </div>
  </body>
  </html>
</q:component>
