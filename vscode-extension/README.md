# Claude Top VS Code Extension

Monitor Claude CLI instances directly from VS Code.

## Features

- **Status Bar Integration**: Shows the number of active Claude instances
- **Interactive Panel**: View detailed information about each Claude instance
- **Real-time Updates**: Automatic refresh with configurable interval
- **Process Management**: Pause or kill Claude instances from VS Code
- **Tree View**: Claude instances appear in the Explorer sidebar
- **Resource Alerts**: Get notifications for high CPU or memory usage

## Installation

1. Copy the `vscode-extension` folder to your VS Code extensions directory:
   - Windows: `%USERPROFILE%\.vscode\extensions\`
   - macOS/Linux: `~/.vscode/extensions/`

2. Rename the folder to `claude-top-0.1.0`

3. Restart VS Code

## Usage

### Commands

- `Claude Top: Show Monitor Panel` - Opens the monitoring panel
- `Claude Top: Refresh` - Manually refresh the instance list
- `Claude Top: Pause Instance` - Pause a selected Claude instance
- `Claude Top: Kill Instance` - Terminate a selected Claude instance

### Status Bar

Click on the Claude status bar item (shows instance count) to open the monitor panel.

### Configuration

Configure the extension in VS Code settings:

- `claudeTop.updateInterval`: Update interval in seconds (default: 2)
- `claudeTop.showNotifications`: Show notifications for high resource usage (default: true)
- `claudeTop.cpuThreshold`: CPU usage threshold for notifications in % (default: 80)
- `claudeTop.memoryThreshold`: Memory usage threshold for notifications in MB (default: 1000)

## Requirements

- Python 3.6+
- claude-top installed and accessible in PATH
- psutil Python package

## Development

To modify the extension:

1. Edit `extension.js`
2. Reload VS Code window (Developer: Reload Window)
3. Test the changes

To package for distribution:
```bash
npm install -g vsce
vsce package
```

## Future Enhancements

- Historical metrics graphs
- Productivity analytics integration
- Custom alert rules
- Export session data
- Integration with Claude Code features