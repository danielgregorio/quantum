/**
 * Quantum VS Code Extension - Phase 3-4 Exports
 *
 * This file exports all Phase 3 (Tooling) and Phase 4 (AI Assistance) modules.
 */

// Phase 3: Tooling
export { QuantumPreviewPanel } from './panels/previewPanel';
export {
    QuantumTreeDataProvider,
    QuantumTreeItem,
    QuantumNodeType,
    registerComponentTreeView
} from './views/componentTreeView';
export {
    runQuantumFile,
    startQuantumServer,
    QuantumTaskProvider,
    QuantumDebugConfigurationProvider,
    QuantumDebugAdapterDescriptorFactory,
    registerRunCommands,
    initializeOutputChannel
} from './commands/runCommand';
export {
    QuantumTaskProvider as TaskProvider,
    registerQuantumTasks,
    getTasksJsonTemplate,
    getLaunchJsonTemplate
} from './tasks/quantumTasks';

// Phase 4: AI Assistance
export {
    explainError,
    registerExplainErrorCommand
} from './commands/explainError';
export {
    QuantumCodeActionProvider,
    suggestFixWithAI,
    registerSuggestFixProvider
} from './commands/suggestFix';
export {
    lookupDocumentation,
    registerDocumentationLookup
} from './commands/documentationLookup';
export {
    AIProvider,
    CompletionOptions,
    getAIProvider,
    isAIConfigured,
    registerAIProviderConfiguration
} from './ai/aiProvider';
export {
    getErrorExplanationPrompt,
    getSuggestFixPrompt,
    getDocumentationPrompt,
    getCodeCompletionPrompt,
    getRefactoringPrompt,
    getGenerateComponentPrompt,
    getQueryBuilderPrompt,
    getDebugAssistancePrompt
} from './ai/prompts';

// Activation
export {
    activatePhase3,
    activatePhase4,
    activatePhase3and4,
    deactivatePhase3and4
} from './phase3-4-activation';
