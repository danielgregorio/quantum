<q:component name="BlogHeader" type="partial">
  <!--
    Shared header component for the Quantum Blog
    Includes navigation with auth-aware links
  -->

  <header>
    <div class="header-inner">
      <a href="{application.basePath}/" class="logo">
        <span class="logo-icon">Q</span>
        {application.blogName}
      </a>
      <nav>
        <a href="{application.basePath}/">Home</a>
        <a href="{application.basePath}/search">Search</a>
        <q:if condition="{session.authenticated}">
          <a href="{application.basePath}/admin">Admin</a>
          <a href="{application.basePath}/logout">Logout</a>
        </q:if>
        <q:if condition="{!session.authenticated}">
          <a href="{application.basePath}/login">Login</a>
        </q:if>
      </nav>
    </div>
  </header>

</q:component>
