# Changelog

All notable changes to claude-top will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-12-22

### Added
- **Real-time Dashboard Mode** (`R` key)
  - Live ASCII charts for CPU, memory, and I/O metrics
  - Sparkline graphs showing trends
  - Multiple view modes (overview/charts)
  - Pause/resume functionality
  
- **Enhanced Visual Indicators** (`V` key)
  - Modern progress bars with gradients and animations
  - Animated indicators for active processes
  - Status icons (●, ⏸, ⏳, ✓, ✗)
  - Color-coded activity indicators
  - Sparkline mini-graphs for trends
  
- **Performance Optimization** (`P` key)
  - Adaptive update intervals based on system load
  - Priority-based update scheduling (critical/high/medium/low)
  - Background task processing
  - Performance metrics display (`I` key showing FPS and update time)
  - Smart caching system to reduce system calls
  
- **VS Code Extension**
  - Status bar integration showing Claude instance count
  - Interactive webview panel with process details
  - Tree view in Explorer sidebar
  - Commands for pause/kill operations
  - Configurable resource usage alerts
  - Settings for update interval and thresholds
  
- **Analytics Dashboard** (`A` key)
  - Historical data visualization
  - Productivity metrics tracking
  - Project-based analytics
  - Session timeline view
  - Export functionality for reports
  
- **Data Export** (`X` key)
  - CSV format support
  - JSON format support
  - Excel format support (when pandas available)
  - Customizable export options
  - Session summaries and metrics

- **JSON Output Mode**
  - `--json-once` flag for integration purposes
  - Machine-readable process data output
  - VS Code extension support

- **Alert System** (`C` key for configuration)
  - Configurable CPU usage alerts
  - Memory usage thresholds
  - Visual and optional sound alerts
  - Per-process alert configuration

### Changed
- **Improved Process Detection**
  - Only shows actual Claude CLI processes
  - Filters out false positives (projects with "claude" in path)
  - Detects various execution methods (direct, npx, npm, node)
  - Better handling of globally installed Claude CLI
  
- **Enhanced UI Layout**
  - Better spacing and alignment
  - More intuitive visual indicators
  - Improved color scheme for better readability
  - Smoother animations and transitions
  
- **Optimized Performance**
  - Reduced CPU usage in idle state
  - Smarter update scheduling
  - Background processing for non-critical tasks
  - Efficient caching of system calls

### Fixed
- **AttributeError**: Fixed initialization order issue (moved setup_colors after attribute initialization)
- **Checkbox Logic**: Fixed incorrect nested ternary expression in multi-select mode
- **Module Dependencies**: Added proper null checks for optional modules when DATABASE_AVAILABLE is False
- **Process Filtering**: Now correctly identifies only Claude CLI processes
- **Memory Leaks**: Fixed CPU history cleanup for terminated processes

### From Previous Release [Unreleased]
- **Search & Filter**: Real-time process filtering by PID, status, command, or directory
- **Batch Operations**: Multi-select mode for managing multiple processes at once
  - Select multiple processes with checkboxes
  - Batch pause/resume operations
  - Batch kill with confirmation dialog
- **Project Grouping**: Group processes by project/workspace
  - Toggle grouping with 'g' key
  - Aggregate CPU/memory stats per project
  - Hierarchical display with indentation
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

[2.0.0]: https://github.com/mcappelloni/claude-top/releases/tag/v2.0.0
[0.0.1]: https://github.com/mcappelloni/claude-top/releases/tag/v0.0.1