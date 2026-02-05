<q:application id="api-tests" type="testing">

    <qtest:browser-config engine="chromium" headless="true" base-url="http://localhost:8080" />

    <qtest:fixture name="api_data">
        {"token": "test-jwt-token-123", "user_id": 42}
    </qtest:fixture>

    <qtest:suite name="APIContracts" browser="true">

        <qtest:case name="GET /api/users returns list" browser="true">
            <qtest:intercept url="**/api/users" method="GET">
                <qtest:respond status="200" content-type="application/json">
                    [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
                </qtest:respond>
            </qtest:intercept>
            <qtest:navigate to="/users" />
            <qtest:expect selector=".user-item" count="2" />
        </qtest:case>

        <qtest:case name="POST /api/users creates user" browser="true">
            <qtest:intercept url="**/api/users" method="POST">
                <qtest:respond status="201" content-type="application/json">
                    {"id": 3, "name": "Charlie"}
                </qtest:respond>
            </qtest:intercept>
            <qtest:navigate to="/users/new" />
            <qtest:fill selector="#name" value="Charlie" />
            <qtest:click selector="button[type=submit]" />
            <qtest:wait-for selector=".success" state="visible" />
        </qtest:case>

        <qtest:case name="handles API errors gracefully" browser="true">
            <qtest:intercept url="**/api/users" method="GET">
                <qtest:respond status="500" content-type="application/json">
                    {"error": "Internal Server Error"}
                </qtest:respond>
            </qtest:intercept>
            <qtest:navigate to="/users" />
            <qtest:expect selector=".error-state" visible="true" />
            <qtest:expect selector=".error-state" text-contains="error" />
        </qtest:case>

        <qtest:case name="handles slow responses" browser="true">
            <qtest:intercept url="**/api/data" method="GET" delay="3000">
                <qtest:respond status="200" content-type="application/json">
                    {"data": "loaded"}
                </qtest:respond>
            </qtest:intercept>
            <qtest:navigate to="/data" />
            <qtest:expect selector=".loading-spinner" visible="true" />
            <qtest:wait-for selector=".data-content" state="visible" timeout="5000" />
        </qtest:case>
    </qtest:suite>

    <qtest:suite name="NetworkSpying" browser="true">
        <qtest:case name="tracks API calls" browser="true">
            <qtest:intercept url="**/api/analytics" spy="true" />
            <qtest:navigate to="/" />
            <qtest:click text="Track Event" />
        </qtest:case>
    </qtest:suite>

</q:application>
