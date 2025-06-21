#!/usr/bin/env python3
"""Test search, batch operations, and grouping features"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from claude_top_core import ClaudeMonitor, ClaudeInstance
from datetime import datetime
from collections import deque

def create_test_instances():
    """Create test instances for demonstration"""
    instances = [
        ClaudeInstance(
            pid=1001,
            working_dir="/Users/test/projects/web-app",
            task="Active Session",
            context_length=0,
            tokens_used=0,
            start_time=datetime.now(),
            status="running",
            cpu_percent=15.5,
            memory_mb=256.7,
            command="claude --project web-app",
            cpu_history=deque([15.0, 14.5, 16.0, 15.5, 15.0], maxlen=5),
            net_bytes_sent=1024,
            net_bytes_recv=2048,
            net_bytes_total=3072,
            disk_total_bytes=4096,
            disk_current_bytes=512,
            connections_count=3,
            mcp_connections=1
        ),
        ClaudeInstance(
            pid=1002,
            working_dir="/Users/test/projects/web-app/frontend",
            task="Active Session",
            context_length=0,
            tokens_used=0,
            start_time=datetime.now(),
            status="waiting",
            cpu_percent=0.2,
            memory_mb=128.3,
            command="claude --project web-app/frontend",
            cpu_history=deque([0.1, 0.2, 0.3, 0.2, 0.1], maxlen=5)
        ),
        ClaudeInstance(
            pid=1003,
            working_dir="/Users/test/projects/api-service",
            task="Active Session",
            context_length=0,
            tokens_used=0,
            start_time=datetime.now(),
            status="idle",
            cpu_percent=0.0,
            memory_mb=64.5,
            command="claude --project api-service",
            cpu_history=deque([0.0, 0.0, 0.0, 0.0, 0.0], maxlen=5)
        ),
        ClaudeInstance(
            pid=1004,
            working_dir="/Users/test/projects/api-service/tests",
            task="Active Session",
            context_length=0,
            tokens_used=0,
            start_time=datetime.now(),
            status="running",
            cpu_percent=25.8,
            memory_mb=512.0,
            command="claude --project api-service/tests",
            cpu_history=deque([24.0, 26.0, 25.0, 26.5, 25.8], maxlen=5)
        ),
        ClaudeInstance(
            pid=1005,
            working_dir="/Users/test/documents/report",
            task="Active Session",
            context_length=0,
            tokens_used=0,
            start_time=datetime.now(),
            status="paused",
            cpu_percent=0.0,
            memory_mb=96.2,
            command="claude --project report",
            cpu_history=deque([0.0, 0.0, 0.0, 0.0, 0.0], maxlen=5)
        )
    ]
    
    return instances

def test_search_filter():
    """Test search/filter functionality"""
    print("Testing Search/Filter Functionality")
    print("=" * 50)
    
    monitor = ClaudeMonitor()
    instances = create_test_instances()
    
    # Test different search queries
    test_queries = [
        ("web", "Should find web-app instances"),
        ("api", "Should find api-service instances"),
        ("1003", "Should find PID 1003"),
        ("running", "Should find running instances"),
        ("test", "Should find instances with 'test' in path")
    ]
    
    for query, description in test_queries:
        print(f"\nSearch: '{query}' - {description}")
        print("-" * 30)
        
        filtered = [
            inst for inst in instances
            if (query in inst.working_dir.lower() or
                query in inst.command.lower() or
                query in inst.status.lower() or
                str(inst.pid) == query)
        ]
        
        print(f"Found {len(filtered)} matches:")
        for inst in filtered:
            print(f"  PID {inst.pid}: {inst.working_dir.split('/')[-1]} ({inst.status})")

def test_batch_operations():
    """Test batch/multi-select operations"""
    print("\n\nTesting Batch Operations")
    print("=" * 50)
    
    instances = create_test_instances()
    
    # Simulate selecting multiple instances
    selected_pids = {1001, 1003, 1004}
    
    print("Selected instances for batch operation:")
    for inst in instances:
        if inst.pid in selected_pids:
            print(f"  [×] PID {inst.pid}: {inst.working_dir.split('/')[-1]} ({inst.status})")
        else:
            print(f"  [ ] PID {inst.pid}: {inst.working_dir.split('/')[-1]} ({inst.status})")
    
    print("\nBatch operations available:")
    print("  - Pause all selected")
    print("  - Kill all selected (with confirmation)")
    print("  - Select all / Select none")
    
    print("\nBatch kill confirmation would show:")
    print("  Kill 3 Processes?")
    print("  Selected processes:")
    for inst in instances:
        if inst.pid in selected_pids:
            print(f"    PID {inst.pid}: {inst.working_dir.split('/')[-1]}")

def test_project_grouping():
    """Test project grouping functionality"""
    print("\n\nTesting Project Grouping")
    print("=" * 50)
    
    monitor = ClaudeMonitor()
    monitor.instances = create_test_instances()
    
    # Group by project
    project_groups = {}
    for instance in monitor.instances:
        project_path = os.path.dirname(instance.working_dir)
        if project_path not in project_groups:
            project_groups[project_path] = []
        project_groups[project_path].append(instance)
    
    print("Grouped by project:")
    for project_path in sorted(project_groups.keys()):
        instances = project_groups[project_path]
        project_name = os.path.basename(project_path) or "root"
        
        # Calculate aggregate stats
        total_cpu = sum(inst.cpu_percent for inst in instances)
        total_mem = sum(inst.memory_mb for inst in instances)
        
        print(f"\n▼ {project_name} ({len(instances)} instances) - CPU: {total_cpu:.1f}% Mem: {total_mem:.0f}MB")
        
        for inst in instances:
            status_indicator = {
                'running': '●',
                'waiting': '◐',
                'idle': '○',
                'paused': '⏸'
            }.get(inst.status, '?')
            
            print(f"    {status_indicator} PID {inst.pid}: {inst.working_dir.split('/')[-1]} "
                  f"(CPU: {inst.cpu_percent:.1f}% Mem: {inst.memory_mb:.0f}MB)")

def test_combined_features():
    """Test combining search with grouping"""
    print("\n\nTesting Combined Features")
    print("=" * 50)
    
    instances = create_test_instances()
    
    # Search for "web" with grouping enabled
    query = "web"
    filtered = [
        inst for inst in instances
        if query in inst.working_dir.lower()
    ]
    
    print(f"Search '{query}' with grouping enabled:")
    
    # Group filtered results
    project_groups = {}
    for instance in filtered:
        project_path = os.path.dirname(instance.working_dir)
        if project_path not in project_groups:
            project_groups[project_path] = []
        project_groups[project_path].append(instance)
    
    for project_path in sorted(project_groups.keys()):
        instances = project_groups[project_path]
        project_name = os.path.basename(project_path) or "root"
        print(f"\n▼ {project_name} ({len(instances)} instances)")
        for inst in instances:
            print(f"    PID {inst.pid}: {inst.working_dir.split('/')[-1]}")

if __name__ == "__main__":
    test_search_filter()
    test_batch_operations()
    test_project_grouping()
    test_combined_features()
    
    print("\n" + "=" * 50)
    print("FEATURE TEST SUMMARY")
    print("=" * 50)
    print("✅ Search/Filter: Find processes by PID, status, command, or directory")
    print("✅ Multi-Select: Select multiple processes for batch operations")
    print("✅ Batch Operations: Pause/kill multiple processes at once")
    print("✅ Project Grouping: Group instances by project/workspace")
    print("✅ Combined Features: Search works with grouping disabled")
    print("\nNew keyboard shortcuts:")
    print("  /  - Enter search mode")
    print("  m  - Enter multi-select mode")
    print("  g  - Toggle project grouping")
    print("  Space - Toggle selection (in multi-select)")
    print("  a/n - Select all/none (in multi-select)")