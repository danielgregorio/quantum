"""
Tests for Quantum UI Form Validation System

Tests parsing of validation attributes on ui:input and ui:form,
as well as the custom ui:validator tag.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from core.parser import QuantumParser
from core.ast_nodes import ApplicationNode
from core.features.ui_engine.src.ast_nodes import (
    UIFormNode, UIInputNode, UIValidatorNode, UIFormItemNode
)
from runtime.ui_html_adapter import UIHtmlAdapter


@pytest.fixture
def parser():
    return QuantumParser()


def parse_ui(parser, body: str) -> ApplicationNode:
    """Helper: wrap body in <q:application type="ui"> and parse."""
    source = f'<q:application id="test" type="ui">{body}</q:application>'
    return parser.parse(source)


# ============================================
# Input Validation Attributes Parsing
# ============================================

class TestInputValidationParsing:
    """Test parsing of validation attributes on ui:input."""

    def test_required_attribute(self, parser):
        """Test parsing required attribute."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="email" required="true" />
            </ui:window>
        ''')
        window = app.ui_windows[0]
        input_node = window.children[0]
        assert isinstance(input_node, UIInputNode)
        assert input_node.required is True

    def test_minlength_maxlength(self, parser):
        """Test parsing minlength and maxlength attributes."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="username" minlength="3" maxlength="20" />
            </ui:window>
        ''')
        window = app.ui_windows[0]
        input_node = window.children[0]
        assert input_node.minlength == 3
        assert input_node.maxlength == 20

    def test_min_max_for_number(self, parser):
        """Test parsing min and max attributes for number inputs."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="age" type="number" min="18" max="120" />
            </ui:window>
        ''')
        window = app.ui_windows[0]
        input_node = window.children[0]
        assert input_node.input_type == 'number'
        assert input_node.min == '18'
        assert input_node.max == '120'

    def test_pattern_attribute(self, parser):
        """Test parsing pattern attribute for regex validation."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="phone" pattern="\\d{10}" />
            </ui:window>
        ''')
        window = app.ui_windows[0]
        input_node = window.children[0]
        assert input_node.pattern == '\\d{10}'

    def test_error_message_attribute(self, parser):
        """Test parsing custom error message."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="email" required="true"
                          error-message="Email is required" />
            </ui:window>
        ''')
        window = app.ui_windows[0]
        input_node = window.children[0]
        assert input_node.error_message == 'Email is required'

    def test_custom_validators_attribute(self, parser):
        """Test parsing validators attribute (comma-separated list)."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="password" validators="strongPassword,noSpaces" />
            </ui:window>
        ''')
        window = app.ui_windows[0]
        input_node = window.children[0]
        assert input_node.validators == ['strongPassword', 'noSpaces']

    def test_combined_validation_attributes(self, parser):
        """Test parsing multiple validation attributes together."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="username"
                          required="true"
                          minlength="3"
                          maxlength="15"
                          pattern="[a-zA-Z0-9_]+"
                          error-message="Invalid username format" />
            </ui:window>
        ''')
        window = app.ui_windows[0]
        input_node = window.children[0]
        assert input_node.required is True
        assert input_node.minlength == 3
        assert input_node.maxlength == 15
        assert input_node.pattern == '[a-zA-Z0-9_]+'
        assert input_node.error_message == 'Invalid username format'


# ============================================
# Form Validation Attributes Parsing
# ============================================

class TestFormValidationParsing:
    """Test parsing of validation attributes on ui:form."""

    def test_validation_mode_client(self, parser):
        """Test parsing validation mode: client."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form validation="client">
                    <ui:input bind="name" required="true" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        assert isinstance(form, UIFormNode)
        assert form.validation_mode == 'client'

    def test_validation_mode_server(self, parser):
        """Test parsing validation mode: server."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form validation="server">
                    <ui:input bind="name" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        assert form.validation_mode == 'server'

    def test_validation_mode_both(self, parser):
        """Test parsing validation mode: both (default)."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form>
                    <ui:input bind="name" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        assert form.validation_mode == 'both'

    def test_error_display_inline(self, parser):
        """Test parsing error display mode: inline."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form error-display="inline">
                    <ui:input bind="name" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        assert form.error_display == 'inline'

    def test_error_display_summary(self, parser):
        """Test parsing error display mode: summary."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form error-display="summary">
                    <ui:input bind="name" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        assert form.error_display == 'summary'

    def test_novalidate_attribute(self, parser):
        """Test parsing novalidate attribute."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form novalidate="true">
                    <ui:input bind="name" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        assert form.novalidate is True


# ============================================
# Validator Tag Parsing
# ============================================

class TestValidatorParsing:
    """Test parsing of ui:validator tag."""

    def test_pattern_validator(self, parser):
        """Test parsing pattern-based validator."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form>
                    <ui:validator name="phone" pattern="^\\d{10}$"
                                  message="Phone must be 10 digits" />
                    <ui:input bind="phone" validators="phone" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        assert len(form.validators) == 1
        validator = form.validators[0]
        assert isinstance(validator, UIValidatorNode)
        assert validator.name == 'phone'
        assert validator.pattern == '^\\d{10}$'
        assert validator.message == 'Phone must be 10 digits'

    def test_match_validator(self, parser):
        """Test parsing match validator for password confirmation."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form>
                    <ui:validator name="confirmMatch" match="password"
                                  message="Passwords must match" />
                    <ui:input bind="password" type="password" />
                    <ui:input bind="confirmPassword" validators="confirmMatch" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        validator = form.validators[0]
        assert validator.name == 'confirmMatch'
        assert validator.match == 'password'
        assert validator.message == 'Passwords must match'

    def test_type_validator(self, parser):
        """Test parsing type-based validator."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form>
                    <ui:validator name="email" type="email"
                                  message="Invalid email format" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        validator = form.validators[0]
        assert validator.name == 'email'
        assert validator.rule_type == 'email'

    def test_expression_validator(self, parser):
        """Test parsing custom expression validator."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form>
                    <ui:validator name="customAge"
                                  expression="parseInt(value) >= 18"
                                  message="Must be 18 or older" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        validator = form.validators[0]
        assert validator.name == 'customAge'
        assert validator.expression == 'parseInt(value) >= 18'

    def test_trigger_attribute(self, parser):
        """Test parsing trigger attribute for validators."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form>
                    <ui:validator name="realtime" pattern=".*" trigger="input" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        validator = form.validators[0]
        assert validator.trigger == 'input'

    def test_field_level_validator(self, parser):
        """Test parsing field-level validator."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form>
                    <ui:validator name="ageCheck" field="age" min="18"
                                  message="Must be at least 18" />
                    <ui:input bind="age" type="number" />
                </ui:form>
            </ui:window>
        ''')
        window = app.ui_windows[0]
        form = window.children[0]
        validator = form.validators[0]
        assert validator.field == 'age'
        assert validator.min == '18'


# ============================================
# HTML Rendering Tests
# ============================================

class TestValidationHTMLRendering:
    """Test HTML output for validation attributes."""

    def test_required_input_renders_html5_attribute(self, parser):
        """Test that required input renders HTML5 required attribute."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="email" required="true" />
            </ui:window>
        ''')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'required' in html

    def test_pattern_input_renders_html5_attribute(self, parser):
        """Test that pattern renders as HTML5 pattern attribute."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="code" pattern="[A-Z]{3}[0-9]{3}" />
            </ui:window>
        ''')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'pattern="[A-Z]{3}[0-9]{3}"' in html

    def test_minlength_maxlength_render_html5_attributes(self, parser):
        """Test that minlength/maxlength render as HTML5 attributes."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="username" minlength="3" maxlength="20" />
            </ui:window>
        ''')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'minlength="3"' in html
        assert 'maxlength="20"' in html

    def test_error_message_container_rendered(self, parser):
        """Test that error message container is rendered for validated inputs."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="email" required="true"
                          error-message="Email is required" />
            </ui:window>
        ''')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-error-message' in html
        assert 'Email is required' in html
        assert 'q-input-wrapper' in html

    def test_form_validation_mode_data_attribute(self, parser):
        """Test that form validation mode is set as data attribute."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form validation="client">
                    <ui:input bind="name" required="true" />
                </ui:form>
            </ui:window>
        ''')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'data-validation="client"' in html

    def test_validation_summary_rendered_for_summary_mode(self, parser):
        """Test that validation summary div is rendered for summary mode."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form error-display="summary">
                    <ui:input bind="name" required="true" />
                </ui:form>
            </ui:window>
        ''')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-validation-summary' in html

    def test_novalidate_attribute_rendered(self, parser):
        """Test that novalidate is rendered on form with client validation."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form validation="client">
                    <ui:input bind="name" required="true" />
                </ui:form>
            </ui:window>
        ''')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'novalidate' in html

    def test_validation_js_included_when_validation_used(self, parser):
        """Test that validation JS is included when form has validation."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:form validation="client">
                    <ui:input bind="email" required="true" />
                </ui:form>
            </ui:window>
        ''')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert '__qValidation' in html

    def test_custom_validators_data_attribute(self, parser):
        """Test that custom validators are added as data attribute."""
        app = parse_ui(parser, '''
            <ui:window title="Test">
                <ui:input bind="password" validators="strong,noSpaces" />
            </ui:window>
        ''')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'data-validators="strong,noSpaces"' in html


# ============================================
# AST Node Validation
# ============================================

class TestASTNodeValidation:
    """Test AST node validation logic."""

    def test_input_minlength_greater_than_maxlength_error(self):
        """Test that minlength > maxlength produces validation error."""
        node = UIInputNode()
        node.minlength = 10
        node.maxlength = 5
        errors = node.validate()
        assert len(errors) == 1
        assert 'minlength' in errors[0].lower()

    def test_validator_without_name_error(self):
        """Test that validator without name produces validation error."""
        node = UIValidatorNode()
        node.pattern = '.*'
        errors = node.validate()
        assert any("name" in e.lower() for e in errors)

    def test_validator_without_rule_error(self):
        """Test that validator without any rule produces validation error."""
        node = UIValidatorNode()
        node.name = 'emptyValidator'
        errors = node.validate()
        assert any("rule" in e.lower() for e in errors)

    def test_form_invalid_validation_mode_error(self):
        """Test that invalid validation mode produces error."""
        node = UIFormNode()
        node.validation_mode = 'invalid'
        errors = node.validate()
        assert any("validation_mode" in e.lower() for e in errors)

    def test_form_invalid_error_display_error(self):
        """Test that invalid error display mode produces error."""
        node = UIFormNode()
        node.error_display = 'invalid'
        errors = node.validate()
        assert any("error_display" in e.lower() for e in errors)


# ============================================
# Complete Form Example
# ============================================

class TestCompleteFormValidation:
    """Test complete form with multiple validation features."""

    def test_registration_form(self, parser):
        """Test parsing a complete registration form with validation."""
        app = parse_ui(parser, '''
            <ui:window title="Registration">
                <ui:form validation="both" error-display="both" on-submit="handleRegistration">
                    <ui:validator name="passwordMatch" match="password"
                                  message="Passwords do not match" />
                    <ui:validator name="strongPassword"
                                  pattern="^(?=.*[A-Za-z])(?=.*\\d)[A-Za-z\\d]{8,}$"
                                  message="Password must be 8+ chars with letters and numbers" />

                    <ui:formitem label="Email">
                        <ui:input bind="email" type="email" required="true"
                                  error-message="Valid email is required" />
                    </ui:formitem>

                    <ui:formitem label="Username">
                        <ui:input bind="username" required="true"
                                  minlength="3" maxlength="20"
                                  pattern="[a-zA-Z0-9_]+"
                                  error-message="Username: 3-20 alphanumeric chars" />
                    </ui:formitem>

                    <ui:formitem label="Password">
                        <ui:input bind="password" type="password" required="true"
                                  validators="strongPassword" />
                    </ui:formitem>

                    <ui:formitem label="Confirm Password">
                        <ui:input bind="confirmPassword" type="password" required="true"
                                  validators="passwordMatch" />
                    </ui:formitem>

                    <ui:formitem label="Age">
                        <ui:input bind="age" type="number" min="18" max="120"
                                  error-message="Age must be 18-120" />
                    </ui:formitem>

                    <ui:button variant="primary">Register</ui:button>
                </ui:form>
            </ui:window>
        ''')

        window = app.ui_windows[0]
        form = window.children[0]

        # Verify form attributes
        assert isinstance(form, UIFormNode)
        assert form.validation_mode == 'both'
        assert form.error_display == 'both'
        assert form.on_submit == 'handleRegistration'

        # Verify validators
        assert len(form.validators) == 2
        validators_by_name = {v.name: v for v in form.validators}
        assert 'passwordMatch' in validators_by_name
        assert 'strongPassword' in validators_by_name
        assert validators_by_name['passwordMatch'].match == 'password'

        # Verify form items and inputs
        formitems = [c for c in form.children if isinstance(c, UIFormItemNode)]
        assert len(formitems) == 5

        # Verify email input
        email_input = formitems[0].children[0]
        assert isinstance(email_input, UIInputNode)
        assert email_input.input_type == 'email'
        assert email_input.required is True

        # Verify username input
        username_input = formitems[1].children[0]
        assert username_input.minlength == 3
        assert username_input.maxlength == 20
        assert username_input.pattern == '[a-zA-Z0-9_]+'

        # Verify password input has custom validator
        password_input = formitems[2].children[0]
        assert 'strongPassword' in password_input.validators

        # Verify age input
        age_input = formitems[4].children[0]
        assert age_input.input_type == 'number'
        assert age_input.min == '18'
        assert age_input.max == '120'

        # Generate HTML and verify it includes validation
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)

        # Verify validation JS and CSS are included
        assert '__qValidation' in html
        assert 'q-validation-summary' in html
        assert 'q-error-message' in html

        # Verify form attributes
        assert 'data-validation="both"' in html
        assert 'data-error-display="both"' in html
