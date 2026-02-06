/**
 * Quantum Task Provider
 *
 * Provides VS Code tasks for Quantum operations:
 * - Run file
 * - Start server
 * - Build/compile
 * - Test
 */

import * as vscode from 'vscode';
import * as path from 'path';

/**
 * Task definition for Quantum tasks
 */
interface QuantumTaskDefinition extends vscode.TaskDefinition {
    type: 'quantum';
    command: 'run' | 'start' | 'build' | 'test' | 'lint';
    file?: string;
    args?: string[];
}

/**
 * Quantum Task Provider
 */
export class QuantumTaskProvider implements vscode.TaskProvider {
    static readonly quantumTaskType = 'quantum';

    private taskPromise: Thenable<vscode.Task[]> | undefined = undefined;

    constructor(private workspaceRoot: string | undefined) {}

    public provideTasks(): Thenable<vscode.Task[]> | undefined {
        if (!this.taskPromise) {
            this.taskPromise = this.getTasks();
        }
        return this.taskPromise;
    }

    public resolveTask(task: vscode.Task): vscode.Task | undefined {
        const definition = task.definition as QuantumTaskDefinition;

        if (definition.type === QuantumTaskProvider.quantumTaskType) {
            return this.createTask(definition);
        }

        return undefined;
    }

    private async getTasks(): Promise<vscode.Task[]> {
        const tasks: vscode.Task[] = [];

        // Run current file
        tasks.push(this.createTask({
            type: QuantumTaskProvider.quantumTaskType,
            command: 'run',
            file: '${file}'
        }));

        // Start development server
        tasks.push(this.createTask({
            type: QuantumTaskProvider.quantumTaskType,
            command: 'start'
        }));

        // Build/compile
        tasks.push(this.createTask({
            type: QuantumTaskProvider.quantumTaskType,
            command: 'build',
            file: '${file}'
        }));

        // Run tests
        tasks.push(this.createTask({
            type: QuantumTaskProvider.quantumTaskType,
            command: 'test'
        }));

        // Lint
        tasks.push(this.createTask({
            type: QuantumTaskProvider.quantumTaskType,
            command: 'lint',
            file: '${file}'
        }));

        return tasks;
    }

    private createTask(definition: QuantumTaskDefinition): vscode.Task {
        const config = vscode.workspace.getConfiguration('quantum');
        const pythonPath = config.get<string>('pythonPath') || 'python';
        const frameworkPath = config.get<string>('frameworkPath') || '';
        const runnerPath = path.join(frameworkPath, 'src', 'cli', 'runner.py');

        let args: string[] = [runnerPath, definition.command];

        // Add file argument if applicable
        if (definition.file) {
            args.push(definition.file);
        }

        // Add additional arguments
        if (definition.args) {
            args.push(...definition.args);
        }

        // Add command-specific flags
        switch (definition.command) {
            case 'start':
                const port = config.get<number>('serverPort') || 8080;
                args.push('--port', String(port));
                break;
            case 'build':
                const outputDir = config.get<string>('buildOutputDir') || './dist';
                args.push('-o', outputDir);
                break;
            case 'test':
                args = ['pytest', 'tests/', '-v'];
                break;
        }

        const execution = new vscode.ShellExecution(pythonPath, args, {
            cwd: frameworkPath || this.workspaceRoot
        });

        const taskName = this.getTaskName(definition);

        const task = new vscode.Task(
            definition,
            vscode.TaskScope.Workspace,
            taskName,
            'quantum',
            execution,
            this.getProblemMatcher(definition.command)
        );

        // Set task group
        task.group = this.getTaskGroup(definition.command);

        // Set presentation options
        task.presentationOptions = {
            reveal: vscode.TaskRevealKind.Always,
            panel: vscode.TaskPanelKind.Dedicated,
            showReuseMessage: true,
            clear: false
        };

        return task;
    }

    private getTaskName(definition: QuantumTaskDefinition): string {
        switch (definition.command) {
            case 'run':
                return definition.file
                    ? `Run: ${path.basename(definition.file)}`
                    : 'Run Current File';
            case 'start':
                return 'Start Development Server';
            case 'build':
                return definition.file
                    ? `Build: ${path.basename(definition.file)}`
                    : 'Build Project';
            case 'test':
                return 'Run Tests';
            case 'lint':
                return definition.file
                    ? `Lint: ${path.basename(definition.file)}`
                    : 'Lint Project';
            default:
                return `Quantum: ${definition.command}`;
        }
    }

    private getTaskGroup(command: string): vscode.TaskGroup | undefined {
        switch (command) {
            case 'build':
                return vscode.TaskGroup.Build;
            case 'test':
                return vscode.TaskGroup.Test;
            default:
                return undefined;
        }
    }

    private getProblemMatcher(command: string): string[] {
        // Return appropriate problem matchers
        // These should be defined in package.json
        switch (command) {
            case 'build':
            case 'lint':
                return ['$quantum'];
            case 'test':
                return ['$pytest'];
            default:
                return ['$quantum'];
        }
    }
}

/**
 * Problem matcher patterns for package.json
 * These should be added to the contributes.problemMatchers section
 */
export const quantumProblemMatchers = {
    quantum: {
        name: 'quantum',
        owner: 'quantum',
        fileLocation: ['relative', '${workspaceFolder}'],
        pattern: {
            regexp: '^(.+):(\\d+):(\\d+):\\s+(error|warning|info):\\s+(.+)$',
            file: 1,
            line: 2,
            column: 3,
            severity: 4,
            message: 5
        }
    },
    quantumParser: {
        name: 'quantumParser',
        owner: 'quantum',
        fileLocation: ['relative', '${workspaceFolder}'],
        pattern: {
            regexp: '^Parse error in (.+) at line (\\d+): (.+)$',
            file: 1,
            line: 2,
            message: 3
        }
    }
};

/**
 * Register the task provider
 */
export function registerQuantumTasks(context: vscode.ExtensionContext): void {
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

    context.subscriptions.push(
        vscode.tasks.registerTaskProvider(
            QuantumTaskProvider.quantumTaskType,
            new QuantumTaskProvider(workspaceRoot)
        )
    );

    // Register task-related commands
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.runTask', async () => {
            const tasks = await vscode.tasks.fetchTasks({ type: 'quantum' });
            if (tasks.length === 0) {
                vscode.window.showInformationMessage('No Quantum tasks available');
                return;
            }

            const selected = await vscode.window.showQuickPick(
                tasks.map(t => ({
                    label: t.name,
                    description: t.detail,
                    task: t
                })),
                { placeHolder: 'Select a Quantum task to run' }
            );

            if (selected) {
                vscode.tasks.executeTask(selected.task);
            }
        })
    );

    // Register quick run command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.quickRun', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor || editor.document.languageId !== 'quantum') {
                vscode.window.showErrorMessage('No Quantum file is open');
                return;
            }

            // Save the file first
            await editor.document.save();

            const task = new vscode.Task(
                {
                    type: 'quantum',
                    command: 'run',
                    file: editor.document.uri.fsPath
                } as QuantumTaskDefinition,
                vscode.TaskScope.Workspace,
                `Run: ${path.basename(editor.document.uri.fsPath)}`,
                'quantum',
                new vscode.ShellExecution('python', [
                    '${config:quantum.frameworkPath}/src/cli/runner.py',
                    'run',
                    editor.document.uri.fsPath
                ])
            );

            vscode.tasks.executeTask(task);
        })
    );
}

/**
 * Get task definition JSON for tasks.json
 */
export function getTasksJsonTemplate(): object {
    return {
        version: '2.0.0',
        tasks: [
            {
                label: 'Quantum: Run Current File',
                type: 'quantum',
                command: 'run',
                file: '${file}',
                problemMatcher: ['$quantum'],
                group: {
                    kind: 'build',
                    isDefault: true
                }
            },
            {
                label: 'Quantum: Start Server',
                type: 'quantum',
                command: 'start',
                problemMatcher: ['$quantum'],
                isBackground: true,
                presentation: {
                    reveal: 'always',
                    panel: 'dedicated'
                }
            },
            {
                label: 'Quantum: Build Project',
                type: 'quantum',
                command: 'build',
                problemMatcher: ['$quantum'],
                group: 'build'
            },
            {
                label: 'Quantum: Run Tests',
                type: 'quantum',
                command: 'test',
                problemMatcher: ['$pytest'],
                group: 'test'
            }
        ]
    };
}

/**
 * Get launch.json template for debugging
 */
export function getLaunchJsonTemplate(): object {
    return {
        version: '0.2.0',
        configurations: [
            {
                name: 'Quantum: Run Current File',
                type: 'quantum',
                request: 'launch',
                program: '${file}',
                cwd: '${workspaceFolder}',
                console: 'integratedTerminal'
            },
            {
                name: 'Quantum: Debug Current File',
                type: 'python',
                request: 'launch',
                program: '${config:quantum.frameworkPath}/src/cli/runner.py',
                args: ['run', '${file}'],
                cwd: '${config:quantum.frameworkPath}',
                console: 'integratedTerminal'
            },
            {
                name: 'Quantum: Debug Server',
                type: 'python',
                request: 'launch',
                program: '${config:quantum.frameworkPath}/src/cli/runner.py',
                args: ['start', '--port', '8080', '--debug'],
                cwd: '${config:quantum.frameworkPath}',
                console: 'integratedTerminal'
            }
        ]
    };
}
