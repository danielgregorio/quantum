<q:component name="Header">
  <!-- Site header. The links change with the session. -->
  <header>
    <div class="header-inner">
      <a href="/" class="logo">
        <span class="logo-icon">Q</span>
        Quantum Blog
      </a>
      <nav>
        <a href="/">Home</a>
        <a href="/search">Search</a>
        <q:if condition="session.authenticated">
          <a href="/admin">Admin</a>
          <a href="/logout">Logout</a>
        </q:if>
        <q:else>
          <a href="/login">Login</a>
        </q:else>
      </nav>
    </div>
  </header>
</q:component>
