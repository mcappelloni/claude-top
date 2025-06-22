#!/usr/bin/env python3
"""Productivity metrics and session analysis for Claude Top"""

import sqlite3
import curses
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import math

@dataclass
class ProductivityMetrics:
    """Productivity metrics for a time period"""
    timeframe: str
    total_sessions: int
    active_time: int  # seconds spent in 'running' state
    idle_time: int    # seconds spent in 'idle' state
    waiting_time: int # seconds spent in 'waiting' state
    avg_session_length: float
    productivity_score: float  # 0-100 based on active vs idle ratio
    peak_hours: List[int]      # Most productive hours
    most_productive_day: str
    efficiency_rating: str     # Poor/Fair/Good/Excellent
    focus_score: float         # Based on session continuity
    project_switching: int     # Number of project switches
    avg_cpu_during_active: float
    memory_efficiency: float

@dataclass 
class SessionPattern:
    """Pattern analysis for individual sessions"""
    session_id: int
    project_name: str
    duration: int
    active_percentage: float
    cpu_efficiency: float
    memory_stability: float
    interruptions: int
    productivity_rating: str

class ProductivityAnalyzer:
    def __init__(self, db_path: str = "claude_tracking.db"):
        self.db_path = db_path
    
    def calculate_productivity_metrics(self, days: int = 7) -> ProductivityMetrics:
        """Calculate comprehensive productivity metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get session data with status breakdown
        cursor.execute('''
            SELECT 
                ps.id,
                ps.duration_seconds,
                pm.status,
                COUNT(*) as status_count,
                pm.cpu_percent,
                pm.memory_mb,
                strftime('%H', ps.start_time) as hour,
                DATE(ps.start_time) as date,
                p.name as project_name
            FROM process_sessions ps
            JOIN projects p ON ps.project_id = p.id
            LEFT JOIN process_metrics pm ON ps.id = pm.session_id
            WHERE ps.start_time >= ? AND ps.start_time <= ?
            GROUP BY ps.id, pm.status
            ORDER BY ps.start_time
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        session_data = cursor.fetchall()
        
        # Calculate time spent in each state
        active_time = 0
        idle_time = 0  
        waiting_time = 0
        total_sessions = 0
        session_durations = []
        hourly_activity = defaultdict(int)
        daily_activity = defaultdict(int)
        project_switches = 0
        last_project = None
        cpu_during_active = []
        memory_values = []
        
        sessions_by_id = defaultdict(list)
        for row in session_data:
            sessions_by_id[row[0]].append(row)
        
        for session_id, metrics in sessions_by_id.items():
            total_sessions += 1
            session_duration = metrics[0][1] or 0
            session_durations.append(session_duration)
            
            # Track project switching
            current_project = metrics[0][8]
            if last_project and last_project != current_project:
                project_switches += 1
            last_project = current_project
            
            # Calculate time in each state for this session
            for metric in metrics:
                status = metric[2]
                count = metric[3]
                cpu = metric[4] or 0
                memory = metric[5] or 0
                hour = int(metric[6]) if metric[6] else 0
                date = metric[7]
                
                if status == 'running':
                    active_time += count
                    cpu_during_active.append(cpu)
                    hourly_activity[hour] += count
                    daily_activity[date] += count
                elif status == 'idle':
                    idle_time += count
                elif status == 'waiting':
                    waiting_time += count
                
                if memory > 0:
                    memory_values.append(memory)
        
        # Calculate metrics
        total_time = active_time + idle_time + waiting_time
        avg_session_length = sum(session_durations) / len(session_durations) if session_durations else 0
        
        # Productivity score: active time as percentage of total time
        productivity_score = (active_time / total_time * 100) if total_time > 0 else 0
        
        # Find peak hours (top 3)
        peak_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_hours = [hour for hour, _ in peak_hours]
        
        # Most productive day
        most_productive_day = max(daily_activity.items(), key=lambda x: x[1])[0] if daily_activity else "N/A"
        
        # Efficiency rating
        if productivity_score >= 80:
            efficiency_rating = "Excellent"
        elif productivity_score >= 60:
            efficiency_rating = "Good"
        elif productivity_score >= 40:
            efficiency_rating = "Fair"
        else:
            efficiency_rating = "Poor"
        
        # Focus score: based on average session length and project switching
        focus_base = min(100, avg_session_length / 60)  # Longer sessions = better focus
        focus_penalty = min(50, project_switches * 5)    # Frequent switching = lower focus
        focus_score = max(0, focus_base - focus_penalty)
        
        # Average CPU during active periods
        avg_cpu_active = sum(cpu_during_active) / len(cpu_during_active) if cpu_during_active else 0
        
        # Memory efficiency (lower variance = more efficient)
        memory_efficiency = 100 - (max(memory_values) - min(memory_values)) / max(memory_values) * 100 if memory_values else 0
        memory_efficiency = max(0, min(100, memory_efficiency))
        
        conn.close()
        
        timeframe_desc = f"Last {days} days" if days > 1 else "Today"
        
        return ProductivityMetrics(
            timeframe=timeframe_desc,
            total_sessions=total_sessions,
            active_time=active_time,
            idle_time=idle_time,
            waiting_time=waiting_time,
            avg_session_length=avg_session_length,
            productivity_score=productivity_score,
            peak_hours=peak_hours,
            most_productive_day=most_productive_day,
            efficiency_rating=efficiency_rating,
            focus_score=focus_score,
            project_switching=project_switches,
            avg_cpu_during_active=avg_cpu_active,
            memory_efficiency=memory_efficiency
        )
    
    def analyze_session_patterns(self, days: int = 7) -> List[SessionPattern]:
        """Analyze individual session patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get detailed session metrics
        cursor.execute('''
            SELECT 
                ps.id,
                p.name,
                ps.duration_seconds,
                COUNT(CASE WHEN pm.status = 'running' THEN 1 END) as active_count,
                COUNT(pm.id) as total_count,
                AVG(pm.cpu_percent) as avg_cpu,
                MAX(pm.memory_mb) - MIN(pm.memory_mb) as memory_range,
                AVG(pm.memory_mb) as avg_memory,
                COUNT(DISTINCT pm.status) as status_changes
            FROM process_sessions ps
            JOIN projects p ON ps.project_id = p.id
            LEFT JOIN process_metrics pm ON ps.id = pm.session_id
            WHERE ps.start_time >= ? AND ps.start_time <= ?
                AND ps.duration_seconds > 60  -- Only analyze sessions > 1 minute
            GROUP BY ps.id
            HAVING total_count > 5  -- Only sessions with enough data points
            ORDER BY ps.start_time DESC
            LIMIT 20
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        results = cursor.fetchall()
        conn.close()
        
        patterns = []
        for row in results:
            session_id = row[0]
            project_name = row[1]
            duration = row[2] or 0
            active_count = row[3] or 0
            total_count = row[4] or 1
            avg_cpu = row[5] or 0
            memory_range = row[6] or 0
            avg_memory = row[7] or 0
            status_changes = row[8] or 1
            
            # Calculate metrics
            active_percentage = (active_count / total_count) * 100
            cpu_efficiency = min(100, avg_cpu * 2)  # Higher CPU = more efficiency (capped at 100)
            memory_stability = max(0, 100 - (memory_range / avg_memory * 100)) if avg_memory > 0 else 100
            interruptions = max(0, status_changes - 2)  # -2 because start/end are expected
            
            # Productivity rating
            if active_percentage >= 80 and cpu_efficiency >= 60:
                rating = "Excellent"
            elif active_percentage >= 60 and cpu_efficiency >= 40:
                rating = "Good"
            elif active_percentage >= 40:
                rating = "Fair"
            else:
                rating = "Poor"
            
            patterns.append(SessionPattern(
                session_id=session_id,
                project_name=project_name,
                duration=duration,
                active_percentage=active_percentage,
                cpu_efficiency=cpu_efficiency,
                memory_stability=memory_stability,
                interruptions=interruptions,
                productivity_rating=rating
            ))
        
        return patterns
    
    def get_productivity_trends(self, days: int = 30) -> List[Tuple[str, float, int]]:
        """Get daily productivity trends"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        cursor.execute('''
            SELECT 
                DATE(ps.start_time) as date,
                COUNT(CASE WHEN pm.status = 'running' THEN 1 END) as active_samples,
                COUNT(pm.id) as total_samples,
                COUNT(DISTINCT ps.id) as sessions
            FROM process_sessions ps
            LEFT JOIN process_metrics pm ON ps.id = pm.session_id
            WHERE ps.start_time >= ? AND ps.start_time <= ?
            GROUP BY DATE(ps.start_time)
            ORDER BY date DESC
            LIMIT 14
        ''', (start_date.isoformat(), end_date.isoformat()))
        
        results = cursor.fetchall()
        conn.close()
        
        trends = []
        for row in results:
            date = row[0]
            active_samples = row[1] or 0
            total_samples = row[2] or 1
            sessions = row[3] or 0
            
            productivity = (active_samples / total_samples) * 100
            trends.append((date, productivity, sessions))
        
        return trends
    
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
    
    def render_productivity_overview(self, stdscr, metrics: ProductivityMetrics) -> None:
        """Render productivity metrics overview"""
        height, width = stdscr.getmaxyx()
        
        # Header
        title = f"Productivity Analysis - {metrics.timeframe}"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Productivity score
        y = 2
        stdscr.addstr(y, 2, "Productivity Overview", curses.A_BOLD | curses.A_UNDERLINE)
        y += 2
        
        # Score with color coding
        score_color = curses.color_pair(1)  # Green
        if metrics.productivity_score < 40:
            score_color = curses.color_pair(3)  # Red
        elif metrics.productivity_score < 60:
            score_color = curses.color_pair(2)  # Yellow
        
        stdscr.addstr(y, 4, f"Productivity Score: ", curses.A_BOLD)
        stdscr.addstr(y, 24, f"{metrics.productivity_score:.1f}%", score_color | curses.A_BOLD)
        stdscr.addstr(y, 32, f"({metrics.efficiency_rating})")
        
        # Time breakdown
        y += 2
        total_time = metrics.active_time + metrics.idle_time + metrics.waiting_time
        stdscr.addstr(y, 4, f"Time Breakdown:")
        y += 1
        stdscr.addstr(y, 6, f"Active:  {self.format_duration(metrics.active_time):<10} ({metrics.active_time/total_time*100:.1f}%)" if total_time > 0 else "Active:  0s")
        y += 1
        stdscr.addstr(y, 6, f"Waiting: {self.format_duration(metrics.waiting_time):<10} ({metrics.waiting_time/total_time*100:.1f}%)" if total_time > 0 else "Waiting: 0s")
        y += 1
        stdscr.addstr(y, 6, f"Idle:    {self.format_duration(metrics.idle_time):<10} ({metrics.idle_time/total_time*100:.1f}%)" if total_time > 0 else "Idle:    0s")
        
        # Session statistics
        y += 3
        stdscr.addstr(y, 2, "Session Statistics", curses.A_BOLD | curses.A_UNDERLINE)
        y += 2
        stdscr.addstr(y, 4, f"Total Sessions: {metrics.total_sessions}")
        y += 1
        stdscr.addstr(y, 4, f"Avg Session Length: {self.format_duration(int(metrics.avg_session_length))}")
        y += 1
        stdscr.addstr(y, 4, f"Focus Score: {metrics.focus_score:.1f}/100")
        y += 1
        stdscr.addstr(y, 4, f"Project Switches: {metrics.project_switching}")
        
        # Performance metrics
        y += 3
        stdscr.addstr(y, 2, "Performance Metrics", curses.A_BOLD | curses.A_UNDERLINE)
        y += 2
        stdscr.addstr(y, 4, f"Avg CPU (Active): {metrics.avg_cpu_during_active:.1f}%")
        y += 1
        stdscr.addstr(y, 4, f"Memory Efficiency: {metrics.memory_efficiency:.1f}%")
        
        # Peak hours
        if metrics.peak_hours:
            y += 3
            stdscr.addstr(y, 2, "Peak Productivity Hours", curses.A_BOLD | curses.A_UNDERLINE)
            y += 1
            hours_str = ", ".join([f"{h:02d}:00" for h in metrics.peak_hours])
            stdscr.addstr(y + 1, 4, f"Most Active: {hours_str}")
        
        # Most productive day
        if metrics.most_productive_day != "N/A":
            y += 3
            stdscr.addstr(y, 4, f"Most Productive Day: {metrics.most_productive_day}")
        
        # Controls
        controls = "Press 'Q' to return | 'S' session details | 'T' trends | 'E' export"
        stdscr.addstr(height - 1, 2, controls[:width-4])
    
    def render_session_patterns(self, stdscr, patterns: List[SessionPattern]) -> None:
        """Render session pattern analysis"""
        height, width = stdscr.getmaxyx()
        
        # Header
        title = "Session Pattern Analysis"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Column headers
        y = 2
        headers = f"{'Project':<20} {'Duration':<10} {'Active%':<8} {'CPU Eff':<8} {'Rating':<10}"
        stdscr.addstr(y, 2, headers, curses.A_BOLD | curses.A_UNDERLINE)
        
        y += 2
        for i, pattern in enumerate(patterns[:height-6]):
            if y + i >= height - 2:
                break
            
            # Color code by rating
            color = curses.color_pair(1)  # Green
            if pattern.productivity_rating == "Poor":
                color = curses.color_pair(3)  # Red
            elif pattern.productivity_rating == "Fair":
                color = curses.color_pair(2)  # Yellow
            
            project = pattern.project_name[:18] + ".." if len(pattern.project_name) > 20 else pattern.project_name
            duration = self.format_duration(pattern.duration)
            active_pct = f"{pattern.active_percentage:.1f}%"
            cpu_eff = f"{pattern.cpu_efficiency:.1f}%"
            rating = pattern.productivity_rating
            
            line = f"{project:<20} {duration:<10} {active_pct:<8} {cpu_eff:<8} {rating:<10}"
            stdscr.addstr(y + i, 2, line[:width-4], color)
        
        # Controls
        controls = "Press 'Q' to return | 'O' overview | 'T' trends"
        stdscr.addstr(height - 1, 2, controls[:width-4])

def test_productivity():
    """Test productivity analysis"""
    print("Testing Productivity Analysis")
    print("=" * 40)
    
    analyzer = ProductivityAnalyzer()
    
    # Test productivity metrics
    metrics = analyzer.calculate_productivity_metrics(7)
    print(f"Productivity metrics for {metrics.timeframe}:")
    print(f"  Score: {metrics.productivity_score:.1f}% ({metrics.efficiency_rating})")
    print(f"  Sessions: {metrics.total_sessions}")
    print(f"  Focus Score: {metrics.focus_score:.1f}/100")
    print(f"  Active Time: {analyzer.format_duration(metrics.active_time)}")
    
    # Test session patterns
    patterns = analyzer.analyze_session_patterns(7)
    print(f"\nSession patterns ({len(patterns)} analyzed):")
    for pattern in patterns[:3]:
        print(f"  {pattern.project_name}: {pattern.productivity_rating} - {pattern.active_percentage:.1f}% active")
    
    # Test trends
    trends = analyzer.get_productivity_trends(14)
    print(f"\nProductivity trends ({len(trends)} days):")
    for date, productivity, sessions in trends[:3]:
        print(f"  {date}: {productivity:.1f}% productivity, {sessions} sessions")

if __name__ == "__main__":
    test_productivity()