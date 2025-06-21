#!/usr/bin/env python3
"""Test the enhanced Claude monitoring with I/O tracking"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from claude_top_core import ClaudeMonitor
import time

def test_enhanced_monitoring():
    """Test the new I/O tracking and connection monitoring"""
    monitor = ClaudeMonitor()
    
    print("Testing Enhanced Claude Monitoring with I/O Tracking")
    print("=" * 65)
    
    # Run for a few cycles to collect data
    for cycle in range(3):
        print(f"\nCycle {cycle + 1}/3:")
        instances = monitor.find_claude_processes()
        
        print(f"{'PID':<8} {'Status':<8} {'CPU%':<6} {'Mem(MB)':<8} {'Net I/O':<10} {'Disk I/O':<10} {'Conn':<6} {'MCP':<4}")
        print("-" * 65)
        
        for instance in instances:
            # Format I/O data 
            net_total = instance.net_bytes_sent + instance.net_bytes_recv
            disk_total = instance.disk_read_bytes + instance.disk_write_bytes
            
            # Format in human readable
            def format_bytes(bytes_val):
                if bytes_val == 0:
                    return "0B"
                elif bytes_val < 1024:
                    return f"{bytes_val}B"
                elif bytes_val < 1024 * 1024:
                    return f"{bytes_val/1024:.1f}K"
                elif bytes_val < 1024 * 1024 * 1024:
                    return f"{bytes_val/(1024*1024):.1f}M"
                else:
                    return f"{bytes_val/(1024*1024*1024):.1f}G"
            
            net_display = format_bytes(net_total)
            disk_display = format_bytes(disk_total)
            mcp_indicator = "Yes" if instance.mcp_connections > 0 else "No"
            
            print(f"{instance.pid:<8} {instance.status:<8} {instance.cpu_percent:<6.1f} "
                  f"{instance.memory_mb:<8.1f} {net_display:<10} {disk_display:<10} "
                  f"{instance.connections_count:<6} {mcp_indicator:<4}")
        
        if cycle < 2:
            print("\nWaiting 3 seconds for next sample...")
            time.sleep(3)
    
    print(f"\nSummary:")
    print(f"Total processes found: {len(instances)}")
    
    # Analyze I/O patterns
    if instances:
        total_net = sum(inst.net_bytes_sent + inst.net_bytes_recv for inst in instances)
        total_disk = sum(inst.disk_read_bytes + inst.disk_write_bytes for inst in instances)
        total_connections = sum(inst.connections_count for inst in instances)
        total_mcp = sum(inst.mcp_connections for inst in instances)
        
        def format_bytes(bytes_val):
            if bytes_val < 1024:
                return f"{bytes_val}B"
            elif bytes_val < 1024 * 1024:
                return f"{bytes_val/1024:.1f}KB"
            elif bytes_val < 1024 * 1024 * 1024:
                return f"{bytes_val/(1024*1024):.1f}MB"
            else:
                return f"{bytes_val/(1024*1024*1024):.1f}GB"
        
        print(f"Total Network I/O: {format_bytes(total_net)}")
        print(f"Total Disk I/O: {format_bytes(total_disk)}")
        print(f"Total Connections: {total_connections}")
        print(f"MCP Connections Detected: {total_mcp}")
        
        # State distribution
        states = {}
        for instance in instances:
            states[instance.status] = states.get(instance.status, 0) + 1
        
        print("\nState distribution:")
        for state, count in states.items():
            print(f"  {state}: {count}")

if __name__ == "__main__":
    test_enhanced_monitoring()