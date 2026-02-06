/**
 * Quantum Run Command
 *
 * Provides "Run Quantum" functionality with:
 * - Run button in editor title
 * - Task configuration for quantum commands
 * - Debug configuration
 * - Output channel for logs
 */

import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';

let outputChannel: vscode.OutputChannel;

/**
 * Initialize the output channel
 */
export function initializeOutputChannel(): vscode.OutputChannel {
    if (!outputChannel) {
        outputChannel = vscode.window.createOutputChannel('Quantum');
    }
    return outputChannel;
}

/**
 * Run a Quantum file
 */
export async function runQuantumFile(fileUri?: vscode.Uri): Promise<void> {
    const document = fileUri
        ? await vscode.workspace.openTextDocument(fileUri)
        : vscode.window.activeTextEditor?.document;

    if (!document || document.languageId !== 'quantum') {
        vscode.window.showErrorMessage('No Quantum file is open');
        return;
    }

    // Save the document first
    if (document.isDirty) {
        await document.save();
    }

    const config = vscode.workspace.getConfiguration('quantum');
    const pythonPath = config.get<string>('pythonPath') || 'python';
    const frameworkPath = config.get<string>('frameworkPath') || '';

    if (!frameworkPath) {
        const result = await vscode.window.showWarningMessage(
            'Quantum framework path is not configured. Would you like to configure it now?',
            'Configure',
            'Cancel'
        );

        if (result === 'Configure') {
            vscode.commands.executeCommand('workbench.action.openSettings', 'quantum.frameworkPath');
        }
        return;
    }

    const filePath = document.uri.fsPath;
    const runnerPath = path.join(frameworkPath, 'src', 'cli', 'runner.py');

    outputChannel.show(true);
    outputChannel.clear();
    outputChannel.appendLine(`[Quantum] Running: ${filePath}`);
    outputChannel.appendLine(`[Quantum] Using framework: ${frameworkPath}`);
    outputChannel.appendLine('---');

    const startTime = Date.now();

    const proc = cp.spawn(pythonPath, [runnerPath, 'run', filePath], {
        cwd: frameworkPath,
        env: { ...process.env }
    });

    proc.stdout.on('data', (data) => {
        outputChannel.append(data.toString());
    });

    proc.stderr.on('data', (data) => {
        outputChannel.append(`[ERROR] ${data.toString()}`);
    });

    proc.on('close', (code) => {
        const elapsed = Date.now() - startTime;
        outputChannel.appendLine('---');
        outputChannel.appendLine(`[Quantum] Process exited with code ${code} (${elapsed}ms)`);
    });

    proc.on('error', (err) => {
        outputChannel.appendLine(`[ERROR] Failed to start process: ${err.message}`);
        vscode.window.showErrorMessage(`Failed to run Quantum: ${err.message}`);
    });
}

/**
 * Start the Quantum development server
 */
export async function startQuantumServer(): Promise<void> {
    const config = vscode.workspace.getConfiguration('quantum');
    const pythonPath = config.get<string>('pythonPath') || 'python';
    const frameworkPath = config.get<string>('frameworkPath') || '';
    const port = config.get<number>('serverPort') || 8080;

    if (!frameworkPath) {
        vscode.window.showErrorMessage('Quantum framework path is not configured');
        return;
    }

    const runnerPath = path.join(frameworkPath, 'src', 'cli', 'runner.py');

    outputChannel.show(true);
    outputChannel.clear();
    outputChannel.appendLine(`[Quantum] Starting development server on port ${port}...`);
    outputChannel.appendLine('---');

    const proc = cp.spawn(pythonPath, [runnerPath, 'start', '--port', String(port)], {
        cwd: frameworkPath,
        env: { ...process.env }
    });

    proc.stdout.on('data', (data) => {
        outputChannel.append(data.toString());
    });

    proc.stderr.on('data', (data) => {
        outputChannel.append(data.toString());
    });

    proc.on('close', (code) => {
        outputChannel.appendLine('---');
        outputChannel.appendLine(`[Quantum] Server stopped with code ${code}`);
    });

    proc.on('error', (err) => {
        outputChannel.appendLine(`[ERROR] Failed to start server: ${err.message}`);
        vscode.window.showErrorMessage(`Failed to start Quantum server: ${err.message}`);
    });

    // Open browser after a short delay
    setTimeout(() => {
        vscode.env.openExternal(vscode.Uri.parse(`http://localhost:${port}`));
    }, 2000);
}

/**
 * Task provider for Quantum tasks
 */
export class QuantumTaskProvider implements vscode.TaskProvider {
    static readonly quantumTaskType = 'quantum';

    private tasks: vscode.Task[] | undefined;

    constructor(private workspaceRoot: string | undefined) {}

    provideTasks(): vscode.Task[] {
        if (!this.tasks) {
            this.tasks = this._getTasks();
        }
        return this.tasks;
    }

    resolveTask(task: vscode.Task): vscode.Task | undefined {
        const definition = task.definition;
        if (definition.type === QuantumTaskProvider.quantumTaskType) {
            return this._getTask(
                definition.command,
                definition.file,
                definition
            );
        }
        return undefined;
    }

    private _getTasks(): vscode.Task[] {
        const tasks: vscode.Task[] = [];

        // Run current file task
        tasks.push(this._getTask('run', '${file}', {
            type: QuantumTaskProvider.quantumTaskType,
            command: 'run',
            file: '${file}'
        }));

        // Start server task
        tasks.push(this._getTask('start', undefined, {
            type: QuantumTaskProvider.quantumTaskType,
            command: 'start'
        }));

        // Build task
        tasks.push(this._getTask('build', '${file}', {
            type: QuantumTaskProvider.quantumTaskType,
            command: 'build',
            file: '${file}'
        }));

        return tasks;
    }

    private _getTask(
        command: string,
        file: string | undefined,
        definition: vscode.TaskDefinition
    ): vscode.Task {
        const config = vscode.workspace.getConfiguration('quantum');
        const pythonPath = config.get<string>('pythonPath') || 'python';
        const frameworkPath = config.get<string>('frameworkPath') || '';
        const runnerPath = path.join(frameworkPath, 'src', 'cli', 'runner.py');

        let args = [runnerPath, command];
        if (file) {
            args.push(file);
        }

        const execution = new vscode.ShellExecution(pythonPath, args, {
            cwd: frameworkPath
        });

        const taskName = file ? `Quantum: ${command} ${path.basename(file)}` : `Quantum: ${command}`;

        const task = new vscode.Task(
            definition,
            vscode.TaskScope.Workspace,
            taskName,
            'quantum',
            execution,
            ['$quantum']
        );

        task.group = command === 'build' ? vscode.TaskGroup.Build : undefined;
        task.presentationOptions = {
            reveal: vscode.TaskRevealKind.Always,
            panel: vscode.TaskPanelKind.Dedicated
        };

        return task;
    }
}

/**
 * Debug configuration provider for Quantum
 */
export class QuantumDebugConfigurationProvider implements vscode.DebugConfigurationProvider {
    resolveDebugConfiguration(
        folder: vscode.WorkspaceFolder | undefined,
        config: vscode.DebugConfiguration,
        token?: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.DebugConfiguration> {
        // If launch.json is missing or empty
        if (!config.type && !config.request && !config.name) {
            const editor = vscode.window.activeTextEditor;
            if (editor && editor.document.languageId === 'quantum') {
                config.type = 'quantum';
                config.name = 'Run Quantum File';
                config.request = 'launch';
                config.program = '${file}';
            }
        }

        if (!config.program) {
            return vscode.window.showInformationMessage('Cannot find a program to debug').then(_ => {
                return undefined;
            });
        }

        return config;
    }
}

/**
 * Debug adapter descriptor factory for Quantum
 */
export class QuantumDebugAdapterDescriptorFactory implements vscode.DebugAdapterDescriptorFactory {
    createDebugAdapterDescriptor(
        session: vscode.DebugSession,
        executable: vscode.DebugAdapterExecutable | undefined
    ): vscode.ProviderResult<vscode.DebugAdapterDescriptor> {
        const config = vscode.workspace.getConfiguration('quantum');
        const pythonPath = config.get<string>('pythonPath') || 'python';
        const frameworkPath = config.get<string>('frameworkPath') || '';

        // Use Python debugger with Quantum runner
        const runnerPath = path.join(frameworkPath, 'src', 'cli', 'runner.py');

        return new vscode.DebugAdapterExecutable(pythonPath, [
            '-m', 'debugpy', '--listen', '5678', '--wait-for-client',
            runnerPath, 'run', session.configuration.program
        ]);
    }
}

/**
 * Register all run/debug related functionality
 */
export function registerRunCommands(context: vscode.ExtensionContext): void {
    // Initialize output channel
    initializeOutputChannel();
    context.subscriptions.push(outputChannel);

    // Register run command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.run', runQuantumFile)
    );

    // Register start server command
    context.subscriptions.push(
        vscode.commands.registerCommand('quantum.startServer', startQuantumServer)
    );

    // Register task provider
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    context.subscriptions.push(
        vscode.tasks.registerTaskProvider(
            QuantumTaskProvider.quantumTaskType,
            new QuantumTaskProvider(workspaceRoot)
        )
    );

    // Register problem matcher
    // Note: Problem matchers are defined in package.json

    // Register debug configuration provider
    context.subscriptions.push(
        vscode.debug.registerDebugConfigurationProvider(
            'quantum',
            new QuantumDebugConfigurationProvider()
        )
    );

    // Register debug adapter factory
    context.subscriptions.push(
        vscode.debug.registerDebugAdapterDescriptorFactory(
            'quantum',
            new QuantumDebugAdapterDescriptorFactory()
        )
    );
}
