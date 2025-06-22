#!/usr/bin/env python3
"""Core Claude monitoring logic extracted for testing"""

import psutil
import signal
import os
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
    net_bytes_total: int = 0
    disk_total_bytes: int = 0
    disk_current_bytes: int = 0  # Current cycle activity
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
        
        # Alert configuration
        self.alerts_enabled = True
        self.cpu_threshold = 80.0  # Alert when CPU > 80%
        self.memory_threshold = 1000.0  # Alert when memory > 1GB
        self.alert_history = {}  # pid -> {'cpu': timestamp, 'memory': timestamp}
        self.alert_cooldown = 60  # Don't repeat same alert for 60 seconds
        
    def find_claude_processes(self):
        """Find all Claude CLI processes running on the system"""
        claude_processes = []
        current_pid = os.getpid()  # Get current process PID
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd', 'create_time', 'cpu_percent', 'memory_info']):
            try:
                # Skip our own process
                if proc.info['pid'] == current_pid:
                    continue
                
                # Check if this is a Claude CLI process
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('claude' in cmd.lower() for cmd in cmdline):
                    # Filter out non-CLI Claude processes
                    cmdline_str = ' '.join(cmdline)
                    
                    # Skip Claude desktop app processes
                    if 'Claude.app' in cmdline_str or 'Claude Helper' in cmdline_str or 'chrome_crashpad' in cmdline_str or 'Squirrel' in cmdline_str:
                        continue
                        
                    # Skip claude-top itself (additional check by command)
                    if 'claude-top' in cmdline_str or './claude-top' in cmdline_str:
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
                net_bytes_total=net_io['bytes_total'],
                disk_total_bytes=disk_io['total_bytes'],
                disk_current_bytes=disk_io['current_bytes'],
                connections_count=connections_info['total_connections'],
                mcp_connections=connections_info['mcp_connections']
            )
        except Exception:
            return None
    
    def determine_process_status(self, pid, proc):
        """Determine process status based on CPU usage patterns
        
        States:
        - running: Actively processing (>5% CPU)
        - waiting: In conversation, waiting for user input (<0.5% CPU, recent activity)
        - idle: Between sessions, waiting for new instructions (<0.5% CPU, no recent activity)
        - paused: Manually paused or system stopped
        """
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
            recent_cpu = cpu_samples[-1] if cpu_samples else 0
            
            # Check patterns in CPU history
            recent_samples = cpu_samples[-3:] if len(cpu_samples) >= 3 else cpu_samples
            recent_avg = sum(recent_samples) / len(recent_samples) if recent_samples else 0
            
            # Look for transition from active to idle (indicates waiting)
            had_activity = any(sample > 3.0 for sample in cpu_samples[:-2]) if len(cpu_samples) > 2 else False
            now_idle = recent_avg < 0.5
            
            if avg_cpu > 5.0:
                return 'running'  # Actively processing
            elif recent_avg < 0.5:
                # Very low recent CPU
                if had_activity and max_cpu > 3.0:
                    # Had significant activity before becoming idle - waiting for input
                    return 'waiting'
                elif recent_cpu > 0.2 or any(s > 0.5 for s in recent_samples):
                    # Still has minimal activity - likely waiting
                    return 'waiting'
                else:
                    # No recent activity at all - idle between sessions
                    return 'idle'
            else:
                # Medium CPU (0.5-5.0) - processing
                return 'running'
        
        # Default to running for new processes
        return 'running'
    
    def get_claude_metrics(self, pid: int, working_dir: str) -> tuple:
        """Get context length and token usage from Claude's state files
        
        Note: Token/cost tracking integration investigation completed.
        Claude CLI intentionally does not expose internal usage data for security reasons.
        The /cost command is internal-only and not accessible programmatically.
        
        Instead, claude-top focuses on process monitoring, resource tracking,
        and session analytics which provide valuable productivity insights.
        """
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
            if not hasattr(self, 'io_totals'):
                self.io_totals = {}
            
            # Get current activity indicators
            current_indicators = self.get_activity_indicators(proc)
            
            # Calculate I/O estimates based on activity changes
            if pid in self.io_tracker:
                prev_indicators = self.io_tracker[pid]
                
                # Memory delta often indicates I/O activity
                memory_delta = current_indicators.get('memory_usage', 0) - prev_indicators.get('memory_usage', 0)
                files_delta = current_indicators.get('open_files', 0) - prev_indicators.get('open_files', 0)
                
                # Estimate current cycle disk I/O
                estimated_write = max(0, memory_delta // 10)  # Memory growth -> writes
                estimated_read = abs(files_delta) * 1024  # File activity -> reads
                current_disk_io = estimated_write + estimated_read
                
                # Network estimation based on connection activity and CPU
                conn_count = current_indicators.get('network_connections', 0)
                cpu_factor = max(1, current_indicators.get('cpu_percent', 0) / 10)  # CPU activity affects network
                base_net_activity = conn_count * 1024 * cpu_factor  # More sophisticated estimate
                
                current_net_sent = int(base_net_activity * 0.6)  # Assume more outbound (requests)
                current_net_recv = int(base_net_activity * 0.4)  # Less inbound (responses)
                
                # Update totals
                if pid not in self.io_totals:
                    self.io_totals[pid] = {
                        'total_net_sent': 0, 'total_net_recv': 0, 'total_disk': 0
                    }
                
                self.io_totals[pid]['total_net_sent'] += current_net_sent
                self.io_totals[pid]['total_net_recv'] += current_net_recv
                self.io_totals[pid]['total_disk'] += current_disk_io
                
                net_stats = {
                    'bytes_sent': current_net_sent,
                    'bytes_recv': current_net_recv,
                    'bytes_total': self.io_totals[pid]['total_net_sent'] + self.io_totals[pid]['total_net_recv']
                }
                
                disk_stats = {
                    'total_bytes': self.io_totals[pid]['total_disk'],
                    'current_bytes': current_disk_io
                }
            else:
                # First time seeing this process
                net_stats = {'bytes_sent': 0, 'bytes_recv': 0, 'bytes_total': 0}
                disk_stats = {'total_bytes': 0, 'current_bytes': 0}
                if pid not in self.io_totals:
                    self.io_totals[pid] = {
                        'total_net_sent': 0, 'total_net_recv': 0, 'total_disk': 0
                    }
            
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
            return ({'bytes_sent': 0, 'bytes_recv': 0, 'bytes_total': 0}, 
                   {'total_bytes': 0, 'current_bytes': 0},
                   {'total_connections': 0, 'mcp_connections': 0})
    
    def get_activity_indicators(self, proc):
        """Get activity indicators for a process"""
        indicators = {
            'memory_usage': 0,
            'open_files': 0,
            'threads': 0,
            'network_connections': 0,
            'cpu_percent': 0
        }
        
        try:
            # Memory usage
            memory_info = proc.memory_info()
            indicators['memory_usage'] = memory_info.rss
            
            # CPU usage
            indicators['cpu_percent'] = proc.cpu_percent()
            
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
    
    def calculate_summary_stats(self, instances):
        """Calculate comprehensive summary statistics for all Claude instances"""
        if not instances:
            return {
                'session_totals': {'net_in': 0, 'net_out': 0, 'net_total': 0, 'disk_total': 0, 'disk_current': 0},
                'current_rates': {'net_in_rate': 0, 'net_out_rate': 0, 'disk_rate': 0},
                'cpu_stats': {'current': 0, 'average': 0, 'count_running': 0, 'count_idle': 0, 'count_waiting': 0, 'count_paused': 0},
                'memory_stats': {'current': 0, 'average': 0, 'peak': 0},
                'process_stats': {'total': 0, 'with_mcp': 0, 'total_connections': 0},
                'historical_averages': {'cpu': 0, 'memory': 0, 'sessions': 0}
            }
        
        # Session totals (cumulative across all processes)
        session_totals = {
            'net_in': sum(inst.net_bytes_recv for inst in instances),
            'net_out': sum(inst.net_bytes_sent for inst in instances), 
            'net_total': sum(inst.net_bytes_total for inst in instances),
            'disk_total': sum(inst.disk_total_bytes for inst in instances),
            'disk_current': sum(inst.disk_current_bytes for inst in instances)
        }
        
        # Current rates (current cycle activity)
        current_rates = {
            'net_in_rate': session_totals['net_in'],  # Current cycle in
            'net_out_rate': session_totals['net_out'], # Current cycle out
            'disk_rate': session_totals['disk_current']  # Current cycle disk
        }
        
        # CPU statistics
        cpu_values = [inst.cpu_percent for inst in instances]
        cpu_stats = {
            'current': sum(cpu_values),
            'average': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            'count_running': sum(1 for inst in instances if inst.status == 'running'),
            'count_idle': sum(1 for inst in instances if inst.status == 'idle'),
            'count_waiting': sum(1 for inst in instances if inst.status == 'waiting'),
            'count_paused': sum(1 for inst in instances if inst.status == 'paused')
        }
        
        # Memory statistics
        memory_values = [inst.memory_mb for inst in instances]
        memory_stats = {
            'current': sum(memory_values),
            'average': sum(memory_values) / len(memory_values) if memory_values else 0,
            'peak': max(memory_values) if memory_values else 0
        }
        
        # Process statistics
        process_stats = {
            'total': len(instances),
            'with_mcp': sum(1 for inst in instances if inst.mcp_connections > 0),
            'total_connections': sum(inst.connections_count for inst in instances)
        }
        
        # Historical averages (placeholder for core module)
        historical_averages = {'cpu': 0, 'memory': 0, 'sessions': 0}
        
        return {
            'session_totals': session_totals,
            'current_rates': current_rates,
            'cpu_stats': cpu_stats,
            'memory_stats': memory_stats,
            'process_stats': process_stats,
            'historical_averages': historical_averages
        }
    
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

    def pause_resume_process(self, pid: int):
        """Pause or resume a process"""
        try:
            if pid in self.paused_pids:
                os.kill(pid, signal.SIGCONT)
                self.paused_pids.remove(pid)
            else:
                os.kill(pid, signal.SIGSTOP)
                self.paused_pids.add(pid)
        except Exception as e:
            return f"Error: {str(e)}"
        return None

    def kill_process(self, pid: int, force=False):
        """Kill a process gracefully (SIGTERM) or forcefully (SIGKILL)"""
        try:
            proc = psutil.Process(pid)
            
            if force:
                # Force kill with SIGKILL
                proc.kill()
                return None, "Process killed forcefully (SIGKILL)"
            else:
                # Graceful termination with SIGTERM
                proc.terminate()
                return None, "Process terminated gracefully (SIGTERM)"
                
        except psutil.NoSuchProcess:
            return f"Process {pid} no longer exists", None
        except psutil.AccessDenied:
            return f"Access denied to process {pid}", None
        except Exception as e:
            return f"Error killing process {pid}: {str(e)}", None

    def sort_instances(self):
        """Sort instances based on current sort key"""
        if not self.instances:
            return
        
        sort_map = {
            'pid': lambda x: x.pid,
            'cpu': lambda x: x.cpu_percent,
            'memory': lambda x: x.memory_mb,
            'net_out': lambda x: x.net_bytes_sent,
            'net_in': lambda x: x.net_bytes_recv,
            'net_total': lambda x: x.net_bytes_total,
            'disk_total': lambda x: x.disk_total_bytes,
            'disk_current': lambda x: x.disk_current_bytes,
            'connections': lambda x: x.connections_count,
            'time': lambda x: x.start_time
        }
        
        if self.sort_key in sort_map:
            self.instances.sort(key=sort_map[self.sort_key], reverse=self.reverse_sort)
    
    def check_resource_alerts(self):
        """Check for processes exceeding resource thresholds"""
        if not self.alerts_enabled:
            return []
        
        import time
        alerts = []
        current_time = time.time()
        
        for instance in self.instances:
            pid = instance.pid
            
            # Initialize alert history for new processes
            if pid not in self.alert_history:
                self.alert_history[pid] = {'cpu': 0, 'memory': 0}
            
            # Check CPU threshold
            if instance.cpu_percent > self.cpu_threshold:
                last_alert = self.alert_history[pid]['cpu']
                if current_time - last_alert > self.alert_cooldown:
                    alerts.append({
                        'type': 'cpu',
                        'pid': pid,
                        'process': instance.working_dir.split('/')[-1],
                        'value': instance.cpu_percent,
                        'threshold': self.cpu_threshold
                    })
                    self.alert_history[pid]['cpu'] = current_time
            
            # Check memory threshold
            if instance.memory_mb > self.memory_threshold:
                last_alert = self.alert_history[pid]['memory']
                if current_time - last_alert > self.alert_cooldown:
                    alerts.append({
                        'type': 'memory',
                        'pid': pid,
                        'process': instance.working_dir.split('/')[-1],
                        'value': instance.memory_mb,
                        'threshold': self.memory_threshold
                    })
                    self.alert_history[pid]['memory'] = current_time
        
        # Clean up alert history for dead processes
        active_pids = {inst.pid for inst in self.instances}
        self.alert_history = {pid: hist for pid, hist in self.alert_history.items() if pid in active_pids}
        
        return alerts