# Changelog

All notable changes to claude-top will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Improved process state detection to properly distinguish between:
  - "waiting": Claude is in an active conversation but waiting for user input
  - "idle": Claude has finished all tasks and is waiting for new instructions
- Enhanced CPU pattern analysis for more accurate state determination

## [0.0.1] - 2024-12-21

### Added
- Initial release of claude-top
- Real-time monitoring of Claude CLI instances
- Htop-style interface with summary statistics
- Process state detection (running/idle/waiting/paused)
- Resource tracking:
  - CPU usage with historical analysis
  - Memory consumption tracking
  - Network I/O split by direction (in/out/total)
  - Disk I/O with total and current activity
  - Connection counting with MCP detection
- Process management features:
  - Pause/resume processes (SIGSTOP/SIGCONT)
  - Kill processes with three-way confirmation dialog
  - Safety checks to prevent self-termination
- SQLite database integration for historical tracking
- Subprocess tree monitoring and analysis
- Interactive controls:
  - Advanced sorting by multiple columns
  - Keyboard navigation (arrow keys and vim-style)
  - Toggle between full/abbreviated paths
  - Database statistics view
- Visual indicators:
  - Color-coded process states
  - Sort direction indicators
  - Resource usage warnings
  - Progress bars for CPU/memory
- NPX support for easy execution
- Cross-platform compatibility (Windows/macOS/Linux)
- Automatic Python environment setup

### Features
- **Kill Confirmation Dialog**: Three options (Cancel/Graceful/Force) with detailed process information
- **Self-Process Filtering**: Automatically excludes claude-top from monitoring
- **Activity-Based I/O Estimation**: Works around macOS psutil limitations
- **Smart Process Detection**: Filters out Claude desktop app and non-CLI processes
- **Database Analytics**: Track usage patterns and resource consumption over time

### Technical Details
- Written in Python with curses UI
- Node.js wrapper for npm/npx distribution
- Automatic virtual environment management
- psutil for process monitoring
- SQLite for data persistence

[0.0.1]: https://github.com/mcappelloni/claude-top/releases/tag/v0.0.1