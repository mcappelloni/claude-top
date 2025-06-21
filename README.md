# claude-top

A terminal-based monitoring tool for Claude CLI instances, similar to Unix `top` but specifically designed for monitoring Claude processes.

## Features

- **Real-time monitoring** of all running Claude CLI instances
- **Resource tracking**: CPU usage, memory consumption, token usage
- **Process management**: Pause/resume Claude instances with keyboard shortcuts
- **Smart filtering**: Automatically filters out Claude desktop app processes
- **Customizable display**: Toggle between full paths and abbreviated directory names
- **Interactive controls**: Sort by different metrics, navigate with arrow keys
- **Visual indicators**: Shows sorted column and selected process

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-top.git
cd claude-top

# Create virtual environment using uv
uv venv

# Activate virtual environment and install dependencies
source .venv/bin/activate && uv pip install psutil

# Make the script executable
chmod +x claude-top
```

## Usage

```bash
# Run with default settings (1 second update interval)
source .venv/bin/activate && ./claude-top

# Run with custom update interval (e.g., 2 seconds)
source .venv/bin/activate && ./claude-top --interval 2.0
```

## Keyboard Shortcuts

- **↑/↓** or **j/k**: Navigate through processes
- **p**: Pause/Resume selected Claude instance
- **k**: Kill selected instance
- **s**: Cycle through sort options (PID, CPU%, Memory, Tokens, Time)
- **r**: Reverse sort order
- **f**: Toggle between full path and abbreviated directory display
- **h**: Show help
- **q** or **Esc**: Quit

## Display Information

The tool displays the following information for each Claude instance:

- **PID**: Process ID
- **Status**: Running or Paused
- **CPU%**: Current CPU usage
- **Mem(MB)**: Memory usage in megabytes
- **Tokens**: Token count (currently using mock data)
- **Context**: Context length (currently using mock data)
- **Time**: Elapsed time since process started
- **Working Directory**: Current working directory of the Claude instance

## Visual Indicators

- **→**: Currently selected process
- **▲/▼**: Sort direction indicator on column headers
- **Color coding**:
  - Green: Running processes
  - Yellow: Paused processes
  - Red: High resource usage (>80% CPU or >1GB memory)

## Requirements

- Python 3.6+
- psutil library
- Terminal with Unicode support

## License

MIT License