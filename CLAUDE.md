# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`claude-top` is a terminal-based monitoring tool for Claude CLI instances, similar to Unix `top` but specifically for monitoring Claude processes. It provides real-time monitoring of CPU, memory, network/disk I/O, and process status with advanced features like real-time dashboards, analytics, and VS Code integration.

## Commands

### Setup
```bash
# Create virtual environment using uv
uv venv

# Activate virtual environment and install dependencies
source .venv/bin/activate && uv pip install psutil
```

### Running the Tool
```bash
# Run with default settings (1 second update interval)
source .venv/bin/activate && ./claude-top

# Run with custom update interval (e.g., 2 seconds)
source .venv/bin/activate && ./claude-top --interval 2.0

# Run without database tracking
source .venv/bin/activate && ./claude-top --no-database

# Get JSON output for integration
source .venv/bin/activate && ./claude-top --json-once

# Alternative: run with Python directly
source .venv/bin/activate && python claude-top
```

### Development
```bash
# Make the script executable (if needed)
chmod +x claude-top

# Check for Python syntax errors
source .venv/bin/activate && python3 -m py_compile claude-top

# Test Claude process detection without UI
source .venv/bin/activate && python test_claude_detection.py
```

## Architecture

The tool is modular with core functionality and optional enhanced features. Key components:

### Core Components
1. **ClaudeMonitor** class: Core monitoring logic that finds and tracks Claude processes
2. **ClaudeTopUI** class: Curses-based terminal UI for displaying process information
3. **ClaudeInstance** dataclass: Represents a single Claude CLI process with all its metrics

### Enhanced Components (when available)
4. **RealTimeDashboard**: Live charts and sparklines for metrics visualization
5. **VisualIndicators**: Modern progress bars, animations, and status icons
6. **PerformanceOptimizer**: Adaptive update intervals and background processing
7. **HistoricalAnalytics**: Database-backed analytics and productivity tracking
8. **ProcessManager**: Advanced process control and cleanup features

### VS Code Extension
- Located in `vscode-extension/` directory
- Provides monitoring directly in VS Code
- Uses `--json-once` flag for data retrieval

The tool uses:
- `psutil` for process discovery and resource monitoring
- `curses` for the terminal UI
- `SQLite` for optional database tracking
- Signal handling (SIGSTOP/SIGCONT) for pause/resume functionality

## Key Implementation Details

- **Process Detection**: Smart filtering to only show actual Claude CLI processes
  - Checks for `claude` command as first argument
  - Detects `npx claude`, `npm view @anthropic-ai/claude-code`
  - Filters out false positives (desktop app, projects with "claude" in path)
  
- **Enhanced Features**:
  - Real-time dashboard with ASCII charts (`R` key)
  - Visual indicators with animations (`V` key)
  - Performance optimization mode (`P` key)
  - Analytics dashboard (`A` key)
  - Data export functionality (`X` key)
  
- **Interactive Controls**: 
  - Advanced keyboard shortcuts for all features
  - Multi-select mode for batch operations
  - Search and filter capabilities
  - Project grouping views
  
- **Visual Design**:
  - Color-coded process states (running/idle/waiting/paused)
  - Modern progress bars with gradients
  - Status icons and activity indicators
  - Resource usage warnings (>80% CPU or >1GB memory)

## Memories

- You only have access to current working directory and subfolders