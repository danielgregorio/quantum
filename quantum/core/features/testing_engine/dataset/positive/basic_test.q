<q:application id="basic-tests" type="testing">
    <qtest:suite name="MathUtils">
        <qtest:case name="addition works">
            <qtest:expect var="1 + 1" equals="2" />
        </qtest:case>
        <qtest:case name="string contains">
            <qtest:expect var="'hello world'" text-contains="hello" />
        </qtest:case>
    </qtest:suite>
</q:application>
