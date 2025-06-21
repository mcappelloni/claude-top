#!/usr/bin/env python3
"""Advanced I/O tracking for macOS using alternative methods"""

import subprocess
import psutil
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class IOStats:
    read_bytes: int = 0
    write_bytes: int = 0
    read_ops: int = 0
    write_ops: int = 0

@dataclass
class NetworkStats:
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0

class MacOSIOTracker:
    def __init__(self):
        self.previous_stats = {}
        self.network_stats = {}
        
    def get_process_io_with_iotop(self, pid: int) -> Optional[IOStats]:
        """Get I/O stats using iotop command (if available)"""
        try:
            # Use iotop to get I/O statistics
            result = subprocess.run(['iotop', '-a', '-o', '-p', str(pid)], 
                                  capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if str(pid) in line:
                        # Parse iotop output
                        parts = line.split()
                        if len(parts) >= 10:
                            try:
                                read_bytes = self.parse_size(parts[8])  # Read column
                                write_bytes = self.parse_size(parts[9])  # Write column
                                return IOStats(read_bytes=read_bytes, write_bytes=write_bytes)
                            except:
                                pass
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        return None
    
    def get_process_io_with_lsof(self, pid: int) -> Optional[IOStats]:
        """Estimate I/O activity using lsof and file activity"""
        try:
            # Use lsof to see what files the process has open
            result = subprocess.run(['lsof', '-p', str(pid)], 
                                  capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                file_count = 0
                
                for line in lines[1:]:  # Skip header
                    if 'REG' in line or 'PIPE' in line:  # Regular files or pipes
                        file_count += 1
                
                # Estimate I/O based on file activity (rough heuristic)
                estimated_io = file_count * 1024  # Rough estimate
                return IOStats(read_bytes=estimated_io, write_bytes=estimated_io)
                
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        return IOStats()
    
    def get_network_with_netstat(self, pid: int) -> Optional[NetworkStats]:
        """Get network stats using netstat and lsof combination"""
        try:
            # Get network connections for the process
            result = subprocess.run(['lsof', '-i', '-a', '-p', str(pid)], 
                                  capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                connection_count = len([l for l in lines[1:] if 'TCP' in l or 'UDP' in l])
                
                # Estimate network activity based on connection count
                estimated_bytes = connection_count * 4096  # Rough estimate
                return NetworkStats(bytes_sent=estimated_bytes, bytes_recv=estimated_bytes)
                
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        return NetworkStats()
    
    def get_activity_indicators(self, pid: int) -> Dict[str, int]:
        """Get activity indicators using multiple approaches"""
        indicators = {
            'file_descriptors': 0,
            'threads': 0,
            'network_connections': 0,
            'memory_usage': 0,
            'open_files': 0
        }
        
        try:
            proc = psutil.Process(pid)
            
            # Get thread count
            indicators['threads'] = proc.num_threads()
            
            # Get memory usage
            memory_info = proc.memory_info()
            indicators['memory_usage'] = memory_info.rss
            
            # Get open files count
            try:
                open_files = proc.open_files()
                indicators['open_files'] = len(open_files)
            except psutil.AccessDenied:
                pass
            
            # Get network connections
            try:
                connections = proc.net_connections()
                indicators['network_connections'] = len(connections)
            except psutil.AccessDenied:
                pass
                
        except psutil.NoSuchProcess:
            pass
        
        return indicators
    
    def estimate_io_from_activity(self, pid: int) -> (IOStats, NetworkStats):
        """Estimate I/O based on process activity indicators"""
        
        # Get current activity indicators
        current_indicators = self.get_activity_indicators(pid)
        
        # If we have previous data, calculate deltas
        if pid in self.previous_stats:
            prev_indicators = self.previous_stats[pid]
            
            # Calculate activity deltas
            memory_delta = current_indicators['memory_usage'] - prev_indicators.get('memory_usage', 0)
            files_delta = current_indicators['open_files'] - prev_indicators.get('open_files', 0)
            
            # Estimate I/O based on activity
            # Memory growth often indicates disk writes (swap, cache)
            estimated_write = max(0, memory_delta // 10)  # Conservative estimate
            estimated_read = abs(files_delta) * 1024  # File activity estimate
            
            io_stats = IOStats(
                read_bytes=estimated_read,
                write_bytes=estimated_write
            )
            
            # Network estimation based on connection activity
            net_activity = current_indicators['network_connections'] * 2048  # Rough estimate
            network_stats = NetworkStats(
                bytes_sent=net_activity // 2,
                bytes_recv=net_activity // 2
            )
        else:
            # First time seeing this process
            io_stats = IOStats()
            network_stats = NetworkStats()
        
        # Store current indicators for next comparison
        self.previous_stats[pid] = current_indicators
        
        return io_stats, network_stats
    
    def parse_size(self, size_str: str) -> int:
        """Parse size string like '1.2K', '345M' to bytes"""
        if not size_str or size_str == '-':
            return 0
        
        size_str = size_str.strip().upper()
        multipliers = {'B': 1, 'K': 1024, 'M': 1024**2, 'G': 1024**3}
        
        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                try:
                    return int(float(size_str[:-1]) * multiplier)
                except ValueError:
                    return 0
        
        try:
            return int(size_str)
        except ValueError:
            return 0

def test_io_tracker():
    """Test the I/O tracker with Claude processes"""
    tracker = MacOSIOTracker()
    
    print("Testing Advanced I/O Tracking")
    print("=" * 40)
    
    # Find Claude processes
    claude_pids = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any('claude' in cmd.lower() for cmd in cmdline):
                cmdline_str = ' '.join(cmdline)
                if 'Claude.app' not in cmdline_str and 'Claude Helper' not in cmdline_str:
                    claude_pids.append(proc.info['pid'])
        except:
            continue
    
    if not claude_pids:
        print("No Claude processes found")
        return
    
    print(f"Found {len(claude_pids)} Claude processes: {claude_pids}")
    
    # Test over multiple cycles
    for cycle in range(3):
        print(f"\nCycle {cycle + 1}:")
        print(f"{'PID':<8} {'Disk R/W':<12} {'Net S/R':<12} {'Files':<6} {'Threads':<8} {'Mem':<10}")
        print("-" * 60)
        
        for pid in claude_pids:
            try:
                io_stats, net_stats = tracker.estimate_io_from_activity(pid)
                indicators = tracker.get_activity_indicators(pid)
                
                disk_display = f"{tracker.parse_size(str(io_stats.read_bytes))//1024}K/{tracker.parse_size(str(io_stats.write_bytes))//1024}K"
                net_display = f"{net_stats.bytes_sent//1024}K/{net_stats.bytes_recv//1024}K"
                mem_display = f"{indicators['memory_usage']//1024//1024}MB"
                
                print(f"{pid:<8} {disk_display:<12} {net_display:<12} {indicators['open_files']:<6} {indicators['threads']:<8} {mem_display:<10}")
                
            except Exception as e:
                print(f"{pid:<8} Error: {e}")
        
        if cycle < 2:
            time.sleep(2)

if __name__ == "__main__":
    test_io_tracker()