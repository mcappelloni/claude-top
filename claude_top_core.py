#!/usr/bin/env python3
"""Core Claude monitoring logic extracted for testing"""

import psutil
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
from typing import List, Optional

@dataclass
class ClaudeInstance:
    pid: int
    working_dir: str
    task: str
    context_length: int
    tokens_used: int
    start_time: datetime
    status: str  # 'running', 'idle', 'waiting', 'paused'
    cpu_percent: float
    memory_mb: float
    command: str
    cpu_history: deque = field(default_factory=lambda: deque(maxlen=5))
    net_bytes_sent: int = 0
    net_bytes_recv: int = 0
    disk_read_bytes: int = 0
    disk_write_bytes: int = 0
    connections_count: int = 0
    mcp_connections: int = 0

class ClaudeMonitor:
    def __init__(self):
        self.instances: List[ClaudeInstance] = []
        self.selected_index = 0
        self.paused_pids = set()
        self.update_interval = 1.0
        self.sort_key = 'pid'
        self.reverse_sort = False
        self.show_full_path = False
        self.cpu_histories = {}  # Track CPU history for each PID
        
    def find_claude_processes(self):
        """Find all Claude CLI processes running on the system"""
        claude_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd', 'create_time', 'cpu_percent', 'memory_info']):
            try:
                # Check if this is a Claude CLI process
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('claude' in cmd.lower() for cmd in cmdline):
                    # Filter out non-CLI Claude processes
                    cmdline_str = ' '.join(cmdline)
                    # Skip Claude desktop app processes
                    if 'Claude.app' in cmdline_str or 'Claude Helper' in cmdline_str or 'chrome_crashpad' in cmdline_str or 'Squirrel' in cmdline_str:
                        continue
                    # Skip docker processes unless they're Claude-related containers
                    if 'docker' in cmdline_str and 'mcp/filesystem' in cmdline_str:
                        continue
                    
                    # Extract relevant information
                    instance = self.parse_claude_process(proc)
                    if instance:
                        claude_processes.append(instance)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return claude_processes
    
    def parse_claude_process(self, proc) -> Optional[ClaudeInstance]:
        """Parse process information to create ClaudeInstance"""
        try:
            info = proc.info
            pid = info['pid']
            # Get working directory - try multiple methods
            cwd = info.get('cwd', None)
            if not cwd or cwd == '/':
                try:
                    # Try to get cwd directly from process
                    cwd = proc.cwd()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    cwd = 'Unknown'
            
            cmdline = ' '.join(info.get('cmdline', []))
            
            # For now, we'll use a placeholder for task
            task = "Active Session"
            
            # Get context and token information (would need to read from Claude's state files)
            context_length, tokens_used = self.get_claude_metrics(pid, cwd)
            
            # Initialize CPU history for new processes
            if pid not in self.cpu_histories:
                self.cpu_histories[pid] = deque(maxlen=5)
            
            # Update CPU history
            current_cpu = info.get('cpu_percent', 0.0)
            self.cpu_histories[pid].append(current_cpu)
            
            # Determine status based on CPU usage patterns
            status = self.determine_process_status(pid, proc)
            
            # Get network and disk I/O statistics
            net_io, disk_io, connections_info = self.get_io_stats(proc)
            
            return ClaudeInstance(
                pid=pid,
                working_dir=cwd,
                task=task,
                context_length=context_length,
                tokens_used=tokens_used,
                start_time=datetime.fromtimestamp(info['create_time']),
                status=status,
                cpu_percent=info.get('cpu_percent', 0.0),
                memory_mb=info.get('memory_info').rss / 1024 / 1024 if info.get('memory_info') else 0,
                command=cmdline,
                cpu_history=self.cpu_histories[pid].copy(),
                net_bytes_sent=net_io['bytes_sent'],
                net_bytes_recv=net_io['bytes_recv'],
                disk_read_bytes=disk_io['read_bytes'],
                disk_write_bytes=disk_io['write_bytes'],
                connections_count=connections_info['total_connections'],
                mcp_connections=connections_info['mcp_connections']
            )
        except Exception:
            return None
    
    def determine_process_status(self, pid, proc):
        """Determine process status based on CPU usage patterns"""
        # Check if manually paused
        if pid in self.paused_pids:
            return 'paused'
        
        # Check system status
        sys_status = proc.status()
        if sys_status == 'stopped':
            return 'paused'
        
        # Analyze CPU history
        cpu_samples = list(self.cpu_histories[pid])
        if len(cpu_samples) >= 3:
            avg_cpu = sum(cpu_samples) / len(cpu_samples)
            max_cpu = max(cpu_samples)
            
            if avg_cpu < 0.5 and max_cpu < 1.0:
                return 'waiting'  # Waiting for user input
            elif avg_cpu > 5.0:
                return 'running'  # Actively processing
            else:
                return 'idle'     # Minimal activity
        
        # Default to running for new processes
        return 'running'
    
    def get_claude_metrics(self, pid: int, working_dir: str) -> tuple:
        """Get context length and token usage from Claude's state files"""
        # Claude CLI does not expose token/context data in accessible files
        # This information is only available internally via /cost command
        return 0, 0
    
    def get_io_stats(self, proc):
        """Get network I/O, disk I/O, and connection statistics for a process"""
        try:
            pid = proc.pid
            
            # Initialize I/O tracker if not exists
            if not hasattr(self, 'io_tracker'):
                self.io_tracker = {}
            
            # Get current activity indicators
            current_indicators = self.get_activity_indicators(proc)
            
            # Calculate I/O estimates based on activity changes
            if pid in self.io_tracker:
                prev_indicators = self.io_tracker[pid]
                
                # Memory delta often indicates I/O activity
                memory_delta = current_indicators.get('memory_usage', 0) - prev_indicators.get('memory_usage', 0)
                files_delta = current_indicators.get('open_files', 0) - prev_indicators.get('open_files', 0)
                
                # Estimate disk I/O based on memory and file activity
                estimated_write = max(0, memory_delta // 10)  # Memory growth -> writes
                estimated_read = abs(files_delta) * 1024  # File activity -> reads
                
                disk_stats = {
                    'read_bytes': estimated_read,
                    'write_bytes': estimated_write
                }
                
                # Network estimation based on connection activity
                conn_count = current_indicators.get('network_connections', 0)
                net_activity = conn_count * 2048  # Rough estimate per connection
                
                net_stats = {
                    'bytes_sent': net_activity // 2,
                    'bytes_recv': net_activity // 2
                }
            else:
                # First time seeing this process
                disk_stats = {'read_bytes': 0, 'write_bytes': 0}
                net_stats = {'bytes_sent': 0, 'bytes_recv': 0}
            
            # Store current indicators for next comparison
            self.io_tracker[pid] = current_indicators
            
            # Connection analysis
            connections_info = {
                'total_connections': current_indicators.get('network_connections', 0),
                'mcp_connections': self.detect_mcp_connections(proc)
            }
            
            return net_stats, disk_stats, connections_info
            
        except Exception:
            # Return default values on any error
            return ({'bytes_sent': 0, 'bytes_recv': 0}, 
                   {'read_bytes': 0, 'write_bytes': 0},
                   {'total_connections': 0, 'mcp_connections': 0})
    
    def get_activity_indicators(self, proc):
        """Get activity indicators for a process"""
        indicators = {
            'memory_usage': 0,
            'open_files': 0,
            'threads': 0,
            'network_connections': 0
        }
        
        try:
            # Memory usage
            memory_info = proc.memory_info()
            indicators['memory_usage'] = memory_info.rss
            
            # Thread count
            indicators['threads'] = proc.num_threads()
            
            # Open files count
            try:
                open_files = proc.open_files()
                indicators['open_files'] = len(open_files)
            except psutil.AccessDenied:
                pass
            
            # Network connections
            try:
                connections = proc.net_connections()
                indicators['network_connections'] = len(connections)
            except psutil.AccessDenied:
                pass
                
        except psutil.NoSuchProcess:
            pass
        
        return indicators
    
    def detect_mcp_connections(self, proc):
        """Detect potential MCP connections"""
        try:
            connections = proc.net_connections()
            mcp_count = 0
            
            for conn in connections:
                if conn.status == 'ESTABLISHED':
                    # Heuristic for MCP: WebSocket-like ports or specific patterns
                    if (conn.raddr and conn.raddr.port in [8000, 8080, 3000, 9000] or
                        (conn.laddr and conn.laddr.port > 8000)):
                        mcp_count += 1
            
            return mcp_count
        except (psutil.AccessDenied, AttributeError):
            return 0