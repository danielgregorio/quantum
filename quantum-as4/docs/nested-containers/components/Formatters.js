/**
 * Formatters
 *
 * Non-visual components for formatting data display.
 * Compatible with Adobe Flex Formatter API.
 *
 * Features:
 * - DateFormatter: Format dates with patterns
 * - NumberFormatter: Format numbers with precision
 * - CurrencyFormatter: Format currency values
 * - PhoneFormatter: Format phone numbers
 *
 * @example
 * <mx:DateFormatter id="dateFormatter" formatString="MM/DD/YYYY" />
 * <s:Label text="{dateFormatter.format(new Date())}" />
 */

/**
 * DateFormatter
 */
export class DateFormatter {
    constructor() {
        this.formatString = 'MM/DD/YYYY';
    }

    format(date) {
        if (!date) return '';
        if (typeof date === 'string') {
            date = new Date(date);
        }

        const tokens = {
            'YYYY': date.getFullYear(),
            'YY': String(date.getFullYear()).slice(-2),
            'MM': String(date.getMonth() + 1).padStart(2, '0'),
            'M': date.getMonth() + 1,
            'DD': String(date.getDate()).padStart(2, '0'),
            'D': date.getDate(),
            'HH': String(date.getHours()).padStart(2, '0'),
            'H': date.getHours(),
            'mm': String(date.getMinutes()).padStart(2, '0'),
            'm': date.getMinutes(),
            'ss': String(date.getSeconds()).padStart(2, '0'),
            's': date.getSeconds(),
            'A': date.getHours() >= 12 ? 'PM' : 'AM',
            'a': date.getHours() >= 12 ? 'pm' : 'am'
        };

        // Month names
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];
        const monthNamesShort = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

        tokens['MMMM'] = monthNames[date.getMonth()];
        tokens['MMM'] = monthNamesShort[date.getMonth()];

        // Day names
        const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const dayNamesShort = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

        tokens['EEEE'] = dayNames[date.getDay()];
        tokens['EEE'] = dayNamesShort[date.getDay()];

        // Replace tokens in format string
        let result = this.formatString;

        // Sort by length descending to replace longer tokens first
        const sortedTokens = Object.keys(tokens).sort((a, b) => b.length - a.length);

        for (const token of sortedTokens) {
            result = result.replace(new RegExp(token, 'g'), tokens[token]);
        }

        return result;
    }
}

/**
 * NumberFormatter
 */
export class NumberFormatter {
    constructor() {
        this.precision = 2;
        this.decimalSeparator = '.';
        this.thousandsSeparator = ',';
        this.useThousandsSeparator = true;
        this.rounding = 'nearest'; // 'none', 'up', 'down', 'nearest'
    }

    format(value) {
        if (value === null || value === undefined || value === '') return '';

        let num = parseFloat(value);
        if (isNaN(num)) return value.toString();

        // Apply rounding
        switch (this.rounding) {
            case 'up':
                num = Math.ceil(num * Math.pow(10, this.precision)) / Math.pow(10, this.precision);
                break;
            case 'down':
                num = Math.floor(num * Math.pow(10, this.precision)) / Math.pow(10, this.precision);
                break;
            case 'nearest':
                num = Math.round(num * Math.pow(10, this.precision)) / Math.pow(10, this.precision);
                break;
        }

        // Split into integer and decimal parts
        const parts = num.toFixed(this.precision).split('.');
        let integerPart = parts[0];
        const decimalPart = parts[1];

        // Add thousands separator
        if (this.useThousandsSeparator && this.thousandsSeparator) {
            integerPart = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, this.thousandsSeparator);
        }

        // Combine parts
        let result = integerPart;
        if (this.precision > 0 && decimalPart) {
            result += this.decimalSeparator + decimalPart;
        }

        return result;
    }
}

/**
 * CurrencyFormatter
 */
export class CurrencyFormatter extends NumberFormatter {
    constructor() {
        super();
        this.currencySymbol = '$';
        this.alignSymbol = 'left'; // 'left' or 'right'
        this.precision = 2;
        this.useNegativeSign = true;
        this.useThousandsSeparator = true;
    }

    format(value) {
        if (value === null || value === undefined || value === '') return '';

        let num = parseFloat(value);
        if (isNaN(num)) return value.toString();

        const isNegative = num < 0;
        num = Math.abs(num);

        // Format the number
        const formatted = super.format(num);

        // Add currency symbol
        let result;
        if (this.alignSymbol === 'left') {
            result = this.currencySymbol + formatted;
        } else {
            result = formatted + this.currencySymbol;
        }

        // Add negative sign
        if (isNegative && this.useNegativeSign) {
            result = '-' + result;
        }

        return result;
    }
}

/**
 * PhoneFormatter
 */
export class PhoneFormatter {
    constructor() {
        this.formatString = '(###) ###-####';
    }

    format(value) {
        if (!value) return '';

        // Remove all non-digits
        const digits = value.toString().replace(/\D/g, '');

        // Apply format
        let result = this.formatString;
        let digitIndex = 0;

        for (let i = 0; i < result.length && digitIndex < digits.length; i++) {
            if (result[i] === '#') {
                result = result.substring(0, i) + digits[digitIndex] + result.substring(i + 1);
                digitIndex++;
            }
        }

        // Remove remaining # symbols
        result = result.replace(/#/g, '');

        return result;
    }
}

/**
 * ZipCodeFormatter
 */
export class ZipCodeFormatter {
    constructor() {
        this.formatString = '#####-####';
    }

    format(value) {
        if (!value) return '';

        // Remove all non-digits
        const digits = value.toString().replace(/\D/g, '');

        // Handle 5-digit or 9-digit ZIP codes
        if (digits.length <= 5) {
            return digits;
        }

        return digits.substring(0, 5) + '-' + digits.substring(5, 9);
    }
}

/**
 * SwitchSymbolFormatter (for formatting expressions)
 */
export class SwitchSymbolFormatter {
    constructor() {
        this.formatString = '#';
    }

    format(value) {
        if (!value && value !== 0) return '';
        return this.formatString.replace(/#/g, value.toString());
    }
}

/**
 * Render formatters as non-visual components
 */
export function renderDateFormatter(runtime, node) {
    const formatter = new DateFormatter();

    if (node.props.formatString) {
        formatter.formatString = node.props.formatString;
    }

    // Store in runtime if has ID
    if (node.props.id) {
        runtime.app[node.props.id] = formatter;
    }

    return document.createComment(`DateFormatter: ${node.props.id}`);
}

export function renderNumberFormatter(runtime, node) {
    const formatter = new NumberFormatter();

    if (node.props.precision !== undefined) {
        formatter.precision = parseInt(node.props.precision);
    }
    if (node.props.decimalSeparator) {
        formatter.decimalSeparator = node.props.decimalSeparator;
    }
    if (node.props.thousandsSeparator) {
        formatter.thousandsSeparator = node.props.thousandsSeparator;
    }
    if (node.props.useThousandsSeparator !== undefined) {
        formatter.useThousandsSeparator = node.props.useThousandsSeparator === 'true';
    }
    if (node.props.rounding) {
        formatter.rounding = node.props.rounding;
    }

    if (node.props.id) {
        runtime.app[node.props.id] = formatter;
    }

    return document.createComment(`NumberFormatter: ${node.props.id}`);
}

export function renderCurrencyFormatter(runtime, node) {
    const formatter = new CurrencyFormatter();

    if (node.props.precision !== undefined) {
        formatter.precision = parseInt(node.props.precision);
    }
    if (node.props.currencySymbol) {
        formatter.currencySymbol = node.props.currencySymbol;
    }
    if (node.props.alignSymbol) {
        formatter.alignSymbol = node.props.alignSymbol;
    }
    if (node.props.decimalSeparator) {
        formatter.decimalSeparator = node.props.decimalSeparator;
    }
    if (node.props.thousandsSeparator) {
        formatter.thousandsSeparator = node.props.thousandsSeparator;
    }
    if (node.props.useThousandsSeparator !== undefined) {
        formatter.useThousandsSeparator = node.props.useThousandsSeparator === 'true';
    }

    if (node.props.id) {
        runtime.app[node.props.id] = formatter;
    }

    return document.createComment(`CurrencyFormatter: ${node.props.id}`);
}

export function renderPhoneFormatter(runtime, node) {
    const formatter = new PhoneFormatter();

    if (node.props.formatString) {
        formatter.formatString = node.props.formatString;
    }

    if (node.props.id) {
        runtime.app[node.props.id] = formatter;
    }

    return document.createComment(`PhoneFormatter: ${node.props.id}`);
}

export function renderZipCodeFormatter(runtime, node) {
    const formatter = new ZipCodeFormatter();

    if (node.props.formatString) {
        formatter.formatString = node.props.formatString;
    }

    if (node.props.id) {
        runtime.app[node.props.id] = formatter;
    }

    return document.createComment(`ZipCodeFormatter: ${node.props.id}`);
}
