#!/usr/bin/env python3
"""Historical Analytics Dashboard for Claude Top"""

import sqlite3
import curses
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import math

@dataclass
class AnalyticsData:
    """Data structure for analytics calculations"""
    timeframe: str
    total_sessions: int
    total_runtime: int
    avg_cpu: float
    avg_memory: float
    peak_cpu: float
    peak_memory: float
    total_network: int
    total_disk: int
    productive_hours: List[int]  # Hours with most activity
    top_projects: List[Tuple[str, int]]  # (project, session_count)

class HistoricalAnalytics:
    def __init__(self, db_path: str = "claude_tracking.db"):
        self.db_path = db_path
        self.current_view = "overview"  # overview, daily, weekly, monthly, projects
        self.selected_timeframe = 7  # days
        
    def get_analytics_data(self, days: int = 7) -> AnalyticsData:
        """Get comprehensive analytics data for the specified timeframe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get basic session statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_sessions,
                SUM(COALESCE(duration_seconds, 0)) as total_runtime,
                COUNT(DISTINCT project_id) as unique_projects
            FROM process_sessions 
            WHERE start_time >= ? AND start_time <= ?
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        session_stats = cursor.fetchone()
        total_sessions = session_stats[0] or 0
        total_runtime = session_stats[1] or 0
        unique_projects = session_stats[2] or 0
        
        # Get resource usage statistics
        cursor.execute('''
            SELECT 
                AVG(pm.cpu_percent) as avg_cpu,
                AVG(pm.memory_mb) as avg_memory,
                MAX(pm.cpu_percent) as peak_cpu,
                MAX(pm.memory_mb) as peak_memory,
                MAX(pm.net_bytes_total) as total_network,
                MAX(pm.disk_total_bytes) as total_disk
            FROM process_metrics pm
            JOIN process_sessions ps ON pm.session_id = ps.id
            WHERE ps.start_time >= ? AND ps.start_time <= ?
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        resource_stats = cursor.fetchone()
        avg_cpu = resource_stats[0] or 0.0
        avg_memory = resource_stats[1] or 0.0
        peak_cpu = resource_stats[2] or 0.0
        peak_memory = resource_stats[3] or 0.0
        total_network = resource_stats[4] or 0
        total_disk = resource_stats[5] or 0
        
        # Get hourly activity pattern
        cursor.execute('''
            SELECT 
                CAST(strftime('%H', ps.start_time) AS INTEGER) as hour,
                COUNT(*) as sessions
            FROM process_sessions ps
            WHERE ps.start_time >= ? AND ps.start_time <= ?
            GROUP BY hour
            ORDER BY sessions DESC
            LIMIT 5
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        hourly_data = cursor.fetchall()
        productive_hours = [row[0] for row in hourly_data]
        
        # Get top projects by session count
        cursor.execute('''
            SELECT 
                p.name,
                COUNT(ps.id) as session_count
            FROM projects p
            JOIN process_sessions ps ON p.id = ps.project_id
            WHERE ps.start_time >= ? AND ps.start_time <= ?
            GROUP BY p.id, p.name
            ORDER BY session_count DESC
            LIMIT 10
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        project_data = cursor.fetchall()
        top_projects = [(row[0], row[1]) for row in project_data]
        
        conn.close()
        
        timeframe_desc = f"Last {days} days" if days > 1 else "Today"
        
        return AnalyticsData(
            timeframe=timeframe_desc,
            total_sessions=total_sessions,
            total_runtime=total_runtime,
            avg_cpu=avg_cpu,
            avg_memory=avg_memory,
            peak_cpu=peak_cpu,
            peak_memory=peak_memory,
            total_network=total_network,
            total_disk=total_disk,
            productive_hours=productive_hours,
            top_projects=top_projects
        )
    
    def get_daily_trends(self, days: int = 30) -> List[Tuple[str, int, int]]:
        """Get daily session and runtime trends"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        cursor.execute('''
            SELECT 
                DATE(start_time) as date,
                COUNT(*) as sessions,
                SUM(COALESCE(duration_seconds, 0)) as runtime
            FROM process_sessions 
            WHERE start_time >= ? AND start_time <= ?
            GROUP BY DATE(start_time)
            ORDER BY date DESC
            LIMIT 14
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        results = cursor.fetchall()
        conn.close()
        
        return [(row[0], row[1], row[2]) for row in results]
    
    def get_project_analytics(self) -> List[Dict]:
        """Get detailed project analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
                MAX(COALESCE(ps.end_time, ps.start_time)) as last_session
            FROM projects p
            LEFT JOIN process_sessions ps ON p.id = ps.project_id
            LEFT JOIN process_metrics pm ON ps.id = pm.session_id
            WHERE ps.start_time >= datetime('now', '-30 days')
            GROUP BY p.id, p.name, p.path
            HAVING total_sessions > 0
            ORDER BY total_sessions DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        projects = []
        for row in results:
            projects.append({
                'name': row[0],
                'path': row[1],
                'sessions': row[2] or 0,
                'avg_cpu': row[3] or 0.0,
                'avg_memory': row[4] or 0.0,
                'runtime': row[5] or 0,
                'network': row[6] or 0,
                'disk': row[7] or 0,
                'first_session': row[8],
                'last_session': row[9]
            })
        
        return projects
    
    def format_duration(self, seconds: int) -> str:
        """Format duration in human readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m{seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h{minutes}m"
    
    def format_bytes(self, bytes_val: int) -> str:
        """Format bytes in human readable format"""
        if bytes_val == 0:
            return "0B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        value = float(bytes_val)
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(value)}{units[unit_index]}"
        else:
            return f"{value:.1f}{units[unit_index]}"
    
    def create_ascii_chart(self, data: List[int], width: int = 50, height: int = 10) -> List[str]:
        """Create ASCII bar chart from data"""
        if not data or max(data) == 0:
            return [" " * width for _ in range(height)]
        
        # Normalize data to chart height
        max_val = max(data)
        normalized = [int((val / max_val) * height) for val in data]
        
        chart = []
        for row in range(height - 1, -1, -1):
            line = ""
            for val in normalized:
                if val > row:
                    line += "█"
                else:
                    line += " "
            chart.append(line[:width])
        
        return chart
    
    def create_horizontal_bar(self, value: float, max_value: float, width: int = 30) -> str:
        """Create horizontal bar for displaying percentages/values"""
        if max_value == 0:
            return "─" * width
        
        filled = int((value / max_value) * width)
        bar = "█" * filled + "─" * (width - filled)
        return bar
    
    def render_overview(self, stdscr, data: AnalyticsData) -> None:
        """Render overview analytics screen"""
        height, width = stdscr.getmaxyx()
        
        # Header
        title = f"Claude Analytics - {data.timeframe}"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Key metrics section
        y = 2
        stdscr.addstr(y, 2, "Key Metrics", curses.A_BOLD | curses.A_UNDERLINE)
        y += 2
        
        # Session statistics
        stdscr.addstr(y, 4, f"Total Sessions: {data.total_sessions}")
        stdscr.addstr(y + 1, 4, f"Total Runtime: {self.format_duration(data.total_runtime)}")
        
        if data.total_sessions > 0:
            avg_session = data.total_runtime // data.total_sessions
            stdscr.addstr(y + 2, 4, f"Avg Session: {self.format_duration(avg_session)}")
        
        # Resource usage
        y += 4
        stdscr.addstr(y, 4, f"Average CPU: {data.avg_cpu:.1f}%")
        stdscr.addstr(y + 1, 4, f"Peak CPU: {data.peak_cpu:.1f}%")
        stdscr.addstr(y + 2, 4, f"Average Memory: {data.avg_memory:.0f}MB")
        stdscr.addstr(y + 3, 4, f"Peak Memory: {data.peak_memory:.0f}MB")
        
        # I/O statistics
        y += 5
        stdscr.addstr(y, 4, f"Network I/O: {self.format_bytes(data.total_network)}")
        stdscr.addstr(y + 1, 4, f"Disk I/O: {self.format_bytes(data.total_disk)}")
        
        # Productive hours
        if data.productive_hours:
            y += 3
            stdscr.addstr(y, 2, "Most Active Hours", curses.A_BOLD | curses.A_UNDERLINE)
            y += 1
            hours_str = ", ".join([f"{h:02d}:00" for h in data.productive_hours[:3]])
            stdscr.addstr(y + 1, 4, f"Peak Hours: {hours_str}")
        
        # Top projects
        if data.top_projects:
            y += 3
            stdscr.addstr(y, 2, "Top Projects", curses.A_BOLD | curses.A_UNDERLINE)
            y += 1
            
            for i, (project, sessions) in enumerate(data.top_projects[:5]):
                if y + i + 1 < height - 3:
                    project_display = project[:25] + "..." if len(project) > 25 else project
                    stdscr.addstr(y + i + 1, 4, f"{project_display:<28} {sessions:>3} sessions")
        
        # Controls
        controls = "Q:exit | 1-3:days | T:trends | P:projects | R:productivity | S:sessions | E:export"
        stdscr.addstr(height - 1, 2, controls[:width-4])
    
    def render_daily_trends(self, stdscr) -> None:
        """Render daily trends chart"""
        height, width = stdscr.getmaxyx()
        
        trends = self.get_daily_trends(14)
        if not trends:
            stdscr.addstr(height // 2, width // 2 - 10, "No data available")
            return
        
        # Header
        title = "Daily Activity Trends (Last 14 Days)"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Prepare data for chart
        sessions_data = [t[1] for t in trends]
        runtime_data = [t[2] // 3600 for t in trends]  # Convert to hours
        
        # Sessions chart
        y = 3
        stdscr.addstr(y, 2, "Daily Sessions", curses.A_BOLD)
        
        if sessions_data:
            chart_height = min(8, height - 15)
            chart = self.create_ascii_chart(sessions_data, width - 20, chart_height)
            
            for i, line in enumerate(chart):
                if y + i + 2 < height - 5:
                    stdscr.addstr(y + i + 2, 4, line)
            
            # Add scale
            max_sessions = max(sessions_data) if sessions_data else 0
            stdscr.addstr(y + 1, 4, f"Max: {max_sessions}")
        
        # Runtime chart
        y += chart_height + 4
        if y < height - 8:
            stdscr.addstr(y, 2, "Daily Runtime (Hours)", curses.A_BOLD)
            
            if runtime_data:
                chart = self.create_ascii_chart(runtime_data, width - 20, chart_height)
                
                for i, line in enumerate(chart):
                    if y + i + 2 < height - 3:
                        stdscr.addstr(y + i + 2, 4, line)
                
                # Add scale
                max_hours = max(runtime_data) if runtime_data else 0
                stdscr.addstr(y + 1, 4, f"Max: {max_hours}h")
        
        # Controls
        controls = "Q:exit | O:overview | P:projects | R:productivity | S:sessions | E:export"
        stdscr.addstr(height - 1, 2, controls[:width-4])
    
    def render_project_analytics(self, stdscr) -> None:
        """Render detailed project analytics"""
        height, width = stdscr.getmaxyx()
        
        projects = self.get_project_analytics()
        if not projects:
            stdscr.addstr(height // 2, width // 2 - 10, "No project data available")
            return
        
        # Header
        title = "Project Analytics (Last 30 Days)"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Column headers
        y = 2
        headers = f"{'Project':<20} {'Sessions':<8} {'Runtime':<10} {'CPU%':<6} {'Memory':<8} {'Network':<10}"
        stdscr.addstr(y, 2, headers, curses.A_BOLD | curses.A_UNDERLINE)
        
        y += 2
        for i, project in enumerate(projects[:height-6]):
            if y + i >= height - 2:
                break
                
            name = project['name'][:18] + ".." if len(project['name']) > 20 else project['name']
            sessions = project['sessions']
            runtime = self.format_duration(project['runtime'])
            cpu = f"{project['avg_cpu']:.1f}"
            memory = f"{project['avg_memory']:.0f}MB"
            network = self.format_bytes(project['network'])
            
            line = f"{name:<20} {sessions:<8} {runtime:<10} {cpu:<6} {memory:<8} {network:<10}"
            stdscr.addstr(y + i, 2, line[:width-4])
        
        # Controls
        controls = "Q:exit | O:overview | T:trends | R:productivity | S:sessions | E:export"
        stdscr.addstr(height - 1, 2, controls[:width-4])

def test_analytics():
    """Test the analytics functionality"""
    print("Testing Historical Analytics")
    print("=" * 40)
    
    analytics = HistoricalAnalytics("claude_tracking.db")
    
    # Test data retrieval
    data = analytics.get_analytics_data(7)
    print(f"Analytics for {data.timeframe}:")
    print(f"  Sessions: {data.total_sessions}")
    print(f"  Runtime: {analytics.format_duration(data.total_runtime)}")
    print(f"  Avg CPU: {data.avg_cpu:.1f}%")
    print(f"  Peak Memory: {data.peak_memory:.0f}MB")
    
    # Test trends
    trends = analytics.get_daily_trends(7)
    print(f"\nDaily trends ({len(trends)} days):")
    for date, sessions, runtime in trends[:3]:
        print(f"  {date}: {sessions} sessions, {analytics.format_duration(runtime)}")
    
    # Test projects
    projects = analytics.get_project_analytics()
    print(f"\nTop projects ({len(projects)} total):")
    for project in projects[:3]:
        print(f"  {project['name']}: {project['sessions']} sessions")

if __name__ == "__main__":
    test_analytics()