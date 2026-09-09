<q:component name="LoginPage" type="page">
  <!--
    Quantum Blog - Login Page
    Features:
    - Database-driven authentication
    - Password hashing verification
    - Session management
    - Login attempt tracking
    - Remember me option
  -->

  <q:set name="application.blogName" value="Quantum Blog" scope="application" />
  <q:set name="application.basePath" value="/quantum-blog" scope="application" />
  <q:set name="errorMsg" value="" />
  <q:set name="loginSuccess" value="false" />

  <!-- Already logged in? Redirect to admin -->
  <q:if condition="{session.authenticated}">
    <q:redirect url="{application.basePath}/admin" />
  </q:if>

  <!-- Handle login action -->
  <q:action name="login" method="POST">
    <q:validate field="username" required="true" minLength="2" maxLength="100" />
    <q:validate field="password" required="true" minLength="4" maxLength="255" />

    <!-- Query user from database -->
    <q:query name="authUser" datasource="blog-db">
      SELECT
        id,
        username,
        email,
        display_name,
        password_hash,
        role,
        is_active
      FROM users
      WHERE (username = :username OR email = :username)
        AND is_active = TRUE

      <q:param name="username" value="{form.username}" type="string" />
    </q:query>

    <q:if condition="{authUser_result.recordCount > 0}">
      <!-- Verify password hash -->
      <q:set name="passwordValid" value="{crypto.verifyHash(form.password, authUser.password_hash)}" />

      <q:if condition="{passwordValid}">
        <!-- Set session variables -->
        <q:set name="session.authenticated" value="true" scope="session" />
        <q:set name="session.userId" value="{authUser.id}" scope="session" />
        <q:set name="session.username" value="{authUser.username}" scope="session" />
        <q:set name="session.displayName" value="{authUser.display_name}" scope="session" />
        <q:set name="session.role" value="{authUser.role}" scope="session" />

        <!-- Update last login timestamp -->
        <q:query name="updateLogin" datasource="blog-db" type="execute">
          UPDATE users SET last_login = NOW() WHERE id = :userId
          <q:param name="userId" value="{authUser.id}" type="integer" />
        </q:query>

        <!-- Log successful login -->
        <q:query name="logLogin" datasource="blog-db" type="execute">
          INSERT INTO login_attempts (user_id, ip_address, success)
          VALUES (:userId, :ip, TRUE)
          <q:param name="userId" value="{authUser.id}" type="integer" />
          <q:param name="ip" value="{request.clientIp}" type="string" />
        </q:query>

        <q:set name="loginSuccess" value="true" />
        <q:redirect url="{application.basePath}/admin" />
      </q:if>

      <q:if condition="{!passwordValid}">
        <q:set name="errorMsg" value="Invalid password. Please try again." />
      </q:if>
    </q:if>

    <q:if condition="{authUser_result.recordCount == 0}">
      <q:set name="errorMsg" value="User not found. Check your username or email." />
    </q:if>
  </q:action>

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

      .remember-row { display: flex; align-items: center; gap: 8px; margin-bottom: 20px; }
      .remember-row input[type="checkbox"] { width: 16px; height: 16px; accent-color: #6366f1; }
      .remember-row label { font-size: 0.85rem; color: #94a3b8; text-transform: none; letter-spacing: 0; }

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
          <input type="hidden" name="action" value="login" />
          <div class="form-group">
            <label>Username or Email</label>
            <input type="text" name="username" placeholder="Enter username or email" required="required" />
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" placeholder="Enter password" required="required" />
          </div>
          <div class="remember-row">
            <input type="checkbox" name="remember" id="remember" />
            <label for="remember">Remember me</label>
          </div>
          <button type="submit" class="btn-login">Sign In</button>
        </form>

        <div class="hint">Demo: <strong>admin</strong> / <strong>quantum123</strong></div>

        <div class="back-link">
          <a href="{application.basePath}/">&#8592; Back to blog</a>
        </div>
      </div>
    </div>

  </body>
  </html>

</q:component>
