/**
 * Validators
 *
 * Form validation components compatible with Adobe Flex Validator API.
 *
 * Features:
 * - StringValidator - validates string length and format
 * - NumberValidator - validates numeric ranges and integers
 * - EmailValidator - validates email addresses
 * - RegExpValidator - validates against custom regex
 * - ValidationResultEvent with error messages
 * - Visual error indicators
 *
 * @example
 * <mx:StringValidator id="usernameValidator"
 *                     source="{usernameInput}"
 *                     property="text"
 *                     minLength="3"
 *                     maxLength="20"
 *                     required="true" />
 */

/**
 * ValidationResultEvent
 */
export class ValidationResultEvent {
    constructor(type, valid = true, results = []) {
        this.type = type;
        this.valid = valid;
        this.results = results;
        this.message = results.length > 0 ? results[0].errorMessage : '';
    }

    static VALID = 'valid';
    static INVALID = 'invalid';
}

/**
 * ValidationResult
 */
export class ValidationResult {
    constructor(isError, errorMessage = '', errorCode = '') {
        this.isError = isError;
        this.errorMessage = errorMessage;
        this.errorCode = errorCode;
    }
}

/**
 * Base Validator Class
 */
class BaseValidator {
    constructor(runtime, node) {
        this.runtime = runtime;
        this.node = node;
        this.id = node.props.id;
        this.required = node.props.required === 'true';
        this.requiredFieldError = node.props.requiredFieldError || 'This field is required.';

        // Source component reference
        this.sourceId = node.props.source ? node.props.source.replace(/[{}]/g, '') : null;
        this.property = node.props.property || 'text';

        // Trigger (when to validate: blur, change, submit)
        this.trigger = node.props.trigger || 'blur';

        // Store in runtime
        if (this.id) {
            runtime.app[this.id] = this;
        }

        // Setup automatic validation on trigger
        this.setupTrigger();
    }

    setupTrigger() {
        if (!this.sourceId || this.trigger === 'manual') {
            return;
        }

        // Wait for source component to be registered
        setTimeout(() => {
            const sourceComponent = this.runtime.app[this.sourceId];

            if (sourceComponent && sourceComponent.element) {
                const element = sourceComponent.element;
                const inputElement = element.tagName === 'INPUT' || element.tagName === 'TEXTAREA'
                    ? element
                    : element.querySelector('input, textarea');

                if (inputElement) {
                    if (this.trigger === 'blur' || this.trigger === 'focusOut') {
                        inputElement.addEventListener('blur', () => {
                            this.validate();
                        });
                    } else if (this.trigger === 'change') {
                        inputElement.addEventListener('input', () => {
                            this.validate();
                        });
                    }
                }
            }
        }, 100);
    }

    getValue() {
        if (!this.sourceId) {
            return null;
        }

        const sourceComponent = this.runtime.app[this.sourceId];

        if (sourceComponent) {
            // Try different methods to get value
            if (typeof sourceComponent.getText === 'function') {
                return sourceComponent.getText();
            } else if (typeof sourceComponent.getValue === 'function') {
                return sourceComponent.getValue();
            } else if (sourceComponent[this.property] !== undefined) {
                return sourceComponent[this.property];
            } else if (sourceComponent.element) {
                const element = sourceComponent.element;
                if (element.value !== undefined) {
                    return element.value;
                } else if (element.textContent !== undefined) {
                    return element.textContent;
                }
            }
        }

        return null;
    }

    showError(message) {
        if (!this.sourceId) {
            return;
        }

        const sourceComponent = this.runtime.app[this.sourceId];

        if (sourceComponent && sourceComponent.element) {
            const element = sourceComponent.element;

            // Add error styling
            element.style.borderColor = '#e74c3c';
            element.style.backgroundColor = '#fff5f5';

            // Create or update error message
            let errorMsg = element.parentElement.querySelector('.validation-error');

            if (!errorMsg) {
                errorMsg = document.createElement('div');
                errorMsg.className = 'validation-error';
                errorMsg.style.color = '#e74c3c';
                errorMsg.style.fontSize = '11px';
                errorMsg.style.marginTop = '2px';
                element.parentElement.appendChild(errorMsg);
            }

            errorMsg.textContent = message;
            errorMsg.style.display = 'block';
        }
    }

    clearError() {
        if (!this.sourceId) {
            return;
        }

        const sourceComponent = this.runtime.app[this.sourceId];

        if (sourceComponent && sourceComponent.element) {
            const element = sourceComponent.element;

            // Remove error styling
            element.style.borderColor = '';
            element.style.backgroundColor = '';

            // Hide error message
            const errorMsg = element.parentElement.querySelector('.validation-error');
            if (errorMsg) {
                errorMsg.style.display = 'none';
            }
        }
    }

    validate() {
        // Override in subclasses
        return new ValidationResultEvent(ValidationResultEvent.VALID);
    }
}

/**
 * StringValidator
 */
export class StringValidator extends BaseValidator {
    constructor(runtime, node) {
        super(runtime, node);
        this.minLength = node.props.minLength ? parseInt(node.props.minLength) : 0;
        this.maxLength = node.props.maxLength ? parseInt(node.props.maxLength) : Infinity;
        this.tooShortError = node.props.tooShortError || `Minimum length is ${this.minLength} characters.`;
        this.tooLongError = node.props.tooLongError || `Maximum length is ${this.maxLength} characters.`;
    }

    validate() {
        const value = this.getValue() || '';
        const results = [];

        // Check required
        if (this.required && value.trim().length === 0) {
            results.push(new ValidationResult(true, this.requiredFieldError, 'required'));
        }
        // Check min length
        else if (value.length < this.minLength) {
            results.push(new ValidationResult(true, this.tooShortError, 'tooShort'));
        }
        // Check max length
        else if (value.length > this.maxLength) {
            results.push(new ValidationResult(true, this.tooLongError, 'tooLong'));
        }

        const event = new ValidationResultEvent(
            results.length === 0 ? ValidationResultEvent.VALID : ValidationResultEvent.INVALID,
            results.length === 0,
            results
        );

        // Show/hide error
        if (event.valid) {
            this.clearError();
        } else {
            this.showError(event.message);
        }

        // Fire valid/invalid event
        const eventType = event.valid ? 'valid' : 'invalid';
        if (this.node.events && this.node.events[eventType]) {
            const handlerName = this.node.events[eventType].replace(/[()]/g, '');
            if (this.runtime.app[handlerName]) {
                this.runtime.app[handlerName](event);
            }
        }

        return event;
    }
}

/**
 * NumberValidator
 */
export class NumberValidator extends BaseValidator {
    constructor(runtime, node) {
        super(runtime, node);
        this.minValue = node.props.minValue !== undefined ? parseFloat(node.props.minValue) : -Infinity;
        this.maxValue = node.props.maxValue !== undefined ? parseFloat(node.props.maxValue) : Infinity;
        this.domain = node.props.domain || 'real'; // 'real' or 'int'
        this.allowNegative = node.props.allowNegative !== 'false';
        this.lowerThanMinError = node.props.lowerThanMinError || `Value must be at least ${this.minValue}.`;
        this.exceedsMaxError = node.props.exceedsMaxError || `Value must be at most ${this.maxValue}.`;
        this.integerError = node.props.integerError || 'Value must be an integer.';
        this.invalidCharError = node.props.invalidCharError || 'Value must be a number.';
        this.negativeError = node.props.negativeError || 'Negative values are not allowed.';
    }

    validate() {
        const value = this.getValue() || '';
        const results = [];

        // Check required
        if (this.required && value.toString().trim().length === 0) {
            results.push(new ValidationResult(true, this.requiredFieldError, 'required'));
        } else if (value.toString().trim().length > 0) {
            const numValue = parseFloat(value);

            // Check if valid number
            if (isNaN(numValue)) {
                results.push(new ValidationResult(true, this.invalidCharError, 'invalidChar'));
            } else {
                // Check negative
                if (!this.allowNegative && numValue < 0) {
                    results.push(new ValidationResult(true, this.negativeError, 'negative'));
                }
                // Check integer
                else if (this.domain === 'int' && !Number.isInteger(numValue)) {
                    results.push(new ValidationResult(true, this.integerError, 'integer'));
                }
                // Check min
                else if (numValue < this.minValue) {
                    results.push(new ValidationResult(true, this.lowerThanMinError, 'lowerThanMin'));
                }
                // Check max
                else if (numValue > this.maxValue) {
                    results.push(new ValidationResult(true, this.exceedsMaxError, 'exceedsMax'));
                }
            }
        }

        const event = new ValidationResultEvent(
            results.length === 0 ? ValidationResultEvent.VALID : ValidationResultEvent.INVALID,
            results.length === 0,
            results
        );

        // Show/hide error
        if (event.valid) {
            this.clearError();
        } else {
            this.showError(event.message);
        }

        // Fire valid/invalid event
        const eventType = event.valid ? 'valid' : 'invalid';
        if (this.node.events && this.node.events[eventType]) {
            const handlerName = this.node.events[eventType].replace(/[()]/g, '');
            if (this.runtime.app[handlerName]) {
                this.runtime.app[handlerName](event);
            }
        }

        return event;
    }
}

/**
 * EmailValidator
 */
export class EmailValidator extends BaseValidator {
    constructor(runtime, node) {
        super(runtime, node);
        this.invalidCharError = node.props.invalidCharError || 'Invalid email address format.';
    }

    validate() {
        const value = this.getValue() || '';
        const results = [];

        // Check required
        if (this.required && value.trim().length === 0) {
            results.push(new ValidationResult(true, this.requiredFieldError, 'required'));
        } else if (value.trim().length > 0) {
            // Email regex
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            if (!emailRegex.test(value)) {
                results.push(new ValidationResult(true, this.invalidCharError, 'invalidChar'));
            }
        }

        const event = new ValidationResultEvent(
            results.length === 0 ? ValidationResultEvent.VALID : ValidationResultEvent.INVALID,
            results.length === 0,
            results
        );

        // Show/hide error
        if (event.valid) {
            this.clearError();
        } else {
            this.showError(event.message);
        }

        // Fire valid/invalid event
        const eventType = event.valid ? 'valid' : 'invalid';
        if (this.node.events && this.node.events[eventType]) {
            const handlerName = this.node.events[eventType].replace(/[()]/g, '');
            if (this.runtime.app[handlerName]) {
                this.runtime.app[handlerName](event);
            }
        }

        return event;
    }
}

/**
 * Render validators (non-visual components)
 */
export function renderStringValidator(runtime, node) {
    new StringValidator(runtime, node);
    return document.createComment(`StringValidator: ${node.props.id}`);
}

export function renderNumberValidator(runtime, node) {
    new NumberValidator(runtime, node);
    return document.createComment(`NumberValidator: ${node.props.id}`);
}

export function renderEmailValidator(runtime, node) {
    new EmailValidator(runtime, node);
    return document.createComment(`EmailValidator: ${node.props.id}`);
}

/**
 * Validate all validators in the application
 */
export function validateAll(runtime) {
    const validators = [];
    let allValid = true;

    // Find all validators
    for (const key in runtime.app) {
        const obj = runtime.app[key];
        if (obj instanceof BaseValidator) {
            const result = obj.validate();
            validators.push({ validator: obj, result: result });
            if (!result.valid) {
                allValid = false;
            }
        }
    }

    return {
        valid: allValid,
        validators: validators
    };
}
