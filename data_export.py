#!/usr/bin/env python3
"""Data export functionality for Claude Top"""

import csv
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

class DataExporter:
    def __init__(self, db_path: str = "claude_tracking.db"):
        self.db_path = db_path
        
    def export_sessions_csv(self, output_file: str, days: int = 30) -> bool:
        """Export session data to CSV format"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get session data with project information
            cursor.execute('''
                SELECT 
                    ps.id as session_id,
                    ps.pid,
                    p.name as project_name,
                    p.path as project_path,
                    ps.start_time,
                    ps.end_time,
                    ps.duration_seconds,
                    ps.command,
                    ps.status,
                    AVG(pm.cpu_percent) as avg_cpu,
                    AVG(pm.memory_mb) as avg_memory,
                    MAX(pm.net_bytes_total) as total_network,
                    MAX(pm.disk_total_bytes) as total_disk,
                    COUNT(pm.id) as metric_samples
                FROM process_sessions ps
                JOIN projects p ON ps.project_id = p.id
                LEFT JOIN process_metrics pm ON ps.id = pm.session_id
                WHERE ps.start_time >= ? AND ps.start_time <= ?
                GROUP BY ps.id
                ORDER BY ps.start_time DESC
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            results = cursor.fetchall()
            conn.close()
            
            # Write CSV file
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                header = [
                    'session_id', 'pid', 'project_name', 'project_path',
                    'start_time', 'end_time', 'duration_seconds', 'command', 'status',
                    'avg_cpu_percent', 'avg_memory_mb', 'total_network_bytes',
                    'total_disk_bytes', 'metric_samples'
                ]
                writer.writerow(header)
                
                # Write data
                for row in results:
                    writer.writerow(row)
            
            return True
            
        except Exception as e:
            print(f"Error exporting sessions CSV: {e}")
            return False
    
    def export_metrics_csv(self, output_file: str, days: int = 7) -> bool:
        """Export detailed metrics data to CSV format"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Get detailed metrics with session and project info
            cursor.execute('''
                SELECT 
                    pm.id as metric_id,
                    pm.session_id,
                    ps.pid,
                    p.name as project_name,
                    pm.timestamp,
                    pm.cpu_percent,
                    pm.memory_mb,
                    pm.net_bytes_sent,
                    pm.net_bytes_recv,
                    pm.net_bytes_total,
                    pm.disk_total_bytes,
                    pm.disk_current_bytes,
                    pm.connections_count,
                    pm.mcp_connections,
                    pm.status
                FROM process_metrics pm
                JOIN process_sessions ps ON pm.session_id = ps.id
                JOIN projects p ON ps.project_id = p.id
                WHERE pm.timestamp >= ? AND pm.timestamp <= ?
                ORDER BY pm.timestamp DESC
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            results = cursor.fetchall()
            conn.close()
            
            # Write CSV file
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                header = [
                    'metric_id', 'session_id', 'pid', 'project_name', 'timestamp',
                    'cpu_percent', 'memory_mb', 'net_bytes_sent', 'net_bytes_recv',
                    'net_bytes_total', 'disk_total_bytes', 'disk_current_bytes',
                    'connections_count', 'mcp_connections', 'status'
                ]
                writer.writerow(header)
                
                # Write data
                for row in results:
                    writer.writerow(row)
            
            return True
            
        except Exception as e:
            print(f"Error exporting metrics CSV: {e}")
            return False
    
    def export_project_summary_csv(self, output_file: str) -> bool:
        """Export project summary statistics to CSV"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get project statistics
            cursor.execute('''
                SELECT 
                    p.name,
                    p.path,
                    COUNT(DISTINCT ps.id) as total_sessions,
                    AVG(pm.cpu_percent) as avg_cpu,
                    AVG(pm.memory_mb) as avg_memory,
                    SUM(COALESCE(ps.duration_seconds, 0)) as total_runtime,
                    MAX(pm.net_bytes_total) as max_network,
                    MAX(pm.disk_total_bytes) as max_disk,
                    MIN(ps.start_time) as first_session,
                    MAX(COALESCE(ps.end_time, ps.start_time)) as last_session,
                    COUNT(pm.id) as total_metrics
                FROM projects p
                LEFT JOIN process_sessions ps ON p.id = ps.project_id
                LEFT JOIN process_metrics pm ON ps.id = pm.session_id
                GROUP BY p.id, p.name, p.path
                HAVING total_sessions > 0
                ORDER BY total_sessions DESC
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            # Write CSV file
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                header = [
                    'project_name', 'project_path', 'total_sessions', 'avg_cpu_percent',
                    'avg_memory_mb', 'total_runtime_seconds', 'max_network_bytes',
                    'max_disk_bytes', 'first_session', 'last_session', 'total_metrics'
                ]
                writer.writerow(header)
                
                # Write data
                for row in results:
                    writer.writerow(row)
            
            return True
            
        except Exception as e:
            print(f"Error exporting project summary CSV: {e}")
            return False
    
    def export_data_json(self, output_file: str, days: int = 30) -> bool:
        """Export comprehensive data to JSON format"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            export_data = {
                'export_info': {
                    'generated_at': datetime.now().isoformat(),
                    'timeframe_start': start_date.isoformat(),
                    'timeframe_end': end_date.isoformat(),
                    'days_included': days
                },
                'projects': [],
                'sessions': [],
                'daily_summaries': []
            }
            
            # Get projects
            cursor.execute('''
                SELECT id, name, path, created_at, last_seen
                FROM projects
                ORDER BY name
            ''')
            projects = cursor.fetchall()
            
            for project in projects:
                export_data['projects'].append({
                    'id': project[0],
                    'name': project[1],
                    'path': project[2],
                    'created_at': project[3],
                    'last_seen': project[4]
                })
            
            # Get sessions with metrics summary
            cursor.execute('''
                SELECT 
                    ps.id, ps.pid, ps.project_id, ps.start_time, ps.end_time,
                    ps.duration_seconds, ps.command, ps.status,
                    COUNT(pm.id) as metric_count,
                    AVG(pm.cpu_percent) as avg_cpu,
                    AVG(pm.memory_mb) as avg_memory,
                    MAX(pm.net_bytes_total) as total_network,
                    MAX(pm.disk_total_bytes) as total_disk
                FROM process_sessions ps
                LEFT JOIN process_metrics pm ON ps.id = pm.session_id
                WHERE ps.start_time >= ? AND ps.start_time <= ?
                GROUP BY ps.id
                ORDER BY ps.start_time DESC
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            sessions = cursor.fetchall()
            
            for session in sessions:
                export_data['sessions'].append({
                    'id': session[0],
                    'pid': session[1],
                    'project_id': session[2],
                    'start_time': session[3],
                    'end_time': session[4],
                    'duration_seconds': session[5],
                    'command': session[6],
                    'status': session[7],
                    'metrics': {
                        'count': session[8] or 0,
                        'avg_cpu_percent': session[9] or 0,
                        'avg_memory_mb': session[10] or 0,
                        'total_network_bytes': session[11] or 0,
                        'total_disk_bytes': session[12] or 0
                    }
                })
            
            # Get daily summaries
            cursor.execute('''
                SELECT 
                    DATE(ps.start_time) as date,
                    COUNT(DISTINCT ps.id) as sessions,
                    SUM(COALESCE(ps.duration_seconds, 0)) as total_runtime,
                    AVG(pm.cpu_percent) as avg_cpu,
                    AVG(pm.memory_mb) as avg_memory,
                    COUNT(DISTINCT ps.project_id) as unique_projects
                FROM process_sessions ps
                LEFT JOIN process_metrics pm ON ps.id = pm.session_id
                WHERE ps.start_time >= ? AND ps.start_time <= ?
                GROUP BY DATE(ps.start_time)
                ORDER BY date DESC
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            daily_data = cursor.fetchall()
            
            for day in daily_data:
                export_data['daily_summaries'].append({
                    'date': day[0],
                    'sessions': day[1],
                    'total_runtime_seconds': day[2] or 0,
                    'avg_cpu_percent': day[3] or 0,
                    'avg_memory_mb': day[4] or 0,
                    'unique_projects': day[5] or 0
                })
            
            conn.close()
            
            # Write JSON file
            with open(output_file, 'w', encoding='utf-8') as jsonfile:
                json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error exporting JSON: {e}")
            return False
    
    def get_export_stats(self) -> Dict:
        """Get statistics about available data for export"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get basic stats
            cursor.execute('SELECT COUNT(*) FROM projects')
            total_projects = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM process_sessions')
            total_sessions = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM process_metrics')
            total_metrics = cursor.fetchone()[0]
            
            # Get date range
            cursor.execute('SELECT MIN(start_time), MAX(start_time) FROM process_sessions')
            date_range = cursor.fetchone()
            
            # Get recent activity
            cursor.execute('''
                SELECT COUNT(*) FROM process_sessions 
                WHERE start_time >= datetime('now', '-7 days')
            ''')
            recent_sessions = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_projects': total_projects,
                'total_sessions': total_sessions,
                'total_metrics': total_metrics,
                'date_range': {
                    'earliest': date_range[0],
                    'latest': date_range[1]
                },
                'recent_sessions_7d': recent_sessions
            }
            
        except Exception as e:
            return {'error': str(e)}

def test_export():
    """Test export functionality"""
    print("Testing Data Export Functionality")
    print("=" * 40)
    
    exporter = DataExporter()
    
    # Get export stats
    stats = exporter.get_export_stats()
    print(f"Available data:")
    print(f"  Projects: {stats.get('total_projects', 0)}")
    print(f"  Sessions: {stats.get('total_sessions', 0)}")
    print(f"  Metrics: {stats.get('total_metrics', 0)}")
    
    if stats.get('date_range', {}).get('earliest'):
        print(f"  Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")
    
    # Test CSV exports
    print("\nTesting CSV exports...")
    
    # Export sessions (last 7 days)
    if exporter.export_sessions_csv("test_sessions.csv", 7):
        print("✓ Sessions CSV exported successfully")
        
        # Check file size
        path = Path("test_sessions.csv")
        if path.exists():
            print(f"  File size: {path.stat().st_size} bytes")
    else:
        print("✗ Sessions CSV export failed")
    
    # Export project summary
    if exporter.export_project_summary_csv("test_projects.csv"):
        print("✓ Project summary CSV exported successfully")
    else:
        print("✗ Project summary CSV export failed")
    
    # Test JSON export
    print("\nTesting JSON export...")
    if exporter.export_data_json("test_export.json", 7):
        print("✓ JSON export completed successfully")
        
        # Check file size
        path = Path("test_export.json")
        if path.exists():
            print(f"  File size: {path.stat().st_size} bytes")
    else:
        print("✗ JSON export failed")
    
    print("\nExport test completed!")

if __name__ == "__main__":
    test_export()