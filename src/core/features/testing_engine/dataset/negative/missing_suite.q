<q:application id="bad-test" type="testing">
    <!-- Missing qtest:suite - test cases should be inside a suite -->
    <qtest:case name="orphan test">
        <qtest:expect var="true" equals="true" />
    </qtest:case>
</q:application>
