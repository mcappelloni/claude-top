#!/usr/bin/env python3
"""Analytics and reporting for Claude process tracking"""

import sqlite3
import sys
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

sys.path.insert(0, os.path.dirname(__file__))
from database_schema import ClaudeDatabase

@dataclass
class UsageReport:
    project_name: str
    session_count: int
    total_runtime_hours: float
    avg_cpu_percent: float
    avg_memory_mb: float
    peak_memory_mb: float
    total_network_bytes: int
    total_disk_bytes: int
    first_seen: str
    last_seen: str
    subprocess_types: Dict[str, int]

@dataclass
class SessionSummary:
    session_id: int
    pid: int
    project_name: str
    start_time: str
    end_time: Optional[str]
    duration_minutes: Optional[float]
    avg_cpu: float
    avg_memory: float
    max_memory: float
    total_network: int
    total_disk: int
    status_changes: List[str]

class ClaudeAnalytics:
    def __init__(self, db_path: str = "claude_tracking.db"):
        self.db_path = db_path
        self.db = ClaudeDatabase(db_path)
    
    def generate_usage_report(self, days: int = 7) -> List[UsageReport]:
        """Generate comprehensive usage report for the last N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get project usage statistics
        cursor.execute('''
            SELECT 
                p.name,
                COUNT(DISTINCT ps.id) as session_count,
                SUM(COALESCE(ps.duration_seconds, 0)) / 3600.0 as total_runtime_hours,
                AVG(pm.cpu_percent) as avg_cpu,
                AVG(pm.memory_mb) as avg_memory,
                MAX(pm.memory_mb) as peak_memory,
                MAX(pm.net_bytes_total) as total_network,
                MAX(pm.disk_total_bytes) as total_disk,
                MIN(ps.start_time) as first_seen,
                MAX(COALESCE(ps.end_time, ps.start_time)) as last_seen
            FROM projects p
            LEFT JOIN process_sessions ps ON p.id = ps.project_id
            LEFT JOIN process_metrics pm ON ps.id = pm.session_id
            WHERE ps.start_time >= datetime('now', '-{} days')
            GROUP BY p.id, p.name
            HAVING session_count > 0
            ORDER BY total_runtime_hours DESC
        '''.format(days))
        
        results = cursor.fetchall()
        reports = []
        
        for row in results:
            # Get subprocess types for this project
            cursor.execute('''
                SELECT pt.command, COUNT(*) as count
                FROM process_tree pt
                JOIN process_sessions ps ON pt.session_id = ps.id
                JOIN projects p ON ps.project_id = p.id
                WHERE p.name = ? AND pt.timestamp >= datetime('now', '-{} days')
                GROUP BY pt.command
                ORDER BY count DESC
            '''.format(days), (row[0],))
            
            subprocess_data = cursor.fetchall()
            subprocess_types = {}
            for cmd, count in subprocess_data:
                # Categorize subprocess types
                cmd_lower = cmd.lower()
                if 'python' in cmd_lower:
                    subprocess_types['Python'] = subprocess_types.get('Python', 0) + count
                elif 'node' in cmd_lower or 'npm' in cmd_lower:
                    subprocess_types['Node.js'] = subprocess_types.get('Node.js', 0) + count
                elif any(term in cmd_lower for term in ['git', 'ssh', 'curl', 'wget']):
                    subprocess_types['System Tools'] = subprocess_types.get('System Tools', 0) + count
                elif 'docker' in cmd_lower:
                    subprocess_types['Docker'] = subprocess_types.get('Docker', 0) + count
                else:
                    subprocess_types['Other'] = subprocess_types.get('Other', 0) + count
            
            reports.append(UsageReport(
                project_name=row[0],
                session_count=row[1] or 0,
                total_runtime_hours=row[2] or 0.0,
                avg_cpu_percent=row[3] or 0.0,
                avg_memory_mb=row[4] or 0.0,
                peak_memory_mb=row[5] or 0.0,
                total_network_bytes=row[6] or 0,
                total_disk_bytes=row[7] or 0,
                first_seen=row[8] or '',
                last_seen=row[9] or '',
                subprocess_types=subprocess_types
            ))
        
        conn.close()
        return reports
    
    def get_session_details(self, session_id: Optional[int] = None, limit: int = 10) -> List[SessionSummary]:
        """Get detailed session information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if session_id:
            where_clause = "WHERE ps.id = ?"
            params = (session_id,)
        else:
            where_clause = "ORDER BY ps.start_time DESC LIMIT ?"
            params = (limit,)
        
        if session_id:
            cursor.execute('''
                SELECT 
                    ps.id, ps.pid, p.name, ps.start_time, ps.end_time, ps.duration_seconds,
                    AVG(pm.cpu_percent) as avg_cpu,
                    AVG(pm.memory_mb) as avg_memory,
                    MAX(pm.memory_mb) as max_memory,
                    MAX(pm.net_bytes_total) as total_network,
                    MAX(pm.disk_total_bytes) as total_disk
                FROM process_sessions ps
                JOIN projects p ON ps.project_id = p.id
                LEFT JOIN process_metrics pm ON ps.id = pm.session_id
                WHERE ps.id = ?
                GROUP BY ps.id, ps.pid, p.name, ps.start_time, ps.end_time, ps.duration_seconds
            ''', params)
        else:
            cursor.execute('''
                SELECT 
                    ps.id, ps.pid, p.name, ps.start_time, ps.end_time, ps.duration_seconds,
                    AVG(pm.cpu_percent) as avg_cpu,
                    AVG(pm.memory_mb) as avg_memory,
                    MAX(pm.memory_mb) as max_memory,
                    MAX(pm.net_bytes_total) as total_network,
                    MAX(pm.disk_total_bytes) as total_disk
                FROM process_sessions ps
                JOIN projects p ON ps.project_id = p.id
                LEFT JOIN process_metrics pm ON ps.id = pm.session_id
                GROUP BY ps.id, ps.pid, p.name, ps.start_time, ps.end_time, ps.duration_seconds
                ORDER BY ps.start_time DESC 
                LIMIT ?
            ''', params)
        
        results = cursor.fetchall()
        summaries = []
        
        for row in results:
            # Get status changes for this session
            cursor.execute('''
                SELECT DISTINCT status, COUNT(*) as count
                FROM process_metrics 
                WHERE session_id = ?
                GROUP BY status
                ORDER BY count DESC
            ''', (row[0],))
            
            status_data = cursor.fetchall()
            status_changes = [f"{status}({count})" for status, count in status_data]
            
            duration_minutes = row[5] / 60.0 if row[5] else None
            
            summaries.append(SessionSummary(
                session_id=row[0],
                pid=row[1],
                project_name=row[2],
                start_time=row[3],
                end_time=row[4],
                duration_minutes=duration_minutes,
                avg_cpu=row[6] or 0.0,
                avg_memory=row[7] or 0.0,
                max_memory=row[8] or 0.0,
                total_network=row[9] or 0,
                total_disk=row[10] or 0,
                status_changes=status_changes
            ))
        
        conn.close()
        return summaries
    
    def get_resource_trends(self, project_name: str, hours: int = 24) -> Dict[str, List]:
        """Get resource usage trends for a project over time"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                datetime(pm.timestamp) as timestamp,
                AVG(pm.cpu_percent) as avg_cpu,
                AVG(pm.memory_mb) as avg_memory,
                SUM(pm.disk_current_bytes) as disk_activity,
                COUNT(DISTINCT ps.pid) as active_processes
            FROM process_metrics pm
            JOIN process_sessions ps ON pm.session_id = ps.id
            JOIN projects p ON ps.project_id = p.id
            WHERE p.name = ? AND pm.timestamp >= datetime('now', '-{} hours')
            GROUP BY datetime(pm.timestamp, '+5 minutes') -- 5-minute intervals
            ORDER BY timestamp
        '''.format(hours), (project_name,))
        
        results = cursor.fetchall()
        
        trends = {
            'timestamps': [],
            'cpu_percent': [],
            'memory_mb': [],
            'disk_activity': [],
            'process_count': []
        }
        
        for row in results:
            trends['timestamps'].append(row[0])
            trends['cpu_percent'].append(row[1] or 0)
            trends['memory_mb'].append(row[2] or 0)
            trends['disk_activity'].append(row[3] or 0)
            trends['process_count'].append(row[4] or 0)
        
        conn.close()
        return trends
    
    def get_subprocess_analysis(self, project_name: Optional[str] = None) -> Dict[str, any]:
        """Analyze subprocess patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if project_name:
            where_clause = "WHERE p.name = ?"
            params = (project_name,)
        else:
            where_clause = ""
            params = ()
        
        cursor.execute(f'''
            SELECT 
                pt.command,
                COUNT(*) as frequency,
                AVG(pt.cpu_percent) as avg_cpu,
                AVG(pt.memory_mb) as avg_memory,
                MAX(pt.depth) as max_depth
            FROM process_tree pt
            JOIN process_sessions ps ON pt.session_id = ps.id
            JOIN projects p ON ps.project_id = p.id
            {where_clause}
            GROUP BY pt.command
            ORDER BY frequency DESC
            LIMIT 20
        ''', params)
        
        results = cursor.fetchall()
        
        analysis = {
            'total_subprocesses': sum(row[1] for row in results),
            'unique_commands': len(results),
            'command_frequency': {},
            'resource_heavy': [],
            'categories': {'Python': 0, 'Node.js': 0, 'System Tools': 0, 'Docker': 0, 'Other': 0}
        }
        
        for cmd, freq, avg_cpu, avg_mem, max_depth in results:
            analysis['command_frequency'][cmd] = freq
            
            # Identify resource-heavy subprocesses
            if avg_cpu > 5.0 or avg_mem > 50.0:
                analysis['resource_heavy'].append({
                    'command': cmd,
                    'frequency': freq,
                    'avg_cpu': avg_cpu,
                    'avg_memory': avg_mem
                })
            
            # Categorize
            cmd_lower = cmd.lower()
            if 'python' in cmd_lower:
                analysis['categories']['Python'] += freq
            elif 'node' in cmd_lower or 'npm' in cmd_lower:
                analysis['categories']['Node.js'] += freq
            elif any(term in cmd_lower for term in ['git', 'ssh', 'curl', 'wget']):
                analysis['categories']['System Tools'] += freq
            elif 'docker' in cmd_lower:
                analysis['categories']['Docker'] += freq
            else:
                analysis['categories']['Other'] += freq
        
        conn.close()
        return analysis
    
    def export_report(self, output_file: str, format: str = 'json'):
        """Export comprehensive report to file"""
        report_data = {
            'generated_at': datetime.now().isoformat(),
            'usage_report_7d': [report.__dict__ for report in self.generate_usage_report(7)],
            'recent_sessions': [session.__dict__ for session in self.get_session_details(limit=20)],
            'subprocess_analysis': self.get_subprocess_analysis()
        }
        
        if format.lower() == 'json':
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        return output_file
    
    def print_usage_summary(self, days: int = 7):
        """Print a formatted usage summary"""
        reports = self.generate_usage_report(days)
        
        print(f"Claude Usage Report - Last {days} Days")
        print("=" * 60)
        
        total_sessions = sum(r.session_count for r in reports)
        total_runtime = sum(r.total_runtime_hours for r in reports)
        
        print(f"Total Projects: {len(reports)}")
        print(f"Total Sessions: {total_sessions}")
        print(f"Total Runtime: {total_runtime:.1f} hours")
        print()
        
        print("Project Breakdown:")
        print("-" * 60)
        print(f"{'Project':<20} {'Sessions':<8} {'Runtime':<10} {'Avg CPU':<8} {'Avg Mem':<10}")
        print("-" * 60)
        
        for report in reports:
            print(f"{report.project_name:<20} {report.session_count:<8} "
                  f"{report.total_runtime_hours:<10.1f} {report.avg_cpu_percent:<8.1f} "
                  f"{report.avg_memory_mb:<10.1f}")
        
        print()
        
        # Subprocess analysis
        subprocess_analysis = self.get_subprocess_analysis()
        print("Subprocess Analysis:")
        print("-" * 40)
        for category, count in subprocess_analysis['categories'].items():
            if count > 0:
                print(f"  {category}: {count} instances")

def test_analytics():
    """Test analytics functions"""
    print("Testing Claude Analytics")
    print("=" * 50)
    
    # Use the test database created earlier
    analytics = ClaudeAnalytics("test_enhanced.db")
    
    # Print usage summary
    analytics.print_usage_summary(7)
    
    print("\n" + "=" * 50)
    print("Recent Session Details:")
    print("=" * 50)
    
    sessions = analytics.get_session_details(limit=5)
    for session in sessions:
        print(f"Session {session.session_id}: PID {session.pid} in {session.project_name}")
        print(f"  Duration: {session.duration_minutes:.1f}min" if session.duration_minutes else "  Still running")
        print(f"  Avg CPU: {session.avg_cpu:.1f}%, Avg Mem: {session.avg_memory:.1f}MB")
        print(f"  Status changes: {', '.join(session.status_changes)}")
        print()
    
    # Export report
    report_file = analytics.export_report("claude_usage_report.json")
    print(f"Full report exported to: {report_file}")

if __name__ == "__main__":
    test_analytics()