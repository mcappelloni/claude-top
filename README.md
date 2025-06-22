# claude-top

A terminal-based monitoring tool for Claude CLI instances, similar to Unix `top` but specifically designed for monitoring Claude processes. Features an htop-inspired interface with comprehensive resource tracking, process management, and safety features.

## Features

### Core Monitoring
- **Real-time Monitoring** of all running Claude CLI instances
- **Htop-style Summary**: CPU/memory bars, session totals, and aggregate statistics
- **Advanced Resource Tracking**: 
  - CPU usage with state detection (running/idle/waiting)
  - Memory consumption with historical tracking
  - Network I/O split by direction (in/out/total)
  - Disk I/O with total and current activity
  - Connection counting with MCP detection
- **Process Management**: 
  - Pause/resume instances
  - Kill processes with confirmation dialog (graceful/force options)
- **Smart Filtering**: Only shows actual Claude CLI processes (filters out false positives)
- **Interactive Controls**: Advanced sorting, navigation, and display options

### Enhanced Features (New in v2.0)
- **Real-time Dashboard Mode**: Live ASCII charts and sparklines for metrics visualization
- **Enhanced Visual Indicators**: 
  - Modern progress bars with gradients and animations
  - Status icons and color-coded indicators
  - Activity sparklines for trends
- **Performance Optimization**: 
  - Adaptive update intervals based on system load
  - Background task processing
  - Priority-based update scheduling
- **VS Code Extension**: Monitor Claude instances directly from your editor
- **Historical Analytics**: Track productivity metrics and session history
- **Resource Alerts**: Configurable alerts for high CPU/memory usage
- **Data Export**: Export session data in multiple formats (CSV, JSON, Excel)

### Organization & Productivity
- **Search & Filter**: Find processes quickly by PID, status, command, or directory
- **Batch Operations**: Select and manage multiple processes simultaneously
- **Project Grouping**: Organize processes by project with aggregate statistics
- **Database Integration**: SQLite tracking for historical data and analytics
- **Productivity Metrics**: Track time spent, tokens used, and session patterns

## Quick Start with npx

The easiest way to use claude-top is with npx (no installation required):

```bash
# Run directly with npx
npx claude-top

# Run with custom update interval
npx claude-top --interval 2.0
```

## Installation

### Option 1: Using npm/npx (Recommended)

```bash
# Install globally
npm install -g claude-top

# Or run directly without installation
npx claude-top
```

### Option 2: From Source

```bash
# Clone the repository
git clone https://github.com/mcappelloni/claude-top.git
cd claude-top

# For npm/yarn users
npm install
npm start

# For Python users with uv
uv venv
source .venv/bin/activate && uv pip install psutil
./claude-top
```

## Usage

```bash
# Run with npx (no installation needed)
npx claude-top

# If installed globally
claude-top

# Run with custom update interval (e.g., 2 seconds)
claude-top --interval 2.0

# Run from source
./claude-top --interval 1.5

# Disable database tracking
claude-top --no-database

# Use custom database path
claude-top --db-path /path/to/custom.db

# Output JSON data for integration (e.g., VS Code extension)
claude-top --json-once
```

### Command Line Options

- `--interval SECONDS`: Update interval in seconds (default: 1.0)
- `--no-database`: Disable database tracking
- `--db-path PATH`: Custom database file path (default: claude_tracking.db)
- `--json-once`: Output JSON data once and exit (for integrations)
- `-h, --help`: Show help message

## Keyboard Shortcuts

### Navigation
- **↑/↓** or **k/j**: Navigate through processes  
- **Home/End**: Jump to first/last process

### Search & Filter
- **/**: Enter search mode (search by PID, status, command, or directory)
- **ESC**: Clear search or exit search mode
- Real-time filtering as you type

### Multi-Select Mode
- **m**: Enter multi-select mode
- **Space**: Toggle selection on current process
- **a**: Select all visible processes
- **n**: Clear all selections
- **p**: Pause/resume all selected processes
- **K**: Kill all selected processes (with confirmation)
- **ESC**: Exit multi-select mode

### Process Control
- **p**: Pause/Resume selected Claude instance
- **K** (capital): Kill selected instance with confirmation dialog
  - **C**: Cancel kill operation
  - **G**: Kill gracefully (SIGTERM)
  - **F**: Force kill (SIGKILL)

### Display Options
- **s**: Cycle through sort columns (PID → CPU% → Memory → Net↑ → Net↓ → NetΣ → DiskΣ → Disk∆ → Connections → Time)
- **r**: Reverse sort order
- **f**: Toggle between full path and abbreviated directory display
- **g**: Toggle project grouping (group by parent directory)
- **d**: Show database statistics (if enabled)

### Enhanced Features
- **R** (capital): Enter real-time dashboard mode
  - **Tab**: Switch between overview and charts view
  - **Space**: Pause/resume updates
  - **ESC**: Exit dashboard mode
- **V** (capital): Toggle enhanced visual indicators
- **P** (capital): Toggle performance optimization mode
- **I** (capital): Show performance information (FPS, update time)
- **A** (capital): Show analytics dashboard
  - **1-5**: Switch analytics views (overview/trends/projects/productivity/sessions)
  - **e**: Export data
  - **ESC**: Exit analytics
- **X** (capital): Export current data
- **C** (capital): Show alert configuration

### General
- **h**: Show/hide help
- **q** or **Esc**: Quit

## Display Information

### Header Summary (htop-style)
- **CPU/Memory bars**: Visual representation of total resource usage
- **Process counts**: Running, idle, waiting, and paused instances
- **Session totals**: Cumulative network and disk I/O
- **Current rates**: Real-time I/O activity indicators

### Process Columns
- **PID**: Process ID
- **Status**: Process state (running/idle/waiting/paused)
- **CPU%**: Current CPU usage
- **Mem(MB)**: Memory usage in megabytes
- **Net↑**: Network bytes sent (outbound)
- **Net↓**: Network bytes received (inbound)
- **NetΣ**: Total network I/O (cumulative)
- **DiskΣ**: Total disk I/O (cumulative)
- **Disk∆**: Current disk activity (this cycle)
- **Conn**: Connection count (M suffix indicates MCP connections)
- **Time**: Elapsed time since process started
- **Working Directory**: Current working directory

### Visual Indicators
- **→**: Currently selected process
- **▲/▼**: Sort direction indicator on column headers
- **[DB]**: Database tracking enabled
- **Color coding**:
  - Green: Running processes (actively processing)
  - Cyan: Waiting (in conversation, waiting for user input)
  - Default/White: Idle (between sessions, waiting for new instructions)
  - Yellow: Paused processes
  - Red: High resource usage (>80% CPU or >1GB memory)

## VS Code Extension

claude-top includes a VS Code extension for monitoring Claude instances directly from your editor.

### Installation

1. Copy the `vscode-extension` folder to your VS Code extensions directory:
   - Windows: `%USERPROFILE%\.vscode\extensions\claude-top-0.1.0`
   - macOS/Linux: `~/.vscode/extensions/claude-top-0.1.0`

2. Restart VS Code

### Extension Features

- **Status Bar**: Shows active Claude instance count
- **Monitor Panel**: Interactive webview with process details
- **Tree View**: Claude instances in Explorer sidebar
- **Commands**: Pause/kill instances from Command Palette
- **Alerts**: Notifications for high resource usage

### Extension Settings

- `claudeTop.updateInterval`: Update interval in seconds
- `claudeTop.showNotifications`: Enable resource usage alerts
- `claudeTop.cpuThreshold`: CPU alert threshold (%)
- `claudeTop.memoryThreshold`: Memory alert threshold (MB)

## Requirements

- Python 3.6+
- psutil library
- Terminal with Unicode support
- Optional: SQLite3 for database features

## Advanced Usage

### Real-time Dashboard

The real-time dashboard provides live visualization of metrics:

- **Live Charts**: ASCII charts showing CPU, memory, and I/O trends
- **Sparklines**: Mini graphs showing recent activity
- **Progress Bars**: Visual representation of resource usage
- **Animated Indicators**: Show active processes and data flow

Access with `R` key, navigate views with `Tab`.

### Performance Optimization

Performance mode adapts to system load:

- **Adaptive Intervals**: Slower updates when system is busy
- **Priority Updates**: Critical data updated more frequently
- **Background Processing**: Non-essential tasks run asynchronously
- **Smart Caching**: Reduces redundant system calls

Toggle with `P` key, view stats with `I` key.

### Analytics Dashboard

Track productivity and usage patterns:

- **Session History**: Timeline of Claude sessions
- **Project Analytics**: Time spent per project
- **Resource Trends**: Historical CPU/memory usage
- **Productivity Metrics**: Tokens used, commands run
- **Export Options**: CSV, JSON, or Excel formats

Access with `A` key, export with `e` key.

## Troubleshooting

### Common Issues

1. **"No Claude instances found"**: Make sure Claude CLI is running (`claude` command)
2. **Database errors**: Use `--no-database` flag or check write permissions
3. **High CPU usage**: Enable performance mode with `P` key
4. **Visual glitches**: Toggle enhanced visuals with `V` key

### Process Detection

claude-top uses smart detection to find only actual Claude CLI processes:
- Filters out Claude desktop app
- Ignores projects with "claude" in the path
- Detects various Claude CLI execution methods (direct, npx, npm)

## License

MIT License