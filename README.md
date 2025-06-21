# claude-top

A terminal-based monitoring tool for Claude CLI instances, similar to Unix `top` but specifically designed for monitoring Claude processes. Features an htop-inspired interface with comprehensive resource tracking, process management, and safety features.

## Features

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
- **Database Integration**: SQLite tracking for historical data and analytics
- **Smart Filtering**: Automatically excludes Claude desktop app and self-processes
- **Interactive Controls**: Advanced sorting, navigation, and display options
- **Visual Indicators**: Process states, resource warnings, and sort indicators

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
```

## Keyboard Shortcuts

### Navigation
- **↑/↓** or **k/j**: Navigate through processes  
- **Home/End**: Jump to first/last process

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
- **d**: Show database statistics (if enabled)

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

## Requirements

- Python 3.6+
- psutil library
- Terminal with Unicode support

## License

MIT License