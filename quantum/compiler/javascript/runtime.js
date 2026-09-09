/**
 * Quantum Runtime for JavaScript
 * ===============================
 *
 * Runtime support library for transpiled Quantum code.
 */

// HTML escaping
export function escape(value) {
    if (value == null) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Raw HTML marker
export class RawHTML {
    constructor(content) {
        this.content = content != null ? String(content) : '';
    }
    toString() {
        return this.content;
    }
}

export function raw(value) {
    return new RawHTML(value);
}

// Databinding
export function bind(template, context) {
    return template.replace(/\{([^}]+)\}/g, (match, expr) => {
        try {
            const fn = new Function(...Object.keys(context), `return ${expr}`);
            const result = fn(...Object.values(context));
            return result instanceof RawHTML ? result.toString() : escape(result);
        } catch {
            return match;
        }
    });
}

// Component base class
export class Component {
    constructor(props = {}) {
        this.props = props;
    }

    render() {
        throw new Error('Component.render() must be implemented');
    }

    toString() {
        return this.render();
    }
}

// Flash messages
const _flashMessages = [];

export function flash(message, category = 'info') {
    _flashMessages.push({ message, category });
}

export function getFlashedMessages(withCategories = false) {
    const messages = [..._flashMessages];
    _flashMessages.length = 0;
    return withCategories ? messages : messages.map(m => m.message);
}

// State management
export function createStore(initialState = {}) {
    let state = { ...initialState };
    const listeners = new Set();

    return {
        getState: () => ({ ...state }),
        setState: (newState) => {
            state = { ...state, ...newState };
            listeners.forEach(fn => fn(state));
        },
        subscribe: (fn) => {
            listeners.add(fn);
            return () => listeners.delete(fn);
        }
    };
}

// HTTP utilities
export async function invoke(url, options = {}) {
    const response = await fetch(url, {
        method: options.method || 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        body: options.body ? JSON.stringify(options.body) : undefined
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
}

// Redirect
export function redirect(url, code = 302) {
    window.location.href = url;
}

// Utilities
export function safeGet(obj, ...keys) {
    let current = obj;
    for (const key of keys) {
        if (current == null) return undefined;
        current = current[key];
    }
    return current;
}

export function range(start, end, step = 1) {
    const result = [];
    if (step > 0) {
        for (let i = start; i < end; i += step) {
            result.push(i);
        }
    } else if (step < 0) {
        for (let i = start; i > end; i += step) {
            result.push(i);
        }
    }
    return result;
}

// Job Queue (Phase 3)
const jobQueue = new Map();

export function defineJob(name, handler) {
    jobQueue.set(name, handler);
}

export function dispatchJob(name, params = {}, delay = null) {
    const handler = jobQueue.get(name);
    if (!handler) {
        throw new Error(`Job not found: ${name}`);
    }
    if (delay) {
        setTimeout(() => handler(params), parseDelay(delay));
    } else {
        queueMicrotask(() => handler(params));
    }
}

// Parse delay string (e.g., "5m", "1h", "30s") to milliseconds
export function parseDelay(delay) {
    const match = delay.match(/(\d+)([smhd])/);
    if (!match) return 0;
    const [, value, unit] = match;
    const multipliers = { s: 1000, m: 60000, h: 3600000, d: 86400000 };
    return parseInt(value) * (multipliers[unit] || 1000);
}

// Parallel execution helper
export async function parallel(...tasks) {
    return Promise.all(tasks.map(t => typeof t === 'function' ? t() : t));
}

// Export all
export default {
    escape,
    raw,
    RawHTML,
    bind,
    Component,
    flash,
    getFlashedMessages,
    createStore,
    invoke,
    redirect,
    safeGet,
    range,
    defineJob,
    dispatchJob,
    parseDelay,
    parallel
};
