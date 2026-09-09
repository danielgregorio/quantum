<q:application id="browser-tests" type="testing">

    <qtest:browser-config
        engine="chromium"
        headless="true"
        base-url="http://localhost:8080"
        viewport-width="1280"
        viewport-height="720"
        timeout="30000"
    />

    <qtest:suite name="HomePage" browser="true">
        <qtest:before-each>
            <qtest:navigate to="/" />
        </qtest:before-each>

        <qtest:case name="page loads successfully" browser="true">
            <qtest:expect selector="h1" visible="true" />
            <qtest:expect selector="h1" text="Welcome" />
        </qtest:case>

        <qtest:case name="navigation menu works" browser="true">
            <qtest:click text="About" role="link" />
            <qtest:wait-for url="**/about" />
            <qtest:expect selector="h1" text="About Us" />
        </qtest:case>

        <qtest:case name="search functionality" browser="true">
            <qtest:fill selector="#search-input" value="quantum framework" />
            <qtest:keyboard press="Enter" />
            <qtest:wait-for selector=".search-results" state="visible" />
            <qtest:expect selector=".search-results .result" count="3" />
        </qtest:case>

        <qtest:case name="form submission" browser="true">
            <qtest:navigate to="/contact" />
            <qtest:fill selector="#name" value="John Doe" />
            <qtest:fill selector="#email" value="john@example.com" />
            <qtest:fill selector="#message" value="Hello from Quantum tests!" />
            <qtest:click selector="button[type=submit]" />
            <qtest:wait-for selector=".success-message" state="visible" />
            <qtest:expect selector=".success-message" text-contains="Thank you" />
        </qtest:case>

        <qtest:case name="screenshot on key pages" browser="true">
            <qtest:screenshot name="homepage" full-page="true" />
            <qtest:navigate to="/about" />
            <qtest:screenshot name="about-page" />
        </qtest:case>
    </qtest:suite>

    <qtest:suite name="Authentication" browser="true">
        <qtest:case name="login with valid credentials" browser="true">
            <qtest:navigate to="/login" />
            <qtest:fill selector="#username" value="admin" />
            <qtest:fill selector="#password" value="password123" />
            <qtest:click selector="button[type=submit]" />
            <qtest:wait-for url="**/dashboard" />
            <qtest:expect selector=".user-name" text="admin" />
        </qtest:case>

        <qtest:case name="login with invalid credentials" browser="true">
            <qtest:navigate to="/login" />
            <qtest:fill selector="#username" value="wrong" />
            <qtest:fill selector="#password" value="invalid" />
            <qtest:click selector="button[type=submit]" />
            <qtest:expect selector=".error-message" visible="true" />
            <qtest:expect selector=".error-message" text-contains="Invalid" />
        </qtest:case>
    </qtest:suite>

</q:application>
