/**
 * AI Provider Abstraction
 *
 * Supports multiple AI providers:
 * - Anthropic (Claude)
 * - OpenAI (GPT)
 * - Local (Ollama)
 *
 * Includes rate limiting and caching.
 */

import * as vscode from 'vscode';
import * as https from 'https';
import * as http from 'http';

/**
 * AI Provider interface
 */
export interface AIProvider {
    /** Check if the provider is available and configured */
    isAvailable(): boolean;

    /** Send a completion request */
    complete(prompt: string, options?: CompletionOptions): Promise<string>;

    /** Get the provider name */
    getName(): string;
}

/**
 * Completion options
 */
export interface CompletionOptions {
    maxTokens?: number;
    temperature?: number;
    stopSequences?: string[];
}

/**
 * Rate limiter for API calls
 */
class RateLimiter {
    private timestamps: number[] = [];
    private readonly maxRequests: number;
    private readonly windowMs: number;

    constructor(maxRequests: number = 10, windowMs: number = 60000) {
        this.maxRequests = maxRequests;
        this.windowMs = windowMs;
    }

    async waitForSlot(): Promise<void> {
        const now = Date.now();

        // Remove old timestamps
        this.timestamps = this.timestamps.filter(t => now - t < this.windowMs);

        if (this.timestamps.length >= this.maxRequests) {
            // Wait until the oldest request expires
            const waitTime = this.windowMs - (now - this.timestamps[0]) + 100;
            await new Promise(resolve => setTimeout(resolve, waitTime));
            return this.waitForSlot();
        }

        this.timestamps.push(now);
    }
}

/**
 * Simple response cache
 */
class ResponseCache {
    private cache: Map<string, { response: string; timestamp: number }> = new Map();
    private readonly ttlMs: number;

    constructor(ttlMs: number = 300000) { // 5 minutes default
        this.ttlMs = ttlMs;
    }

    get(key: string): string | undefined {
        const entry = this.cache.get(key);
        if (!entry) {
            return undefined;
        }

        if (Date.now() - entry.timestamp > this.ttlMs) {
            this.cache.delete(key);
            return undefined;
        }

        return entry.response;
    }

    set(key: string, response: string): void {
        this.cache.set(key, { response, timestamp: Date.now() });

        // Clean up old entries
        const now = Date.now();
        for (const [k, v] of this.cache.entries()) {
            if (now - v.timestamp > this.ttlMs) {
                this.cache.delete(k);
            }
        }
    }

    generateKey(prompt: string, options?: CompletionOptions): string {
        return JSON.stringify({ prompt, options });
    }
}

/**
 * Anthropic (Claude) provider
 */
class AnthropicProvider implements AIProvider {
    private apiKey: string;
    private model: string;
    private rateLimiter = new RateLimiter();
    private cache = new ResponseCache();

    constructor() {
        const config = vscode.workspace.getConfiguration('quantum.ai');
        this.apiKey = config.get<string>('apiKey') || '';
        this.model = config.get<string>('model') || 'claude-sonnet-4-20250514';
    }

    getName(): string {
        return 'Anthropic';
    }

    isAvailable(): boolean {
        return !!this.apiKey;
    }

    async complete(prompt: string, options?: CompletionOptions): Promise<string> {
        // Check cache first
        const cacheKey = this.cache.generateKey(prompt, options);
        const cached = this.cache.get(cacheKey);
        if (cached) {
            return cached;
        }

        await this.rateLimiter.waitForSlot();

        const requestBody = JSON.stringify({
            model: this.model,
            max_tokens: options?.maxTokens || 1024,
            messages: [
                { role: 'user', content: prompt }
            ]
        });

        return new Promise((resolve, reject) => {
            const req = https.request({
                hostname: 'api.anthropic.com',
                path: '/v1/messages',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'x-api-key': this.apiKey,
                    'anthropic-version': '2023-06-01'
                }
            }, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        const response = JSON.parse(data);
                        if (response.error) {
                            reject(new Error(response.error.message));
                            return;
                        }
                        const text = response.content?.[0]?.text || '';
                        this.cache.set(cacheKey, text);
                        resolve(text);
                    } catch (e) {
                        reject(e);
                    }
                });
            });

            req.on('error', reject);
            req.write(requestBody);
            req.end();
        });
    }
}

/**
 * OpenAI (GPT) provider
 */
class OpenAIProvider implements AIProvider {
    private apiKey: string;
    private model: string;
    private rateLimiter = new RateLimiter();
    private cache = new ResponseCache();

    constructor() {
        const config = vscode.workspace.getConfiguration('quantum.ai');
        this.apiKey = config.get<string>('openaiApiKey') || '';
        this.model = config.get<string>('openaiModel') || 'gpt-4';
    }

    getName(): string {
        return 'OpenAI';
    }

    isAvailable(): boolean {
        return !!this.apiKey;
    }

    async complete(prompt: string, options?: CompletionOptions): Promise<string> {
        const cacheKey = this.cache.generateKey(prompt, options);
        const cached = this.cache.get(cacheKey);
        if (cached) {
            return cached;
        }

        await this.rateLimiter.waitForSlot();

        const requestBody = JSON.stringify({
            model: this.model,
            max_tokens: options?.maxTokens || 1024,
            temperature: options?.temperature || 0.7,
            messages: [
                { role: 'user', content: prompt }
            ]
        });

        return new Promise((resolve, reject) => {
            const req = https.request({
                hostname: 'api.openai.com',
                path: '/v1/chat/completions',
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.apiKey}`
                }
            }, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        const response = JSON.parse(data);
                        if (response.error) {
                            reject(new Error(response.error.message));
                            return;
                        }
                        const text = response.choices?.[0]?.message?.content || '';
                        this.cache.set(cacheKey, text);
                        resolve(text);
                    } catch (e) {
                        reject(e);
                    }
                });
            });

            req.on('error', reject);
            req.write(requestBody);
            req.end();
        });
    }
}

/**
 * Ollama (local) provider
 */
class OllamaProvider implements AIProvider {
    private baseUrl: string;
    private model: string;
    private rateLimiter = new RateLimiter(30); // Higher limit for local
    private cache = new ResponseCache();

    constructor() {
        const config = vscode.workspace.getConfiguration('quantum.ai');
        this.baseUrl = config.get<string>('ollamaUrl') || 'http://localhost:11434';
        this.model = config.get<string>('ollamaModel') || 'llama2';
    }

    getName(): string {
        return 'Ollama';
    }

    isAvailable(): boolean {
        // Ollama is considered available if the URL is set
        // Actual availability is checked on first request
        return !!this.baseUrl;
    }

    async complete(prompt: string, options?: CompletionOptions): Promise<string> {
        const cacheKey = this.cache.generateKey(prompt, options);
        const cached = this.cache.get(cacheKey);
        if (cached) {
            return cached;
        }

        await this.rateLimiter.waitForSlot();

        const url = new URL('/api/generate', this.baseUrl);
        const isHttps = url.protocol === 'https:';
        const httpModule = isHttps ? https : http;

        const requestBody = JSON.stringify({
            model: this.model,
            prompt: prompt,
            stream: false,
            options: {
                num_predict: options?.maxTokens || 1024,
                temperature: options?.temperature || 0.7
            }
        });

        return new Promise((resolve, reject) => {
            const req = httpModule.request({
                hostname: url.hostname,
                port: url.port || (isHttps ? 443 : 80),
                path: url.pathname,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            }, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        const response = JSON.parse(data);
                        if (response.error) {
                            reject(new Error(response.error));
                            return;
                        }
                        const text = response.response || '';
                        this.cache.set(cacheKey, text);
                        resolve(text);
                    } catch (e) {
                        reject(e);
                    }
                });
            });

            req.on('error', reject);
            req.write(requestBody);
            req.end();
        });
    }
}

/**
 * Fallback provider that returns predefined responses
 */
class FallbackProvider implements AIProvider {
    getName(): string {
        return 'Fallback';
    }

    isAvailable(): boolean {
        return true; // Always available
    }

    async complete(prompt: string, options?: CompletionOptions): Promise<string> {
        // Return a generic response indicating AI is not configured
        return `AI assistance is not available.

To enable AI features, please configure one of the following in VS Code settings:

1. **Anthropic (Claude)**:
   - Set \`quantum.ai.provider\` to "anthropic"
   - Set \`quantum.ai.apiKey\` to your Anthropic API key

2. **OpenAI (GPT)**:
   - Set \`quantum.ai.provider\` to "openai"
   - Set \`quantum.ai.openaiApiKey\` to your OpenAI API key

3. **Ollama (Local)**:
   - Set \`quantum.ai.provider\` to "ollama"
   - Ensure Ollama is running locally
   - Set \`quantum.ai.ollamaUrl\` if not using default

For more information, see the Quantum extension documentation.`;
    }
}

// Singleton instances
let currentProvider: AIProvider | undefined;

/**
 * Get the configured AI provider
 */
export function getAIProvider(): AIProvider {
    const config = vscode.workspace.getConfiguration('quantum.ai');
    const providerName = config.get<string>('provider') || 'anthropic';

    // Return cached provider if configuration hasn't changed
    if (currentProvider && currentProvider.getName().toLowerCase() === providerName.toLowerCase()) {
        return currentProvider;
    }

    // Create new provider based on configuration
    switch (providerName.toLowerCase()) {
        case 'anthropic':
            currentProvider = new AnthropicProvider();
            break;
        case 'openai':
            currentProvider = new OpenAIProvider();
            break;
        case 'ollama':
            currentProvider = new OllamaProvider();
            break;
        default:
            currentProvider = new AnthropicProvider();
    }

    // If the selected provider is not available, try others or use fallback
    if (!currentProvider.isAvailable()) {
        const providers = [
            new AnthropicProvider(),
            new OpenAIProvider(),
            new OllamaProvider()
        ];

        for (const provider of providers) {
            if (provider.isAvailable()) {
                currentProvider = provider;
                break;
            }
        }

        // If no provider is available, use fallback
        if (!currentProvider.isAvailable()) {
            currentProvider = new FallbackProvider();
        }
    }

    return currentProvider;
}

/**
 * Check if any AI provider is properly configured
 */
export function isAIConfigured(): boolean {
    const provider = getAIProvider();
    return provider.isAvailable() && provider.getName() !== 'Fallback';
}

/**
 * Register configuration change listener to invalidate provider cache
 */
export function registerAIProviderConfiguration(context: vscode.ExtensionContext): void {
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('quantum.ai')) {
                currentProvider = undefined; // Reset cached provider
            }
        })
    );
}
