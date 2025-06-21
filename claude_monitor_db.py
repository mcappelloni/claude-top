#!/usr/bin/env python3
"""Enhanced Claude monitor with SQLite tracking and subprocess monitoring"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from claude_top_core import ClaudeMonitor, ClaudeInstance
from database_schema import ClaudeDatabase, ProcessTreeNode
from process_tree import ProcessTreeTracker, ProcessNode
import time
from typing import Dict, List, Optional
from collections import defaultdict

class ClaudeMonitorDB(ClaudeMonitor):
    def __init__(self, db_path: str = "claude_tracking.db"):
        super().__init__()
        self.db = ClaudeDatabase(db_path)
        self.tree_tracker = ProcessTreeTracker()
        self.active_sessions: Dict[int, int] = {}  # pid -> session_id
        self.project_cache: Dict[str, int] = {}  # working_dir -> project_id
        self.enable_tree_tracking = True
        self.enable_database_logging = True
    
    def find_claude_processes(self):
        """Enhanced process discovery with database tracking"""
        instances = super().find_claude_processes()
        
        if not self.enable_database_logging:
            return instances
        
        current_pids = {inst.pid for inst in instances}
        
        # End sessions for processes that are no longer running
        ended_pids = set(self.active_sessions.keys()) - current_pids
        for pid in ended_pids:
            session_id = self.active_sessions[pid]
            self.db.end_session(session_id)
            del self.active_sessions[pid]
        
        # Start sessions for new processes and record metrics for all
        for instance in instances:
            if instance.pid not in self.active_sessions:
                # Start new session
                project_id = self.get_or_create_project(instance.working_dir)
                session_id = self.db.start_session(
                    instance.pid, 
                    project_id, 
                    instance.command
                )
                self.active_sessions[instance.pid] = session_id
            
            # Record current metrics
            session_id = self.active_sessions[instance.pid]
            metrics = {
                'cpu_percent': instance.cpu_percent,
                'memory_mb': instance.memory_mb,
                'net_bytes_sent': instance.net_bytes_sent,
                'net_bytes_recv': instance.net_bytes_recv,
                'net_bytes_total': instance.net_bytes_total,
                'disk_total_bytes': instance.disk_total_bytes,
                'disk_current_bytes': instance.disk_current_bytes,
                'connections_count': instance.connections_count,
                'mcp_connections': instance.mcp_connections,
                'status': instance.status
            }
            self.db.record_metrics(session_id, metrics)
            
            # Record process tree if enabled
            if self.enable_tree_tracking:
                self.record_process_tree(instance.pid, session_id)
        
        return instances
    
    def get_or_create_project(self, working_dir: str) -> int:
        """Get or create project with caching"""
        if working_dir in self.project_cache:
            return self.project_cache[working_dir]
        
        project_id = self.db.get_or_create_project(working_dir)
        self.project_cache[working_dir] = project_id
        return project_id
    
    def record_process_tree(self, root_pid: int, session_id: int):
        """Record the process tree for a Claude instance"""
        try:
            tree = self.tree_tracker.discover_process_tree(root_pid, max_depth=2)
            if tree:
                # Convert ProcessNode to ProcessTreeNode for database
                tree_nodes = self.convert_tree_to_db_nodes(tree)
                self.db.record_process_tree(session_id, tree_nodes)
        except Exception as e:
            # Don't let tree tracking failures break monitoring
            pass
    
    def convert_tree_to_db_nodes(self, node: ProcessNode) -> List[ProcessTreeNode]:
        """Convert ProcessNode tree to flat list of ProcessTreeNode for database"""
        nodes = []
        
        def flatten_tree(process_node: ProcessNode):
            db_node = ProcessTreeNode(
                pid=process_node.pid,
                parent_pid=process_node.parent_pid,
                command=process_node.command,
                cpu_percent=process_node.cpu_percent,
                memory_mb=process_node.memory_mb,
                children=[]  # Will be flattened
            )
            nodes.append(db_node)
            
            for child in process_node.children:
                flatten_tree(child)
        
        flatten_tree(node)
        return nodes
    
    def get_project_summary(self) -> Dict[str, any]:
        """Get summary of all tracked projects"""
        stats = self.db.get_project_stats()
        active_sessions = self.db.get_active_sessions()
        
        summary = {
            'total_projects': len(stats),
            'active_sessions': len(active_sessions),
            'projects': {},
            'top_projects': []
        }
        
        for stat in stats:
            summary['projects'][stat.project_name] = {
                'sessions': stat.total_sessions,
                'avg_cpu': stat.avg_cpu,
                'avg_memory': stat.avg_memory,
                'runtime_hours': stat.total_runtime / 3600 if stat.total_runtime else 0,
                'total_network': stat.total_network,
                'total_disk': stat.total_disk
            }
        
        # Sort projects by activity
        summary['top_projects'] = sorted(
            stats, 
            key=lambda x: (x.total_sessions, x.total_runtime), 
            reverse=True
        )[:5]
        
        return summary
    
    def get_subprocess_analysis(self) -> Dict[int, Dict]:
        """Get subprocess analysis for all active Claude processes"""
        analysis = {}
        
        for pid in self.active_sessions.keys():
            try:
                tree = self.tree_tracker.discover_process_tree(pid)
                if tree:
                    analysis[pid] = self.tree_tracker.analyze_subprocess_activity(tree)
            except:
                continue
        
        return analysis
    
    def cleanup_database(self, days: int = 30):
        """Clean up old database entries"""
        self.db.cleanup_old_data(days)
    
    def shutdown(self):
        """Gracefully shutdown and end all active sessions"""
        for pid, session_id in self.active_sessions.items():
            self.db.end_session(session_id)
        self.active_sessions.clear()

def test_enhanced_monitoring():
    """Test the enhanced monitoring with database tracking"""
    print("Testing Enhanced Claude Monitor with Database Tracking")
    print("=" * 70)
    
    # Create monitor with database tracking
    monitor = ClaudeMonitorDB("test_enhanced.db")
    
    try:
        # Run monitoring for several cycles
        for cycle in range(5):
            print(f"\nCycle {cycle + 1}/5:")
            print("-" * 40)
            
            instances = monitor.find_claude_processes()
            print(f"Found {len(instances)} Claude processes")
            
            # Show current activity
            for instance in instances[:3]:  # Show first 3
                print(f"  PID {instance.pid}: {instance.status} - "
                      f"CPU: {instance.cpu_percent:.1f}%, "
                      f"Mem: {instance.memory_mb:.1f}MB, "
                      f"Net: {instance.net_bytes_total}B, "
                      f"Disk: {instance.disk_total_bytes}B")
            
            # Show subprocess analysis
            subprocess_analysis = monitor.get_subprocess_analysis()
            if subprocess_analysis:
                print(f"\nSubprocess Analysis:")
                for pid, analysis in list(subprocess_analysis.items())[:2]:
                    print(f"  PID {pid}: {analysis['total_processes']} processes, "
                          f"{analysis['total_cpu']:.1f}% CPU, "
                          f"{analysis['total_memory']:.1f}MB memory")
            
            if cycle < 4:
                print("Waiting 3 seconds...")
                time.sleep(3)
        
        # Show project summary
        print(f"\n" + "=" * 70)
        print("Project Summary:")
        print("=" * 70)
        
        summary = monitor.get_project_summary()
        print(f"Total Projects: {summary['total_projects']}")
        print(f"Active Sessions: {summary['active_sessions']}")
        
        print(f"\nTop Projects by Activity:")
        for i, project in enumerate(summary['top_projects'], 1):
            print(f"  {i}. {project.project_name}: "
                  f"{project.total_sessions} sessions, "
                  f"avg CPU: {project.avg_cpu:.1f}%, "
                  f"avg Mem: {project.avg_memory:.1f}MB")
        
        # Show active sessions
        active_sessions = monitor.db.get_active_sessions()
        if active_sessions:
            print(f"\nActive Sessions:")
            for session in active_sessions:
                print(f"  PID {session['pid']} in {session['project']}: "
                      f"started at {session['start_time']}")
    
    finally:
        # Cleanup
        monitor.shutdown()
        print(f"\nShutdown complete. Database saved as test_enhanced.db")

if __name__ == "__main__":
    test_enhanced_monitoring()