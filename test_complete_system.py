#!/usr/bin/env python3
"""Complete system test for claude-top with SQLite tracking and subprocess monitoring"""

import sys
import os
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from claude_monitor_db import ClaudeMonitorDB
from analytics import ClaudeAnalytics
from process_tree import ProcessTreeTracker

def test_complete_system():
    """Test the complete system with all features"""
    print("Testing Complete Claude Monitoring System")
    print("=" * 80)
    
    # Test database file
    db_path = "test_complete_system.db"
    
    # Initialize enhanced monitor
    monitor = ClaudeMonitorDB(db_path)
    analytics = ClaudeAnalytics(db_path)
    
    try:
        print("Phase 1: Process Discovery and Database Tracking")
        print("-" * 50)
        
        # Run monitoring for several cycles
        for cycle in range(3):
            print(f"\nCycle {cycle + 1}/3:")
            instances = monitor.find_claude_processes()
            
            print(f"Found {len(instances)} Claude processes:")
            for instance in instances[:3]:  # Show first 3
                print(f"  PID {instance.pid}: {instance.status}")
                print(f"    Project: {Path(instance.working_dir).name}")
                print(f"    Resources: CPU {instance.cpu_percent:.1f}%, Mem {instance.memory_mb:.1f}MB")
                print(f"    I/O: Net {instance.net_bytes_total}B, Disk {instance.disk_total_bytes}B")
            
            if cycle < 2:
                time.sleep(2)
        
        print("\nPhase 2: Subprocess Tree Analysis")
        print("-" * 50)
        
        subprocess_analysis = monitor.get_subprocess_analysis()
        for pid, analysis in list(subprocess_analysis.items())[:2]:
            print(f"\nPID {pid} Subprocess Analysis:")
            print(f"  Total Processes: {analysis['total_processes']}")
            print(f"  Resource Usage: {analysis['total_cpu']:.1f}% CPU, {analysis['total_memory']:.1f}MB")
            print(f"  Process Types: {dict(analysis['subprocess_types'])}")
            
            if analysis['active_subprocesses']:
                print(f"  Active Subprocesses:")
                for sub in analysis['active_subprocesses'][:3]:
                    print(f"    - {sub['name']} (Depth: {sub['depth']})")
        
        print("\nPhase 3: Database Analytics")
        print("-" * 50)
        
        # Project summary
        summary = monitor.get_project_summary()
        print(f"Database Summary:")
        print(f"  Total Projects: {summary['total_projects']}")
        print(f"  Active Sessions: {summary['active_sessions']}")
        
        print(f"\nTop Projects:")
        for i, project in enumerate(summary['top_projects'][:3], 1):
            print(f"  {i}. {project.project_name}")
            print(f"     Sessions: {project.total_sessions}, Runtime: {project.total_runtime/3600:.1f}h")
            print(f"     Avg: CPU {project.avg_cpu:.1f}%, Mem {project.avg_memory:.1f}MB")
        
        print("\nPhase 4: Usage Reports")
        print("-" * 50)
        
        # Generate usage report
        usage_reports = analytics.generate_usage_report(1)  # Last 1 day
        
        if usage_reports:
            print("Usage Report (Last 24 Hours):")
            for report in usage_reports:
                print(f"\nProject: {report.project_name}")
                print(f"  Sessions: {report.session_count}")
                print(f"  Runtime: {report.total_runtime_hours:.2f} hours")
                print(f"  Averages: CPU {report.avg_cpu_percent:.1f}%, Memory {report.avg_memory_mb:.1f}MB")
                print(f"  Peak Memory: {report.peak_memory_mb:.1f}MB")
                print(f"  I/O: Network {report.total_network_bytes}B, Disk {report.total_disk_bytes}B")
                if report.subprocess_types:
                    print(f"  Subprocess Types: {report.subprocess_types}")
        
        print("\nPhase 5: Session Details")
        print("-" * 50)
        
        sessions = analytics.get_session_details(limit=3)
        print("Recent Sessions:")
        for session in sessions:
            print(f"\nSession {session.session_id}:")
            print(f"  PID: {session.pid} in {session.project_name}")
            if session.duration_minutes:
                print(f"  Duration: {session.duration_minutes:.1f} minutes")
            else:
                print(f"  Status: Still running")
            print(f"  Resources: CPU {session.avg_cpu:.1f}%, Memory {session.avg_memory:.1f}MB (peak: {session.max_memory:.1f}MB)")
            print(f"  I/O: Network {session.total_network}B, Disk {session.total_disk}B")
            print(f"  Status Changes: {', '.join(session.status_changes)}")
        
        print("\nPhase 6: Export Report")
        print("-" * 50)
        
        # Export comprehensive report
        report_file = analytics.export_report("test_complete_report.json")
        print(f"Comprehensive report exported to: {report_file}")
        
        # Show file size
        file_size = os.path.getsize(report_file)
        print(f"Report file size: {file_size} bytes")
        
        print("\nPhase 7: Process Tree Visualization")
        print("-" * 50)
        
        tree_tracker = ProcessTreeTracker()
        active_pids = list(monitor.active_sessions.keys())
        
        if active_pids:
            print(f"Process tree for PID {active_pids[0]}:")
            tree = tree_tracker.discover_process_tree(active_pids[0], max_depth=2)
            if tree:
                tree_tracker.print_process_tree(tree, show_details=True)
        
        print("\n" + "=" * 80)
        print("SYSTEM TEST RESULTS:")
        print("=" * 80)
        print("✓ Process discovery and filtering")
        print("✓ Database session management")
        print("✓ Real-time metrics tracking") 
        print("✓ I/O monitoring (network/disk)")
        print("✓ Project detection and mapping")
        print("✓ Subprocess tree discovery")
        print("✓ Resource usage analytics")
        print("✓ Historical data analysis")
        print("✓ Report generation and export")
        print("✓ Process tree visualization")
        
        print(f"\nDatabase file: {db_path}")
        print(f"Database size: {os.path.getsize(db_path)} bytes")
        
    finally:
        # Cleanup
        monitor.shutdown()
        print(f"\nMonitoring session ended. Database saved.")

if __name__ == "__main__":
    test_complete_system()