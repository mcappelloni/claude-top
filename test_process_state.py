#!/usr/bin/env python3
"""Test script to analyze Claude process states"""

import psutil
import time
from collections import deque

def analyze_claude_processes():
    """Analyze Claude processes to determine their state"""
    
    # Track CPU usage over time for each process
    cpu_history = {}
    
    print("Monitoring Claude processes for 10 seconds to detect states...")
    print("(Processes with consistent 0% CPU are likely waiting for input)")
    print("-" * 80)
    
    for i in range(10):
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('claude' in cmd.lower() for cmd in cmdline):
                    cmdline_str = ' '.join(cmdline)
                    # Skip non-CLI processes
                    if 'Claude.app' in cmdline_str or 'docker' in cmdline_str:
                        continue
                    
                    pid = proc.info['pid']
                    cpu = proc.cpu_percent(interval=0.1)
                    
                    # Initialize history for new processes
                    if pid not in cpu_history:
                        cpu_history[pid] = {
                            'samples': deque(maxlen=10),
                            'cmdline': cmdline_str,
                            'cwd': proc.cwd() if hasattr(proc, 'cwd') else 'Unknown'
                        }
                    
                    cpu_history[pid]['samples'].append(cpu)
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        time.sleep(1)
        print(f"Sample {i+1}/10 collected...")
    
    print("\nAnalysis Results:")
    print("-" * 80)
    
    for pid, data in cpu_history.items():
        samples = list(data['samples'])
        avg_cpu = sum(samples) / len(samples) if samples else 0
        max_cpu = max(samples) if samples else 0
        
        # Determine state based on CPU patterns
        if avg_cpu < 0.5 and max_cpu < 1.0:
            state = "WAITING (for user input)"
        elif avg_cpu > 5.0:
            state = "RUNNING (active processing)"
        else:
            state = "IDLE (minimal activity)"
        
        print(f"\nPID: {pid}")
        print(f"Working Dir: {data['cwd']}")
        print(f"CPU samples: {[f'{x:.1f}%' for x in samples[-5:]]}")
        print(f"Average CPU: {avg_cpu:.2f}%")
        print(f"Max CPU: {max_cpu:.2f}%")
        print(f"State: {state}")

if __name__ == "__main__":
    analyze_claude_processes()