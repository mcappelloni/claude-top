#!/usr/bin/env python3
"""SQLite database schema for Claude process tracking"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class ProjectStats:
    project_name: str
    total_sessions: int
    avg_cpu: float
    avg_memory: float
    total_runtime: int  # seconds
    total_network: int  # bytes
    total_disk: int     # bytes

@dataclass
class ProcessTreeNode:
    pid: int
    parent_pid: int
    command: str
    cpu_percent: float
    memory_mb: float
    children: List['ProcessTreeNode']

class ClaudeDatabase:
    def __init__(self, db_path: str = "claude_tracking.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Projects table - tracks working directories/projects
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Process sessions table - tracks Claude instance sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pid INTEGER NOT NULL,
                project_id INTEGER,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration_seconds INTEGER,
                command TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')
        
        # Process metrics table - tracks resource usage over time
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cpu_percent REAL,
                memory_mb REAL,
                net_bytes_sent INTEGER DEFAULT 0,
                net_bytes_recv INTEGER DEFAULT 0,
                net_bytes_total INTEGER DEFAULT 0,
                disk_total_bytes INTEGER DEFAULT 0,
                disk_current_bytes INTEGER DEFAULT 0,
                connections_count INTEGER DEFAULT 0,
                mcp_connections INTEGER DEFAULT 0,
                status TEXT,
                FOREIGN KEY (session_id) REFERENCES process_sessions (id)
            )
        ''')
        
        # Process tree table - tracks parent-child relationships
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_tree (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                pid INTEGER NOT NULL,
                parent_pid INTEGER,
                command TEXT,
                depth INTEGER DEFAULT 0,
                cpu_percent REAL DEFAULT 0,
                memory_mb REAL DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES process_sessions (id)
            )
        ''')
        
        # Project statistics view
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS project_stats AS
            SELECT 
                p.id,
                p.name,
                p.path,
                COUNT(DISTINCT ps.id) as total_sessions,
                AVG(pm.cpu_percent) as avg_cpu,
                AVG(pm.memory_mb) as avg_memory,
                SUM(COALESCE(ps.duration_seconds, 0)) as total_runtime,
                MAX(pm.net_bytes_total) as max_network,
                MAX(pm.disk_total_bytes) as max_disk,
                MIN(ps.start_time) as first_seen,
                MAX(COALESCE(ps.end_time, ps.start_time)) as last_seen
            FROM projects p
            LEFT JOIN process_sessions ps ON p.id = ps.project_id
            LEFT JOIN process_metrics pm ON ps.id = pm.session_id
            GROUP BY p.id, p.name, p.path
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_process_sessions_pid ON process_sessions(pid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_process_metrics_session_id ON process_metrics(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_process_metrics_timestamp ON process_metrics(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_process_tree_session_id ON process_tree(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_process_tree_pid ON process_tree(pid)')
        
        conn.commit()
        conn.close()
    
    def get_or_create_project(self, working_dir: str) -> int:
        """Get existing project or create new one based on working directory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Extract project name from path
        if working_dir and working_dir != 'Unknown':
            project_name = os.path.basename(working_dir)
            if not project_name:
                project_name = working_dir.split('/')[-2] if len(working_dir.split('/')) > 1 else 'root'
        else:
            project_name = 'unknown'
            working_dir = 'Unknown'
        
        # Try to find existing project
        cursor.execute(
            'SELECT id FROM projects WHERE path = ? OR name = ?',
            (working_dir, project_name)
        )
        result = cursor.fetchone()
        
        if result:
            project_id = result[0]
            # Update last_seen
            cursor.execute(
                'UPDATE projects SET last_seen = CURRENT_TIMESTAMP WHERE id = ?',
                (project_id,)
            )
        else:
            # Create new project
            cursor.execute(
                'INSERT INTO projects (name, path) VALUES (?, ?)',
                (project_name, working_dir)
            )
            project_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return project_id
    
    def start_session(self, pid: int, project_id: int, command: str) -> int:
        """Start a new process session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO process_sessions (pid, project_id, start_time, command, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (pid, project_id, datetime.now(), command, 'running'))
        
        session_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return session_id
    
    def end_session(self, session_id: int):
        """End a process session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get start time to calculate duration
        cursor.execute('SELECT start_time FROM process_sessions WHERE id = ?', (session_id,))
        result = cursor.fetchone()
        
        if result:
            start_time = datetime.fromisoformat(result[0])
            duration = int((datetime.now() - start_time).total_seconds())
            
            cursor.execute('''
                UPDATE process_sessions 
                SET end_time = CURRENT_TIMESTAMP, duration_seconds = ?, status = ?
                WHERE id = ?
            ''', (duration, 'ended', session_id))
        
        conn.commit()
        conn.close()
    
    def record_metrics(self, session_id: int, metrics: Dict):
        """Record process metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO process_metrics (
                session_id, cpu_percent, memory_mb, net_bytes_sent, net_bytes_recv,
                net_bytes_total, disk_total_bytes, disk_current_bytes,
                connections_count, mcp_connections, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            metrics.get('cpu_percent', 0),
            metrics.get('memory_mb', 0),
            metrics.get('net_bytes_sent', 0),
            metrics.get('net_bytes_recv', 0),
            metrics.get('net_bytes_total', 0),
            metrics.get('disk_total_bytes', 0),
            metrics.get('disk_current_bytes', 0),
            metrics.get('connections_count', 0),
            metrics.get('mcp_connections', 0),
            metrics.get('status', 'unknown')
        ))
        
        conn.commit()
        conn.close()
    
    def record_process_tree(self, session_id: int, tree_nodes: List[ProcessTreeNode]):
        """Record process tree structure"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing tree data for this session and timestamp
        cursor.execute('''
            DELETE FROM process_tree 
            WHERE session_id = ? AND timestamp = date('now')
        ''', (session_id,))
        
        def insert_node(node: ProcessTreeNode, depth: int = 0):
            cursor.execute('''
                INSERT INTO process_tree (
                    session_id, pid, parent_pid, command, depth, cpu_percent, memory_mb
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, node.pid, node.parent_pid, node.command,
                depth, node.cpu_percent, node.memory_mb
            ))
            
            # Recursively insert children
            for child in node.children:
                insert_node(child, depth + 1)
        
        for node in tree_nodes:
            insert_node(node)
        
        conn.commit()
        conn.close()
    
    def get_project_stats(self, project_name: Optional[str] = None) -> List[ProjectStats]:
        """Get project statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if project_name:
            cursor.execute('SELECT * FROM project_stats WHERE name = ?', (project_name,))
        else:
            cursor.execute('SELECT * FROM project_stats ORDER BY total_sessions DESC')
        
        results = cursor.fetchall()
        conn.close()
        
        stats = []
        for row in results:
            stats.append(ProjectStats(
                project_name=row[1],
                total_sessions=row[3] or 0,
                avg_cpu=row[4] or 0.0,
                avg_memory=row[5] or 0.0,
                total_runtime=row[6] or 0,
                total_network=row[7] or 0,
                total_disk=row[8] or 0
            ))
        
        return stats
    
    def get_active_sessions(self) -> List[Dict]:
        """Get currently active sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ps.id, ps.pid, p.name, ps.start_time, ps.command
            FROM process_sessions ps
            JOIN projects p ON ps.project_id = p.id
            WHERE ps.end_time IS NULL
            ORDER BY ps.start_time DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        sessions = []
        for row in results:
            sessions.append({
                'session_id': row[0],
                'pid': row[1],
                'project': row[2],
                'start_time': row[3],
                'command': row[4]
            })
        
        return sessions
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old data beyond specified days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clean old metrics data
        cursor.execute('''
            DELETE FROM process_metrics 
            WHERE timestamp < datetime('now', '-{} days')
        '''.format(days))
        
        # Clean old tree data
        cursor.execute('''
            DELETE FROM process_tree 
            WHERE timestamp < datetime('now', '-{} days')
        '''.format(days))
        
        conn.commit()
        conn.close()

def test_database():
    """Test the database functionality"""
    print("Testing Claude Database Schema")
    print("=" * 40)
    
    # Create test database
    db = ClaudeDatabase("test_claude.db")
    
    # Test project creation
    project_id = db.get_or_create_project("/Users/test/claude-project")
    print(f"Created project with ID: {project_id}")
    
    # Test session management
    session_id = db.start_session(12345, project_id, "claude chat")
    print(f"Started session with ID: {session_id}")
    
    # Test metrics recording
    test_metrics = {
        'cpu_percent': 15.5,
        'memory_mb': 256.7,
        'net_bytes_sent': 1024,
        'net_bytes_recv': 512,
        'net_bytes_total': 1536,
        'disk_total_bytes': 4096,
        'status': 'running'
    }
    db.record_metrics(session_id, test_metrics)
    print("Recorded test metrics")
    
    # Test project stats
    stats = db.get_project_stats()
    for stat in stats:
        print(f"Project: {stat.project_name}, Sessions: {stat.total_sessions}, Avg CPU: {stat.avg_cpu:.1f}%")
    
    # Clean up test database
    os.remove("test_claude.db")
    print("Database test completed")

if __name__ == "__main__":
    test_database()