#!/usr/bin/env python3
"""Test script to check if claude-top can detect Claude instances"""

import psutil
from datetime import datetime

def find_claude_processes():
    """Find all Claude CLI processes running on the system"""
    claude_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cwd', 'create_time', 'cpu_percent', 'memory_info']):
        try:
            # Check if this is a Claude CLI process
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any('claude' in cmd.lower() for cmd in cmdline):
                cmdline_str = ' '.join(cmdline)
                # Skip Claude desktop app processes
                if 'Claude.app' in cmdline_str or 'Claude Helper' in cmdline_str or 'chrome_crashpad' in cmdline_str or 'Squirrel' in cmdline_str:
                    continue
                # Skip docker processes unless they're Claude-related containers
                if 'docker' in cmdline_str and 'mcp/filesystem' in cmdline_str:
                    continue
                    
                # Try to get working directory
                cwd = proc.info.get('cwd', None)
                if not cwd or cwd == '/':
                    try:
                        cwd = proc.cwd()
                    except:
                        cwd = 'Unknown'
                
                # Print process information
                print(f"\nFound Claude CLI process:")
                print(f"  PID: {proc.info['pid']}")
                print(f"  Command: {cmdline_str}")
                print(f"  Working Dir: {cwd}")
                print(f"  CPU %: {proc.info.get('cpu_percent', 0.0)}")
                print(f"  Memory MB: {proc.info.get('memory_info').rss / 1024 / 1024 if proc.info.get('memory_info') else 0:.2f}")
                print(f"  Status: {proc.status()}")
                claude_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print(f"Error accessing process: {e}")
            continue
    
    return claude_processes

if __name__ == "__main__":
    print("Searching for Claude CLI instances...")
    processes = find_claude_processes()
    print(f"\nTotal Claude instances found: {len(processes)}")