<?xml version="1.0" encoding="UTF-8"?>
<!--
    Form Validation Example

    Demonstrates the declarative form validation system in Quantum UI Engine.
    Includes HTML5 validation attributes, custom validators, and error display modes.
-->
<q:application id="FormValidationDemo" type="ui">
    <ui:window title="Registration Form with Validation">
        <ui:panel title="User Registration">
            <!--
                Form with validation attributes:
                - validation="both" - Validate on client and server
                - error-display="both" - Show inline errors + summary
            -->
            <ui:form validation="both" error-display="both" on-submit="handleSubmit()">

                <!-- Custom validators defined at form level -->
                <ui:validator name="passwordStrength"
                              pattern="^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$"
                              message="Password must have at least 8 characters with uppercase, lowercase, and number" />

                <ui:validator name="passwordMatch"
                              match="password"
                              message="Passwords must match" />

                <ui:validator name="ageRange"
                              field="age"
                              min="18"
                              max="120"
                              message="Age must be between 18 and 120" />

                <!-- Email field with HTML5 validation -->
                <ui:formitem label="Email">
                    <ui:input bind="email"
                              type="email"
                              required="true"
                              placeholder="user@example.com"
                              error-message="Please enter a valid email address" />
                </ui:formitem>

                <!-- Username with pattern and length constraints -->
                <ui:formitem label="Username">
                    <ui:input bind="username"
                              required="true"
                              minlength="3"
                              maxlength="20"
                              pattern="[a-zA-Z0-9_]+"
                              placeholder="alphanumeric_only"
                              error-message="Username must be 3-20 alphanumeric characters or underscores" />
                </ui:formitem>

                <!-- Password with custom validator -->
                <ui:formitem label="Password">
                    <ui:input bind="password"
                              type="password"
                              required="true"
                              validators="passwordStrength"
                              placeholder="8+ characters, mixed case + number" />
                </ui:formitem>

                <!-- Confirm Password with match validator -->
                <ui:formitem label="Confirm Password">
                    <ui:input bind="confirmPassword"
                              type="password"
                              required="true"
                              validators="passwordMatch"
                              error-message="Passwords do not match" />
                </ui:formitem>

                <!-- Age with min/max constraints -->
                <ui:formitem label="Age">
                    <ui:input bind="age"
                              type="number"
                              min="18"
                              max="120"
                              placeholder="18-120"
                              error-message="You must be at least 18 years old" />
                </ui:formitem>

                <!-- Phone with pattern -->
                <ui:formitem label="Phone (Optional)">
                    <ui:input bind="phone"
                              type="tel"
                              pattern="\d{10,11}"
                              placeholder="10-11 digits"
                              error-message="Phone must be 10-11 digits" />
                </ui:formitem>

                <!-- Website with URL validation -->
                <ui:formitem label="Website (Optional)">
                    <ui:input bind="website"
                              type="url"
                              placeholder="https://example.com" />
                </ui:formitem>

                <ui:hbox gap="12" justify="end">
                    <ui:button variant="secondary">Cancel</ui:button>
                    <ui:button variant="primary">Register</ui:button>
                </ui:hbox>
            </ui:form>
        </ui:panel>
    </ui:window>
</q:application>
