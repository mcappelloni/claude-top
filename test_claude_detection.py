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
                # Print process information
                print(f"\nFound Claude process:")
                print(f"  PID: {proc.info['pid']}")
                print(f"  Command: {' '.join(cmdline)}")
                print(f"  Working Dir: {proc.info.get('cwd', 'Unknown')}")
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