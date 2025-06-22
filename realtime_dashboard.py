#!/usr/bin/env python3
"""Real-time dashboard updates for Claude Top"""

import time
import curses
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class RealTimeMetrics:
    """Real-time metrics tracking"""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    active_sessions: int
    network_activity: int
    productivity_score: float
    alert_count: int

@dataclass
class LiveChart:
    """Live updating chart data"""
    title: str
    data_points: deque = field(default_factory=lambda: deque(maxlen=60))  # Last 60 data points
    max_value: float = 100.0
    min_value: float = 0.0
    unit: str = "%"
    color_threshold_high: float = 80.0
    color_threshold_medium: float = 50.0

class RealTimeDashboard:
    def __init__(self, max_history: int = 300):  # 5 minutes at 1-second intervals
        self.max_history = max_history
        self.metrics_history = deque(maxlen=max_history)
        self.last_update = 0
        self.update_interval = 1.0  # Update every second
        
        # Live charts
        self.charts = {
            'cpu': LiveChart("CPU Usage", unit="%", max_value=100),
            'memory': LiveChart("Memory Usage", unit="MB", max_value=2000),
            'sessions': LiveChart("Active Sessions", unit="", max_value=50),
            'productivity': LiveChart("Productivity", unit="%", max_value=100),
            'network': LiveChart("Network Activity", unit="KB/s", max_value=1000),
            'alerts': LiveChart("Alert Count", unit="", max_value=10)
        }
        
        # Animation state
        self.animation_frame = 0
        self.last_animation_update = 0
        self.animation_interval = 0.2  # 5 FPS for animations
        
        # Real-time stats
        self.current_stats = {
            'peak_cpu': 0.0,
            'peak_memory': 0.0,
            'total_sessions_today': 0,
            'avg_productivity_1h': 0.0,
            'trend_direction': 'stable'  # up, down, stable
        }
        
    def add_metrics(self, metrics: RealTimeMetrics):
        """Add new metrics to real-time tracking"""
        self.metrics_history.append(metrics)
        
        # Update live charts
        self.charts['cpu'].data_points.append(metrics.cpu_usage)
        self.charts['memory'].data_points.append(metrics.memory_usage)
        self.charts['sessions'].data_points.append(metrics.active_sessions)
        self.charts['productivity'].data_points.append(metrics.productivity_score)
        self.charts['network'].data_points.append(metrics.network_activity)
        self.charts['alerts'].data_points.append(metrics.alert_count)
        
        # Update dynamic max values
        if len(self.charts['memory'].data_points) > 10:
            recent_memory = list(self.charts['memory'].data_points)[-10:]
            self.charts['memory'].max_value = max(max(recent_memory) * 1.2, 100)
        
        # Update current stats
        self._update_current_stats()
        
    def _update_current_stats(self):
        """Update current statistics from recent data"""
        if not self.metrics_history:
            return
            
        recent_metrics = list(self.metrics_history)
        
        # Peak values
        self.current_stats['peak_cpu'] = max(m.cpu_usage for m in recent_metrics)
        self.current_stats['peak_memory'] = max(m.memory_usage for m in recent_metrics)
        
        # Productivity trend (last 10 vs previous 10)
        if len(recent_metrics) >= 20:
            recent_10 = recent_metrics[-10:]
            previous_10 = recent_metrics[-20:-10]
            
            recent_avg = sum(m.productivity_score for m in recent_10) / len(recent_10)
            previous_avg = sum(m.productivity_score for m in previous_10) / len(previous_10)
            
            self.current_stats['avg_productivity_1h'] = recent_avg
            
            if recent_avg > previous_avg + 5:
                self.current_stats['trend_direction'] = 'up'
            elif recent_avg < previous_avg - 5:
                self.current_stats['trend_direction'] = 'down'
            else:
                self.current_stats['trend_direction'] = 'stable'
    
    def should_update(self) -> bool:
        """Check if dashboard should update"""
        current_time = time.time()
        if current_time - self.last_update >= self.update_interval:
            self.last_update = current_time
            return True
        return False
    
    def should_animate(self) -> bool:
        """Check if animation frame should update"""
        current_time = time.time()
        if current_time - self.last_animation_update >= self.animation_interval:
            self.last_animation_update = current_time
            self.animation_frame = (self.animation_frame + 1) % 4
            return True
        return False
    
    def create_live_chart(self, chart: LiveChart, width: int = 50, height: int = 8) -> List[str]:
        """Create ASCII chart with live data"""
        if not chart.data_points:
            return [" " * width for _ in range(height)]
        
        # Normalize data to chart height
        data = list(chart.data_points)
        if len(data) > width:
            # Sample data to fit width
            step = len(data) / width
            data = [data[int(i * step)] for i in range(width)]
        
        # Pad with zeros if needed
        while len(data) < width:
            data.insert(0, 0)
        
        # Calculate scale
        max_val = max(data) if data else chart.max_value
        min_val = min(data) if data else chart.min_value
        range_val = max_val - min_val if max_val > min_val else 1
        
        # Create chart
        lines = []
        for row in range(height - 1, -1, -1):
            line = ""
            threshold = min_val + (row / (height - 1)) * range_val
            
            for i, value in enumerate(data):
                if value >= threshold:
                    # Color based on value
                    if value >= chart.color_threshold_high:
                        char = "█"  # High value
                    elif value >= chart.color_threshold_medium:
                        char = "▓"  # Medium value
                    else:
                        char = "▒"  # Low value
                else:
                    char = " "
                line += char
            lines.append(line)
        
        return lines
    
    def create_progress_bar(self, value: float, max_value: float, width: int = 20, 
                           style: str = "standard") -> Tuple[str, int]:
        """Create a progress bar with color coding"""
        if max_value == 0:
            percentage = 0
        else:
            percentage = min(100, (value / max_value) * 100)
        
        filled = int((percentage / 100) * width)
        
        if style == "standard":
            bar = "█" * filled + "░" * (width - filled)
        elif style == "smooth":
            # Use different Unicode blocks for smoother appearance
            full_blocks = filled
            partial = (percentage / 100 * width) - full_blocks
            
            bar = "█" * full_blocks
            if partial > 0.75 and full_blocks < width:
                bar += "▉"
                full_blocks += 1
            elif partial > 0.5 and full_blocks < width:
                bar += "▊"
                full_blocks += 1
            elif partial > 0.25 and full_blocks < width:
                bar += "▋"
                full_blocks += 1
            elif partial > 0 and full_blocks < width:
                bar += "▌"
                full_blocks += 1
            
            bar += "░" * (width - full_blocks)
        
        # Determine color based on percentage
        if percentage >= 80:
            color = 3  # Red
        elif percentage >= 60:
            color = 2  # Yellow
        else:
            color = 1  # Green
            
        return bar, color
    
    def create_sparkline(self, data: List[float], width: int = 20) -> str:
        """Create a sparkline chart"""
        if not data or len(data) < 2:
            return "─" * width
        
        # Sample data to fit width
        if len(data) > width:
            step = len(data) / width
            sampled_data = [data[int(i * step)] for i in range(width)]
        else:
            sampled_data = data + [data[-1]] * (width - len(data))
        
        # Normalize to sparkline characters
        min_val = min(sampled_data)
        max_val = max(sampled_data)
        range_val = max_val - min_val if max_val > min_val else 1
        
        sparkline_chars = "▁▂▃▄▅▆▇█"
        sparkline = ""
        
        for value in sampled_data:
            normalized = (value - min_val) / range_val
            char_index = int(normalized * (len(sparkline_chars) - 1))
            sparkline += sparkline_chars[char_index]
        
        return sparkline
    
    def get_animation_char(self, base_chars: List[str]) -> str:
        """Get current animation character"""
        return base_chars[self.animation_frame % len(base_chars)]
    
    def render_realtime_overview(self, stdscr, width: int, height: int):
        """Render real-time overview dashboard"""
        # Header with animation
        spinner = self.get_animation_char(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧"])
        title = f"{spinner} Real-Time Dashboard - Live Updates"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        y = 2
        
        # Current time
        current_time = datetime.now().strftime("%H:%M:%S")
        stdscr.addstr(y, width - 15, f"Time: {current_time}")
        
        # Real-time metrics section
        if self.metrics_history:
            latest = self.metrics_history[-1]
            
            y += 2
            stdscr.addstr(y, 2, "Live Metrics", curses.A_BOLD | curses.A_UNDERLINE)
            y += 2
            
            # CPU with progress bar
            cpu_bar, cpu_color = self.create_progress_bar(latest.cpu_usage, 100, 30)
            stdscr.addstr(y, 4, f"CPU: {latest.cpu_usage:5.1f}% ")
            stdscr.addstr(y, 18, f"[{cpu_bar}]", curses.color_pair(cpu_color))
            y += 1
            
            # Memory with progress bar  
            mem_bar, mem_color = self.create_progress_bar(latest.memory_usage, 
                                                         self.charts['memory'].max_value, 30)
            stdscr.addstr(y, 4, f"Memory: {latest.memory_usage:5.0f}MB ")
            stdscr.addstr(y, 18, f"[{mem_bar}]", curses.color_pair(mem_color))
            y += 1
            
            # Sessions
            stdscr.addstr(y, 4, f"Sessions: {latest.active_sessions}")
            y += 1
            
            # Productivity with trend indicator
            trend_char = "↗" if self.current_stats['trend_direction'] == 'up' else \
                        "↘" if self.current_stats['trend_direction'] == 'down' else "→"
            prod_bar, prod_color = self.create_progress_bar(latest.productivity_score, 100, 30)
            stdscr.addstr(y, 4, f"Productivity: {latest.productivity_score:5.1f}% {trend_char} ")
            stdscr.addstr(y, 25, f"[{prod_bar}]", curses.color_pair(prod_color))
            
        # Live charts section
        if height > 20:  # Only show if enough space
            y += 3
            stdscr.addstr(y, 2, "Live Charts (Last 60 updates)", curses.A_BOLD | curses.A_UNDERLINE)
            y += 2
            
            # CPU chart
            if 'cpu' in self.charts:
                cpu_chart = self.create_live_chart(self.charts['cpu'], width - 20, 6)
                stdscr.addstr(y, 4, "CPU Usage:")
                for i, line in enumerate(cpu_chart):
                    if y + i + 1 < height - 5:
                        stdscr.addstr(y + i + 1, 6, line)
                y += len(cpu_chart) + 2
        
        # Statistics section
        y = height - 8 if height > 15 else y + 3
        stdscr.addstr(y, 2, "Session Statistics", curses.A_BOLD | curses.A_UNDERLINE)
        y += 2
        
        stdscr.addstr(y, 4, f"Peak CPU: {self.current_stats['peak_cpu']:.1f}%")
        y += 1
        stdscr.addstr(y, 4, f"Peak Memory: {self.current_stats['peak_memory']:.0f}MB") 
        y += 1
        
        # Sparklines for recent trends
        if len(self.charts['cpu'].data_points) > 5:
            cpu_sparkline = self.create_sparkline(list(self.charts['cpu'].data_points)[-20:], 20)
            stdscr.addstr(y, 4, f"CPU Trend: {cpu_sparkline}")
            y += 1
            
            prod_sparkline = self.create_sparkline(list(self.charts['productivity'].data_points)[-20:], 20)
            stdscr.addstr(y, 4, f"Prod Trend: {prod_sparkline}")
        
        # Controls
        controls = "Q:exit | Space:pause | R:reset | T:toggle view"
        stdscr.addstr(height - 1, 2, controls[:width-4])
    
    def render_live_charts_view(self, stdscr, width: int, height: int):
        """Render detailed live charts view"""
        title = "📊 Live Charts - Real-Time Analytics"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        y = 2
        chart_height = (height - 8) // 2
        chart_width = width - 10
        
        # CPU Chart
        stdscr.addstr(y, 2, "CPU Usage (%)", curses.A_BOLD)
        cpu_chart = self.create_live_chart(self.charts['cpu'], chart_width, chart_height)
        for i, line in enumerate(cpu_chart):
            if y + i + 1 < height // 2:
                stdscr.addstr(y + i + 1, 4, line)
        
        # Add scale
        max_cpu = max(self.charts['cpu'].data_points) if self.charts['cpu'].data_points else 100
        stdscr.addstr(y + 1, chart_width + 6, f"{max_cpu:.1f}")
        stdscr.addstr(y + chart_height, chart_width + 6, "0.0")
        
        # Productivity Chart
        y += chart_height + 3
        stdscr.addstr(y, 2, "Productivity Score (%)", curses.A_BOLD)
        prod_chart = self.create_live_chart(self.charts['productivity'], chart_width, chart_height)
        for i, line in enumerate(prod_chart):
            if y + i + 1 < height - 3:
                stdscr.addstr(y + i + 1, 4, line)
        
        # Add scale
        stdscr.addstr(y + 1, chart_width + 6, "100")
        stdscr.addstr(y + chart_height, chart_width + 6, "0")
        
        # Controls
        controls = "Q:exit | O:overview | Space:pause updates"
        stdscr.addstr(height - 1, 2, controls[:width-4])

def test_realtime_dashboard():
    """Test real-time dashboard functionality"""
    print("Testing Real-Time Dashboard")
    print("=" * 40)
    
    dashboard = RealTimeDashboard()
    
    # Add some test metrics
    import random
    for i in range(20):
        metrics = RealTimeMetrics(
            timestamp=datetime.now(),
            cpu_usage=random.uniform(10, 90),
            memory_usage=random.uniform(100, 800),
            active_sessions=random.randint(1, 10),
            network_activity=random.uniform(0, 500),
            productivity_score=random.uniform(20, 90),
            alert_count=random.randint(0, 3)
        )
        dashboard.add_metrics(metrics)
    
    print(f"Added {len(dashboard.metrics_history)} metrics")
    print(f"CPU chart has {len(dashboard.charts['cpu'].data_points)} data points")
    
    # Test chart creation
    cpu_chart = dashboard.create_live_chart(dashboard.charts['cpu'], 40, 6)
    print(f"Generated CPU chart with {len(cpu_chart)} lines")
    
    # Test progress bar
    bar, color = dashboard.create_progress_bar(75, 100, 20)
    print(f"Progress bar: [{bar}] (color: {color})")
    
    # Test sparkline
    data = [10, 20, 15, 30, 25, 40, 35, 50]
    sparkline = dashboard.create_sparkline(data, 20)
    print(f"Sparkline: {sparkline}")
    
    print("Real-time dashboard test completed!")

if __name__ == "__main__":
    test_realtime_dashboard()