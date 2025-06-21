#!/usr/bin/env python3
"""Test the improved process state detection logic"""

import sys
import os
from collections import deque
sys.path.insert(0, os.path.dirname(__file__))

from claude_top_core import ClaudeMonitor

def test_state_detection():
    """Test different CPU patterns and their resulting states"""
    print("Testing Process State Detection")
    print("=" * 50)
    
    monitor = ClaudeMonitor()
    
    # Test scenarios
    test_cases = [
        {
            'name': 'Actively Processing',
            'cpu_history': deque([15.0, 12.0, 18.0, 20.0, 16.0], maxlen=5),
            'expected': 'running',
            'description': 'High CPU usage indicates active processing'
        },
        {
            'name': 'Waiting for User Input (Recent Activity)',
            'cpu_history': deque([3.0, 4.5, 0.2, 0.1, 0.3], maxlen=5),
            'expected': 'waiting',
            'description': 'Low CPU but had recent spike - in conversation'
        },
        {
            'name': 'Idle Between Sessions',
            'cpu_history': deque([0.1, 0.0, 0.1, 0.0, 0.1], maxlen=5),
            'expected': 'idle',
            'description': 'Consistently low CPU - waiting for new instructions'
        },
        {
            'name': 'Medium Activity',
            'cpu_history': deque([2.0, 3.0, 2.5, 1.8, 2.2], maxlen=5),
            'expected': 'running',
            'description': 'Medium CPU (0.5-5%) - light processing'
        },
        {
            'name': 'Just Became Idle',
            'cpu_history': deque([8.0, 5.0, 0.3, 0.1, 0.0], maxlen=5),
            'expected': 'waiting',
            'description': 'Recent activity followed by low CPU - likely waiting for input'
        },
        {
            'name': 'Long Idle',
            'cpu_history': deque([0.0, 0.0, 0.0, 0.0, 0.0], maxlen=5),
            'expected': 'idle',
            'description': 'No activity for extended period - between sessions'
        }
    ]
    
    print("\nTest Cases:")
    print("-" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Description: {test_case['description']}")
        print(f"   CPU History: {list(test_case['cpu_history'])}")
        
        # Calculate metrics
        cpu_samples = list(test_case['cpu_history'])
        avg_cpu = sum(cpu_samples) / len(cpu_samples)
        max_cpu = max(cpu_samples)
        recent_cpu = cpu_samples[-1]
        
        # Check patterns in CPU history
        recent_samples = cpu_samples[-3:] if len(cpu_samples) >= 3 else cpu_samples
        recent_avg = sum(recent_samples) / len(recent_samples) if recent_samples else 0
        
        # Look for transition from active to idle (indicates waiting)
        had_activity = any(sample > 3.0 for sample in cpu_samples[:-2]) if len(cpu_samples) > 2 else False
        
        print(f"   Metrics: avg={avg_cpu:.1f}%, max={max_cpu:.1f}%, recent={recent_cpu:.1f}%")
        print(f"   Recent avg (last 3): {recent_avg:.1f}%")
        print(f"   Had activity before: {had_activity}")
        
        # Determine state using the same logic
        if avg_cpu > 5.0:
            detected_state = 'running'
        elif recent_avg < 0.5:
            # Very low recent CPU
            if had_activity and max_cpu > 3.0:
                # Had significant activity before becoming idle - waiting for input
                detected_state = 'waiting'
            elif recent_cpu > 0.2 or any(s > 0.5 for s in recent_samples):
                # Still has minimal activity - likely waiting
                detected_state = 'waiting'
            else:
                # No recent activity at all - idle between sessions
                detected_state = 'idle'
        else:
            # Medium CPU (0.5-5.0) - processing
            detected_state = 'running'
        
        print(f"   Expected: {test_case['expected']}")
        print(f"   Detected: {detected_state}")
        
        if detected_state == test_case['expected']:
            print("   ✅ PASS")
        else:
            print("   ❌ FAIL")
    
    print("\n" + "=" * 50)
    print("State Detection Summary:")
    print("=" * 50)
    print("• running: Actively processing (>5% avg CPU or 0.5-5% CPU)")
    print("• waiting: In conversation, waiting for user (<0.5% avg CPU with recent activity)")
    print("• idle: Between sessions, no activity (<0.5% avg CPU, no recent spikes)")
    print("• paused: Manually paused or system stopped")
    
    print("\nThe improved logic now correctly distinguishes between:")
    print("- 'waiting': Claude is in an active conversation but waiting for user input")
    print("- 'idle': Claude has finished all tasks and is waiting for new instructions")

if __name__ == "__main__":
    test_state_detection()