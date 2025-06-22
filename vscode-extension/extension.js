const vscode = require('vscode');
const { spawn } = require('child_process');
const path = require('path');

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    console.log('Claude Top extension is now active!');

    // Create status bar item
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'claudeTop.showPanel';
    statusBarItem.text = '$(pulse) Claude: 0';
    statusBarItem.tooltip = 'Click to open Claude Top monitor';
    statusBarItem.show();

    // Create webview panel
    let panel = undefined;
    let claudeTopProcess = undefined;
    let updateInterval = undefined;

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('claudeTop.showPanel', () => {
            if (panel) {
                panel.reveal();
            } else {
                panel = vscode.window.createWebviewPanel(
                    'claudeTop',
                    'Claude Top Monitor',
                    vscode.ViewColumn.Two,
                    {
                        enableScripts: true,
                        retainContextWhenHidden: true
                    }
                );

                panel.webview.html = getWebviewContent();

                panel.onDidDispose(() => {
                    panel = undefined;
                    if (updateInterval) {
                        clearInterval(updateInterval);
                    }
                }, null, context.subscriptions);

                // Start monitoring
                startMonitoring(panel, statusBarItem);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('claudeTop.refresh', () => {
            if (panel) {
                updateClaudeInfo(panel, statusBarItem);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('claudeTop.pauseInstance', async () => {
            const instances = await getClaudeInstances();
            if (instances.length === 0) {
                vscode.window.showInformationMessage('No Claude instances running');
                return;
            }

            const items = instances.map(inst => ({
                label: `PID: ${inst.pid}`,
                description: `${inst.status} - ${inst.working_dir}`,
                pid: inst.pid
            }));

            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: 'Select instance to pause'
            });

            if (selected) {
                pauseClaudeInstance(selected.pid);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('claudeTop.killInstance', async () => {
            const instances = await getClaudeInstances();
            if (instances.length === 0) {
                vscode.window.showInformationMessage('No Claude instances running');
                return;
            }

            const items = instances.map(inst => ({
                label: `PID: ${inst.pid}`,
                description: `${inst.status} - ${inst.working_dir}`,
                pid: inst.pid
            }));

            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: 'Select instance to kill'
            });

            if (selected) {
                const confirm = await vscode.window.showWarningMessage(
                    `Kill Claude instance (PID: ${selected.pid})?`,
                    'Yes', 'No'
                );
                if (confirm === 'Yes') {
                    killClaudeInstance(selected.pid);
                }
            }
        })
    );

    // Tree data provider for the sidebar
    const claudeProvider = new ClaudeInstanceProvider();
    vscode.window.registerTreeDataProvider('claudeTopView', claudeProvider);

    // Start background monitoring
    startBackgroundMonitoring(statusBarItem, claudeProvider);
}

function deactivate() {
    if (claudeTopProcess) {
        claudeTopProcess.kill();
    }
}

function getWebviewContent() {
    return `<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Claude Top Monitor</title>
        <style>
            body {
                font-family: var(--vscode-font-family);
                background-color: var(--vscode-editor-background);
                color: var(--vscode-editor-foreground);
                padding: 10px;
            }
            .instance {
                border: 1px solid var(--vscode-panel-border);
                border-radius: 4px;
                padding: 10px;
                margin-bottom: 10px;
                background-color: var(--vscode-editor-inactiveSelectionBackground);
            }
            .instance-header {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
            }
            .status-running { color: #4ec9b0; }
            .status-idle { color: #cccccc; }
            .status-waiting { color: #dcdcaa; }
            .status-paused { color: #f48771; }
            .metrics {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }
            .metric {
                display: flex;
                justify-content: space-between;
            }
            .progress-bar {
                width: 100%;
                height: 4px;
                background-color: var(--vscode-progressBar-background);
                border-radius: 2px;
                overflow: hidden;
                margin-top: 4px;
            }
            .progress-fill {
                height: 100%;
                background-color: var(--vscode-progressBar-foreground);
                transition: width 0.3s ease;
            }
            .no-instances {
                text-align: center;
                padding: 40px;
                color: var(--vscode-descriptionForeground);
            }
            button {
                background-color: var(--vscode-button-background);
                color: var(--vscode-button-foreground);
                border: none;
                padding: 4px 8px;
                border-radius: 2px;
                cursor: pointer;
            }
            button:hover {
                background-color: var(--vscode-button-hoverBackground);
            }
        </style>
    </head>
    <body>
        <h2>Claude Top Monitor</h2>
        <div id="instances">
            <div class="no-instances">Loading Claude instances...</div>
        </div>
        <script>
            const vscode = acquireVsCodeApi();
            
            window.addEventListener('message', event => {
                const message = event.data;
                if (message.command === 'update') {
                    updateInstances(message.instances);
                }
            });

            function updateInstances(instances) {
                const container = document.getElementById('instances');
                
                if (instances.length === 0) {
                    container.innerHTML = '<div class="no-instances">No Claude instances running</div>';
                    return;
                }

                container.innerHTML = instances.map(inst => \`
                    <div class="instance">
                        <div class="instance-header">
                            <div>
                                <strong>PID: \${inst.pid}</strong>
                                <span class="status-\${inst.status}">● \${inst.status}</span>
                            </div>
                            <div>
                                <button onclick="pauseInstance(\${inst.pid})">Pause</button>
                                <button onclick="killInstance(\${inst.pid})">Kill</button>
                            </div>
                        </div>
                        <div class="metrics">
                            <div class="metric">
                                <span>CPU:</span>
                                <span>\${inst.cpu_percent.toFixed(1)}%</span>
                            </div>
                            <div class="metric">
                                <span>Memory:</span>
                                <span>\${inst.memory_mb.toFixed(1)}MB</span>
                            </div>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: \${Math.min(inst.cpu_percent, 100)}%"></div>
                        </div>
                        <div style="margin-top: 8px; font-size: 12px; color: var(--vscode-descriptionForeground);">
                            \${inst.working_dir}
                        </div>
                    </div>
                \`).join('');
            }

            function pauseInstance(pid) {
                vscode.postMessage({ command: 'pause', pid: pid });
            }

            function killInstance(pid) {
                vscode.postMessage({ command: 'kill', pid: pid });
            }
        </script>
    </body>
    </html>`;
}

async function getClaudeInstances() {
    return new Promise((resolve) => {
        const claudeTopPath = path.join(__dirname, '..', 'claude-top');
        const proc = spawn('python3', [claudeTopPath, '--json-once'], {
            cwd: path.join(__dirname, '..')
        });

        let output = '';
        proc.stdout.on('data', (data) => {
            output += data.toString();
        });

        proc.on('close', () => {
            try {
                const instances = JSON.parse(output);
                resolve(instances);
            } catch (e) {
                // Fallback to mock data if claude-top doesn't support --json-once yet
                resolve(getMockInstances());
            }
        });

        proc.on('error', () => {
            resolve(getMockInstances());
        });
    });
}

function getMockInstances() {
    // Mock data for development
    return [
        {
            pid: 12345,
            working_dir: '/Users/developer/project1',
            task: 'Analyzing code',
            status: 'running',
            cpu_percent: 45.2,
            memory_mb: 512.3,
            net_bytes_sent: 1024000,
            net_bytes_recv: 2048000
        }
    ];
}

function startMonitoring(panel, statusBarItem) {
    const updateIntervalMs = vscode.workspace.getConfiguration('claudeTop').get('updateInterval') * 1000;
    
    updateClaudeInfo(panel, statusBarItem);
    
    updateInterval = setInterval(() => {
        updateClaudeInfo(panel, statusBarItem);
    }, updateIntervalMs);
}

async function updateClaudeInfo(panel, statusBarItem) {
    const instances = await getClaudeInstances();
    
    // Update status bar
    statusBarItem.text = `$(pulse) Claude: ${instances.length}`;
    if (instances.length > 0) {
        const totalCpu = instances.reduce((sum, inst) => sum + inst.cpu_percent, 0);
        const totalMem = instances.reduce((sum, inst) => sum + inst.memory_mb, 0);
        statusBarItem.tooltip = `Instances: ${instances.length} | CPU: ${totalCpu.toFixed(1)}% | Memory: ${totalMem.toFixed(0)}MB`;
    }

    // Update webview
    if (panel) {
        panel.webview.postMessage({ command: 'update', instances: instances });
    }

    // Check thresholds and show notifications
    const config = vscode.workspace.getConfiguration('claudeTop');
    if (config.get('showNotifications')) {
        const cpuThreshold = config.get('cpuThreshold');
        const memThreshold = config.get('memoryThreshold');

        instances.forEach(inst => {
            if (inst.cpu_percent > cpuThreshold) {
                vscode.window.showWarningMessage(
                    `Claude instance (PID: ${inst.pid}) high CPU usage: ${inst.cpu_percent.toFixed(1)}%`
                );
            }
            if (inst.memory_mb > memThreshold) {
                vscode.window.showWarningMessage(
                    `Claude instance (PID: ${inst.pid}) high memory usage: ${inst.memory_mb.toFixed(0)}MB`
                );
            }
        });
    }
}

function pauseClaudeInstance(pid) {
    spawn('kill', ['-STOP', pid.toString()]);
    vscode.window.showInformationMessage(`Paused Claude instance (PID: ${pid})`);
}

function killClaudeInstance(pid) {
    spawn('kill', ['-TERM', pid.toString()]);
    vscode.window.showInformationMessage(`Killed Claude instance (PID: ${pid})`);
}

// Tree data provider for sidebar
class ClaudeInstanceProvider {
    constructor() {
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
        this.instances = [];
    }

    refresh(instances) {
        this.instances = instances;
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element) {
        return element;
    }

    getChildren(element) {
        if (!element) {
            return this.instances.map(inst => new ClaudeInstanceItem(inst));
        }
        return [];
    }
}

class ClaudeInstanceItem extends vscode.TreeItem {
    constructor(instance) {
        super(`PID: ${instance.pid}`, vscode.TreeItemCollapsibleState.None);
        this.description = `${instance.status} - CPU: ${instance.cpu_percent.toFixed(1)}%`;
        this.contextValue = 'claudeInstance';
        this.iconPath = new vscode.ThemeIcon(
            instance.status === 'running' ? 'pulse' : 
            instance.status === 'paused' ? 'debug-pause' : 'circle-outline'
        );
        this.tooltip = `${instance.working_dir}\nMemory: ${instance.memory_mb.toFixed(1)}MB`;
    }
}

function startBackgroundMonitoring(statusBarItem, provider) {
    const updateIntervalMs = vscode.workspace.getConfiguration('claudeTop').get('updateInterval') * 1000;
    
    const update = async () => {
        const instances = await getClaudeInstances();
        
        // Update status bar
        statusBarItem.text = `$(pulse) Claude: ${instances.length}`;
        
        // Update tree view
        provider.refresh(instances);
    };

    update();
    setInterval(update, updateIntervalMs);
}

module.exports = {
    activate,
    deactivate
}