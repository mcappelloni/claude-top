#!/usr/bin/env python3
"""Test the updated Claude detection with state analysis"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from claude_top_core import ClaudeMonitor
import time

def test_detection():
    """Test the new detection logic"""
    monitor = ClaudeMonitor()
    
    print("Testing Claude process detection with state analysis...")
    print("=" * 70)
    
    # Run for a few cycles to build CPU history
    for cycle in range(3):
        print(f"\nCycle {cycle + 1}/3:")
        instances = monitor.find_claude_processes()
        
        for instance in instances:
            print(f"PID: {instance.pid}")
            print(f"  Working Dir: {instance.working_dir}")
            print(f"  Status: {instance.status}")
            print(f"  CPU: {instance.cpu_percent:.1f}%")
            print(f"  CPU History: {[f'{x:.1f}' for x in instance.cpu_history]}")
            print(f"  Memory: {instance.memory_mb:.1f}MB")
            print()
        
        if cycle < 2:
            print("Waiting 2 seconds for next sample...")
            time.sleep(2)
    
    print(f"Total processes found: {len(instances)}")
    print("State distribution:")
    states = {}
    for instance in instances:
        states[instance.status] = states.get(instance.status, 0) + 1
    
    for state, count in states.items():
        print(f"  {state}: {count}")

if __name__ == "__main__":
    test_detection()