<?xml version="1.0" encoding="UTF-8"?>
<!--
  Python Scripting Example

  Demonstrates the q:python feature that allows embedding native Python code
  inside Quantum components, inspired by ColdFusion's <cfscript>.

  The magical 'q' object bridges Python code to the Quantum context.
-->

<q:component name="PythonScriptingDemo">
    <!-- Import Python modules -->
    <q:pyimport module="json" />
    <q:pyimport module="datetime" as="dt" />
    <q:pyimport module="re" />
    <q:pyimport module="math" names="sqrt,pow,pi" />

    <!-- Define a custom decorator -->
    <q:decorator name="logged">
        import time
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            print(f"Function took {time.time() - start:.2f}s")
            return result
        return wrapper
    </q:decorator>

    <!-- Define a custom class -->
    <q:class name="Calculator">
        def __init__(self):
            self.history = []

        def add(self, a, b):
            result = a + b
            self.history.append(f"{a} + {b} = {result}")
            return result

        def multiply(self, a, b):
            result = a * b
            self.history.append(f"{a} * {b} = {result}")
            return result

        def get_history(self):
            return self.history
    </q:class>

    <!-- Define another class with decorators -->
    <q:class name="UserValidator" decorators="logged">
        def validate_email(self, email):
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, email))

        def validate_age(self, age):
            return isinstance(age, int) and 0 &lt; age &lt; 150

        def validate_user(self, user_data):
            return (
                self.validate_email(user_data.get('email', '')) and
                self.validate_age(user_data.get('age', 0))
            )
    </q:class>

    <!-- Initialize variables using declarative Quantum syntax -->
    <q:set name="title" value="Python Scripting Demo" />
    <q:set name="items" value="[]" />

    <!-- Use Python for complex logic -->
    <q:python>
        # Access Quantum variables via the 'q' object
        q.info("Starting Python scripting demo")

        # Use the Calculator class we defined
        calc = Calculator()

        # Perform calculations
        sum_result = calc.add(10, 20)
        mul_result = calc.multiply(5, 6)

        # Export results back to Quantum context
        q.sum_result = sum_result
        q.mul_result = mul_result
        q.calc_history = calc.get_history()

        # Use imported math functions
        q.circle_area = pi * pow(5, 2)
        q.sqrt_result = sqrt(144)

        # Work with dates
        q.current_time = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Process JSON data
        sample_data = {
            "users": [
                {"name": "Alice", "email": "alice@example.com", "age": 28},
                {"name": "Bob", "email": "bob@example.com", "age": 35},
                {"name": "Charlie", "email": "invalid-email", "age": 200}
            ]
        }

        # Validate users
        validator = UserValidator()
        valid_users = []
        invalid_users = []

        for user in sample_data["users"]:
            if validator.validate_user(user):
                valid_users.append(user["name"])
            else:
                invalid_users.append(user["name"])

        q.valid_users = valid_users
        q.invalid_users = invalid_users
        q.sample_json = json.dumps(sample_data, indent=2)

        q.info(f"Validated {len(valid_users)} users successfully")
    </q:python>

    <!-- Display results using Quantum UI -->
    <ui:window title="{title}">
        <ui:vbox padding="lg" gap="md">
            <ui:text size="2xl" weight="bold">{title}</ui:text>

            <ui:card>
                <ui:card-header>
                    <ui:text weight="semibold">Calculator Results</ui:text>
                </ui:card-header>
                <ui:card-body>
                    <ui:text>Sum: 10 + 20 = {sum_result}</ui:text>
                    <ui:text>Multiply: 5 x 6 = {mul_result}</ui:text>
                    <ui:text>History: {calc_history}</ui:text>
                </ui:card-body>
            </ui:card>

            <ui:card>
                <ui:card-header>
                    <ui:text weight="semibold">Math Functions</ui:text>
                </ui:card-header>
                <ui:card-body>
                    <ui:text>Circle Area (r=5): {circle_area}</ui:text>
                    <ui:text>Square Root of 144: {sqrt_result}</ui:text>
                </ui:card-body>
            </ui:card>

            <ui:card>
                <ui:card-header>
                    <ui:text weight="semibold">Date/Time</ui:text>
                </ui:card-header>
                <ui:card-body>
                    <ui:text>Current Time: {current_time}</ui:text>
                </ui:card-body>
            </ui:card>

            <ui:card>
                <ui:card-header>
                    <ui:text weight="semibold">User Validation</ui:text>
                </ui:card-header>
                <ui:card-body>
                    <ui:text color="success">Valid Users: {valid_users}</ui:text>
                    <ui:text color="danger">Invalid Users: {invalid_users}</ui:text>
                </ui:card-body>
            </ui:card>

            <ui:card>
                <ui:card-header>
                    <ui:text weight="semibold">Sample JSON</ui:text>
                </ui:card-header>
                <ui:card-body>
                    <ui:code language="json">{sample_json}</ui:code>
                </ui:card-body>
            </ui:card>
        </ui:vbox>
    </ui:window>
</q:component>
