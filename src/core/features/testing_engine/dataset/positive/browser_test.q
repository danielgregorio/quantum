<q:application id="browser-tests" type="testing">
    <qtest:browser-config engine="chromium" headless="true" base-url="http://localhost:8080" />

    <qtest:suite name="HomePage" browser="true">
        <qtest:case name="loads correctly" browser="true">
            <qtest:navigate to="/" />
            <qtest:expect selector="h1" visible="true" />
            <qtest:expect selector="h1" text="Welcome" />
        </qtest:case>
    </qtest:suite>
</q:application>
