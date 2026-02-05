<q:application id="basic-tests" type="testing">

    <qtest:fixture name="users" scope="module">
        [{"id": 1, "name": "Alice", "email": "alice@test.com"}, {"id": 2, "name": "Bob", "email": "bob@test.com"}]
    </qtest:fixture>

    <qtest:suite name="MathOperations">
        <qtest:case name="addition works correctly">
            <qtest:expect var="1 + 1" equals="2" />
            <qtest:expect var="100 + 200" equals="300" />
        </qtest:case>

        <qtest:case name="string concatenation">
            <qtest:expect var="'hello' + ' ' + 'world'" equals="'hello world'" />
        </qtest:case>

        <qtest:case name="list operations">
            <qtest:expect var="len([1, 2, 3])" equals="3" />
        </qtest:case>
    </qtest:suite>

    <qtest:suite name="UserValidation">
        <qtest:case name="user has required fields">
            <qtest:expect var="'name' in {'name': 'Alice', 'email': 'a@b.com'}" equals="True" />
            <qtest:expect var="'email' in {'name': 'Alice', 'email': 'a@b.com'}" equals="True" />
        </qtest:case>

        <qtest:scenario name="user registration flow">
            <qtest:given>a new user with valid data</qtest:given>
            <qtest:when>the user submits the registration form</qtest:when>
            <qtest:then>the user should be created successfully
                <qtest:expect var="True" equals="True" />
            </qtest:then>
        </qtest:scenario>
    </qtest:suite>

</q:application>
