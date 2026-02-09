<q:component name="LoginPage" type="page">

  <q:set name="application.blogName" value="Quantum Blog" scope="application" />
  <q:set name="application.basePath" value="/quantum-blog" scope="application" />
  <q:set name="errorMsg" value="" />

  <!-- Handle login action -->
  <q:if condition="{method == 'POST'}">
    <q:set name="inputUser" value="{form.username}" />
    <q:set name="inputPass" value="{form.password}" />

    <q:if condition="{inputUser == 'admin' &amp;&amp; inputPass == 'quantum123'}">
      <q:set name="session.authenticated" value="true" scope="session" />
      <q:set name="session.username" value="admin" scope="session" />
      <q:redirect url="{application.basePath}/admin" />
    </q:if>
    <q:if condition="{inputUser != 'admin' || inputPass != 'quantum123'}">
      <q:set name="errorMsg" value="Invalid credentials. Try admin / quantum123" />
    </q:if>
  </q:if>

  <html>
  <head>
    <title>Login - {application.blogName}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;display=swap');

      * { margin: 0; padding: 0; box-sizing: border-box; }
      body {
        font-family: 'Inter', -apple-system, sans-serif;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #312e81 100%);
        color: #e2e8f0; display: flex; align-items: center; justify-content: center;
        min-height: 100vh; position: relative; overflow: hidden;
      }
      body::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background: radial-gradient(circle at 20% 30%, rgba(99,102,241,0.12) 0%, transparent 50%),
                    radial-gradient(circle at 80% 70%, rgba(139,92,246,0.08) 0%, transparent 50%);
      }

      .login-wrapper { position: relative; z-index: 1; width: 100%; max-width: 420px; padding: 24px; }

      .login-brand { text-align: center; margin-bottom: 32px; }
      .login-brand .logo-icon {
        background: #6366f1; color: white; width: 48px; height: 48px; border-radius: 12px;
        display: inline-flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 1.4rem; margin-bottom: 12px;
      }
      .login-brand h1 { font-size: 1.4rem; font-weight: 700; color: #fff; }
      .login-brand p { color: #64748b; font-size: 0.9rem; margin-top: 4px; }

      .login-box {
        background: rgba(30,41,59,0.8); backdrop-filter: blur(20px);
        border: 1px solid rgba(99,102,241,0.2); border-radius: 16px; padding: 36px;
      }

      .form-group { margin-bottom: 20px; }
      .form-group label { display: block; font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
      .form-group input {
        width: 100%; padding: 12px 16px; border: 1px solid #334155; border-radius: 10px;
        background: rgba(15,23,42,0.6); color: #e2e8f0; font-size: 0.95rem;
        font-family: inherit; transition: all 0.2s;
      }
      .form-group input:focus { outline: none; border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,0.2); }
      .form-group input::placeholder { color: #475569; }

      .btn-login {
        width: 100%; padding: 14px; border: none; border-radius: 10px;
        background: linear-gradient(135deg, #6366f1, #7c3aed); color: white;
        font-size: 0.95rem; font-weight: 700; cursor: pointer; transition: all 0.2s;
        font-family: inherit;
      }
      .btn-login:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(99,102,241,0.35); }

      .error {
        background: rgba(127,29,29,0.3); border: 1px solid rgba(153,27,27,0.5);
        color: #fca5a5; padding: 12px 16px; border-radius: 10px; margin-bottom: 20px;
        text-align: center; font-size: 0.85rem; font-weight: 500;
      }

      .hint {
        text-align: center; margin-top: 20px; color: #475569; font-size: 0.8rem;
        padding: 10px; background: rgba(15,23,42,0.4); border-radius: 8px;
      }
      .hint strong { color: #94a3b8; }

      .back-link { text-align: center; margin-top: 20px; }
      .back-link a { color: #64748b; font-size: 0.85rem; text-decoration: none; transition: color 0.2s; }
      .back-link a:hover { color: #818cf8; }
    </style>
  </head>
  <body>

    <div class="login-wrapper">
      <div class="login-brand">
        <div class="logo-icon">Q</div>
        <h1>{application.blogName}</h1>
        <p>Sign in to manage posts</p>
      </div>

      <div class="login-box">
        <q:if condition="{errorMsg != ''}">
          <div class="error">{errorMsg}</div>
        </q:if>

        <form method="POST" action="{application.basePath}/login">
          <div class="form-group">
            <label>Username</label>
            <input type="text" name="username" placeholder="Enter username" required="required" />
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" placeholder="Enter password" required="required" />
          </div>
          <button type="submit" class="btn-login">Sign In</button>
        </form>

        <div class="hint">Demo credentials: <strong>admin</strong> / <strong>quantum123</strong></div>

        <div class="back-link">
          <a href="{application.basePath}/">&#8592; Back to blog</a>
        </div>
      </div>
    </div>

  </body>
  </html>

</q:component>
