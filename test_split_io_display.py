#!/usr/bin/env python3
"""Test the split I/O display with separate network in/out and disk total/current"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from claude_top_core import ClaudeMonitor
import time

def test_split_io_display():
    """Test the new split I/O display format"""
    monitor = ClaudeMonitor()
    
    print("Testing Split I/O Display Format")
    print("=" * 120)
    
    # Print header
    header = f"{'PID':<8} {'Status':<8} {'CPU%':<6} {'Mem(MB)':<8} {'Net↑':<8} {'Net↓':<8} {'NetΣ':<8} {'DiskΣ':<8} {'Disk∆':<8} {'Conn':<6} {'Working Directory':<20}"
    print(header)
    print("-" * 120)
    
    # Run for several cycles to see accumulation
    for cycle in range(5):
        print(f"\nCycle {cycle + 1}/5:")
        instances = monitor.find_claude_processes()
        
        for instance in instances:
            # Format display values
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
            
            net_out = format_bytes(instance.net_bytes_sent)
            net_in = format_bytes(instance.net_bytes_recv)
            net_total = format_bytes(instance.net_bytes_total)
            disk_total = format_bytes(instance.disk_total_bytes)
            disk_current = format_bytes(instance.disk_current_bytes)
            
            # Connection display with MCP indicator
            conn_display = f"{instance.connections_count}M" if instance.mcp_connections > 0 else str(instance.connections_count)
            
            # Truncate directory for display
            dir_display = instance.working_dir.split('/')[-1] if instance.working_dir != '/' else '/'
            
            print(f"{instance.pid:<8} {instance.status:<8} {instance.cpu_percent:<6.1f} "
                  f"{instance.memory_mb:<8.1f} {net_out:<8} {net_in:<8} {net_total:<8} "
                  f"{disk_total:<8} {disk_current:<8} {conn_display:<6} {dir_display:<20}")
        
        if cycle < 4:
            print("Waiting 2 seconds for next cycle...")
            time.sleep(2)
    
    # Summary statistics
    print(f"\n" + "=" * 120)
    print("Summary:")
    
    if instances:
        total_net_out = sum(inst.net_bytes_sent for inst in instances)
        total_net_in = sum(inst.net_bytes_recv for inst in instances)
        total_net_all = sum(inst.net_bytes_total for inst in instances)
        total_disk_all = sum(inst.disk_total_bytes for inst in instances)
        total_disk_current = sum(inst.disk_current_bytes for inst in instances)
        
        def format_bytes(bytes_val):
            if bytes_val < 1024:
                return f"{bytes_val}B"
            elif bytes_val < 1024 * 1024:
                return f"{bytes_val/1024:.1f}KB"
            elif bytes_val < 1024 * 1024 * 1024:
                return f"{bytes_val/(1024*1024):.1f}MB"
            else:
                return f"{bytes_val/(1024*1024*1024):.1f}GB"
        
        print(f"Total Network Out (current cycle): {format_bytes(total_net_out)}")
        print(f"Total Network In (current cycle):  {format_bytes(total_net_in)}")
        print(f"Total Network All (cumulative):    {format_bytes(total_net_all)}")
        print(f"Total Disk All (cumulative):       {format_bytes(total_disk_all)}")
        print(f"Total Disk Current (this cycle):   {format_bytes(total_disk_current)}")
        
        # Show most active process
        most_active_net = max(instances, key=lambda x: x.net_bytes_total)
        most_active_disk = max(instances, key=lambda x: x.disk_total_bytes)
        
        print(f"\nMost active network: PID {most_active_net.pid} ({format_bytes(most_active_net.net_bytes_total)})")
        print(f"Most active disk:    PID {most_active_disk.pid} ({format_bytes(most_active_disk.disk_total_bytes)})")

if __name__ == "__main__":
    test_split_io_display()