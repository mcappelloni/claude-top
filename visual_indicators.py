#!/usr/bin/env python3
"""Enhanced visual indicators for Claude Top"""

import curses
import math
from typing import Tuple, List, Dict, Optional
from enum import Enum

class IndicatorStyle(Enum):
    """Different styles for visual indicators"""
    BASIC = "basic"
    GRADIENT = "gradient"
    ANIMATED = "animated"
    MODERN = "modern"

class StatusIcon(Enum):
    """Status icons for different states"""
    RUNNING = "🟢"
    WAITING = "🟡"
    IDLE = "⚪"
    PAUSED = "🔴"
    ERROR = "❌"
    WARNING = "⚠️"
    SUCCESS = "✅"
    INFO = "ℹ️"

class VisualIndicators:
    def __init__(self):
        self.animation_frame = 0
        self.gradient_chars = {
            'solid': ['█', '▉', '▊', '▋', '▌', '▍', '▎', '▏'],
            'blocks': ['█', '▓', '▒', '░'],
            'dots': ['●', '◐', '◑', '◒', '◓', '○'],
            'bars': ['█', '▇', '▆', '▅', '▄', '▃', '▂', '▁']
        }
        
        # Color thresholds
        self.cpu_thresholds = {'high': 80, 'medium': 50, 'low': 20}
        self.memory_thresholds = {'high': 1000, 'medium': 500, 'low': 100}  # MB
        self.network_thresholds = {'high': 1000, 'medium': 100, 'low': 10}  # KB/s
    
    def setup_enhanced_colors(self):
        """Setup enhanced color pairs for better visual indicators"""
        # Existing color pairs (1-5) are already defined
        # Add new enhanced color pairs
        try:
            # Status indicator colors
            curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Running - bright green
            curses.init_pair(7, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Waiting - yellow
            curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Idle - white
            curses.init_pair(9, curses.COLOR_RED, curses.COLOR_BLACK)     # Paused/Error - red
            
            # Progress bar colors
            curses.init_pair(10, curses.COLOR_GREEN, curses.COLOR_GREEN)   # Low usage - green fill
            curses.init_pair(11, curses.COLOR_YELLOW, curses.COLOR_YELLOW) # Medium usage - yellow fill
            curses.init_pair(12, curses.COLOR_RED, curses.COLOR_RED)       # High usage - red fill
            
            # Background colors for progress bars
            curses.init_pair(13, curses.COLOR_BLACK, curses.COLOR_BLACK)   # Empty background
            curses.init_pair(14, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Text on dark
            
            # Alert colors
            curses.init_pair(15, curses.COLOR_RED, curses.COLOR_YELLOW)    # Critical alert
            curses.init_pair(16, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # Warning alert
            
        except curses.error:
            # Some terminals might not support all colors
            pass
    
    def get_status_color(self, status: str) -> int:
        """Get color pair for process status"""
        color_map = {
            'running': 6,   # Bright green
            'waiting': 7,   # Yellow
            'idle': 8,      # White
            'paused': 9,    # Red
            'error': 9      # Red
        }
        return color_map.get(status.lower(), 8)  # Default to white
    
    def get_status_icon(self, status: str) -> str:
        """Get Unicode icon for process status"""
        icon_map = {
            'running': '●',   # Solid dot
            'waiting': '◐',   # Half-filled dot
            'idle': '○',      # Empty dot
            'paused': '■',    # Square
            'error': '✗'     # X mark
        }
        return icon_map.get(status.lower(), '○')
    
    def create_enhanced_progress_bar(self, value: float, max_value: float, width: int = 20, 
                                   style: IndicatorStyle = IndicatorStyle.MODERN) -> Tuple[str, int, str]:
        """Create an enhanced progress bar with colors and styles"""
        if max_value == 0:
            percentage = 0
        else:
            percentage = min(100, max((value / max_value) * 100, 0))
        
        # Determine color based on percentage
        if percentage >= 80:
            color = 12  # Red
            level = "high"
        elif percentage >= 50:
            color = 11  # Yellow
            level = "medium"
        else:
            color = 10  # Green
            level = "low"
        
        if style == IndicatorStyle.BASIC:
            filled = int((percentage / 100) * width)
            bar = "█" * filled + "░" * (width - filled)
            
        elif style == IndicatorStyle.GRADIENT:
            filled = int((percentage / 100) * width)
            remainder = ((percentage / 100) * width) - filled
            
            bar = "█" * filled
            if remainder > 0 and filled < width:
                # Add partial character
                partial_chars = self.gradient_chars['solid']
                partial_index = int(remainder * len(partial_chars))
                if partial_index < len(partial_chars):
                    bar += partial_chars[partial_index]
                    filled += 1
            bar += "░" * (width - filled)
            
        elif style == IndicatorStyle.MODERN:
            filled = int((percentage / 100) * width)
            bar = ""
            
            # Use different characters for different levels
            if level == "high":
                fill_char = "▰"
                empty_char = "▱"
            elif level == "medium":
                fill_char = "▰"
                empty_char = "▱"
            else:
                fill_char = "▰"
                empty_char = "▱"
            
            bar = fill_char * filled + empty_char * (width - filled)
            
        elif style == IndicatorStyle.ANIMATED:
            # Animated progress bar with moving elements
            filled = int((percentage / 100) * width)
            
            if percentage > 0:
                # Add animation to the leading edge
                anim_chars = ['▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']
                anim_char = anim_chars[self.animation_frame % len(anim_chars)]
                
                if filled > 0:
                    bar = "█" * (filled - 1) + anim_char + "░" * (width - filled)
                else:
                    bar = anim_char + "░" * (width - 1)
            else:
                bar = "░" * width
        
        # Add percentage text
        percentage_text = f"{percentage:5.1f}%"
        
        return bar, color, percentage_text
    
    def create_sparkline_indicator(self, values: List[float], width: int = 15, 
                                 style: str = "standard") -> Tuple[str, int]:
        """Create a sparkline indicator showing recent trends"""
        if not values or len(values) < 2:
            return "─" * width, 8
        
        # Sample values to fit width
        if len(values) > width:
            step = len(values) / width
            sampled = [values[int(i * step)] for i in range(width)]
        else:
            sampled = values + [values[-1]] * (width - len(values))
        
        # Determine trend direction
        recent_avg = sum(sampled[-3:]) / 3 if len(sampled) >= 3 else sampled[-1]
        earlier_avg = sum(sampled[:3]) / 3 if len(sampled) >= 3 else sampled[0]
        
        if recent_avg > earlier_avg * 1.1:
            trend_color = 6  # Green (trending up)
        elif recent_avg < earlier_avg * 0.9:
            trend_color = 9  # Red (trending down)
        else:
            trend_color = 8  # White (stable)
        
        if style == "standard":
            # Standard sparkline
            min_val = min(sampled)
            max_val = max(sampled)
            range_val = max_val - min_val if max_val > min_val else 1
            
            chars = "▁▂▃▄▅▆▇█"
            sparkline = ""
            
            for value in sampled:
                normalized = (value - min_val) / range_val
                char_index = int(normalized * (len(chars) - 1))
                sparkline += chars[char_index]
                
        elif style == "smooth":
            # Smooth sparkline with more characters
            min_val = min(sampled)
            max_val = max(sampled)
            range_val = max_val - min_val if max_val > min_val else 1
            
            chars = " ▁▂▃▄▅▆▇█"
            sparkline = ""
            
            for i, value in enumerate(sampled):
                normalized = (value - min_val) / range_val
                char_index = int(normalized * (len(chars) - 1))
                sparkline += chars[char_index]
                
        elif style == "dots":
            # Dot-based sparkline
            min_val = min(sampled)
            max_val = max(sampled)
            range_val = max_val - min_val if max_val > min_val else 1
            
            chars = "⠀⠄⠆⠇⡇⡗⡟⡿⣿"
            sparkline = ""
            
            for value in sampled:
                normalized = (value - min_val) / range_val
                char_index = int(normalized * (len(chars) - 1))
                sparkline += chars[char_index]
        
        return sparkline, trend_color
    
    def create_gauge_indicator(self, value: float, max_value: float, width: int = 10) -> Tuple[str, int]:
        """Create a gauge-style indicator"""
        if max_value == 0:
            percentage = 0
        else:
            percentage = min(100, (value / max_value) * 100)
        
        # Create semicircle gauge using Unicode
        segments = width
        filled_segments = int((percentage / 100) * segments)
        
        gauge_chars = ['◔', '◑', '◕', '●']
        gauge = ""
        
        for i in range(segments):
            if i < filled_segments:
                gauge += gauge_chars[3]  # Filled
            elif i == filled_segments and percentage % (100/segments) > 0:
                # Partial fill
                partial = int((percentage % (100/segments)) / (100/segments) * len(gauge_chars))
                gauge += gauge_chars[min(partial, len(gauge_chars)-1)]
            else:
                gauge += gauge_chars[0]  # Empty
        
        # Color based on percentage
        if percentage >= 80:
            color = 9  # Red
        elif percentage >= 50:
            color = 7  # Yellow
        else:
            color = 6  # Green
        
        return gauge, color
    
    def create_status_badge(self, status: str, count: Optional[int] = None) -> Tuple[str, int]:
        """Create a status badge with icon and optional count"""
        icon = self.get_status_icon(status)
        color = self.get_status_color(status)
        
        if count is not None:
            badge = f"{icon} {count}"
        else:
            badge = f"{icon} {status.upper()}"
        
        return badge, color
    
    def create_alert_indicator(self, alert_level: str, message: str, width: int = 40) -> Tuple[str, int]:
        """Create an alert indicator with animation"""
        alert_chars = {
            'critical': ['🚨', '⚠️'],
            'warning': ['⚠️', '⬨'],
            'info': ['ℹ️', '💡'],
            'success': ['✅', '🎉']
        }
        
        colors = {
            'critical': 15,  # Red on yellow
            'warning': 16,   # Black on yellow
            'info': 4,       # Cyan
            'success': 6     # Green
        }
        
        # Animate alert icon
        icons = alert_chars.get(alert_level, ['⚠️'])
        icon = icons[self.animation_frame % len(icons)]
        
        # Truncate message to fit
        max_msg_len = width - 3
        if len(message) > max_msg_len:
            message = message[:max_msg_len-3] + "..."
        
        alert_text = f"{icon} {message}"
        color = colors.get(alert_level, 8)
        
        return alert_text, color
    
    def create_trend_arrow(self, current: float, previous: float, threshold: float = 5.0) -> Tuple[str, int]:
        """Create a trend arrow indicator"""
        if previous == 0:
            return "→", 8  # Neutral
        
        change_percent = ((current - previous) / previous) * 100
        
        if change_percent > threshold:
            return "↗", 6  # Up arrow, green
        elif change_percent < -threshold:
            return "↘", 9  # Down arrow, red
        else:
            return "→", 8  # Right arrow, neutral
    
    def update_animation_frame(self):
        """Update animation frame for animated indicators"""
        self.animation_frame = (self.animation_frame + 1) % 8
    
    def format_bytes_with_indicator(self, bytes_value: int) -> Tuple[str, str]:
        """Format bytes with visual indicator"""
        if bytes_value == 0:
            return "0B", "○"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        value = float(bytes_value)
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
        
        # Activity indicator based on size
        if unit_index >= 3:  # GB or higher
            indicator = "●●●"
        elif unit_index >= 2:  # MB
            indicator = "●●○"
        elif unit_index >= 1:  # KB
            indicator = "●○○"
        else:  # Bytes
            indicator = "○○○"
        
        if unit_index == 0:
            formatted = f"{int(value)}{units[unit_index]}"
        else:
            formatted = f"{value:.1f}{units[unit_index]}"
        
        return formatted, indicator

def test_visual_indicators():
    """Test visual indicators functionality"""
    print("Testing Enhanced Visual Indicators")
    print("=" * 50)
    
    indicators = VisualIndicators()
    
    # Test progress bars
    print("\nProgress Bar Styles:")
    for style in IndicatorStyle:
        bar, color, pct = indicators.create_enhanced_progress_bar(75, 100, 20, style)
        print(f"{style.value:10}: [{bar}] {pct}")
    
    # Test sparklines
    print("\nSparklines:")
    test_data = [10, 15, 12, 20, 18, 25, 22, 30, 28, 35]
    for style in ["standard", "smooth", "dots"]:
        sparkline, color = indicators.create_sparkline_indicator(test_data, 15, style)
        print(f"{style:10}: {sparkline}")
    
    # Test status badges
    print("\nStatus Badges:")
    for status in ["running", "waiting", "idle", "paused"]:
        badge, color = indicators.create_status_badge(status, 5)
        print(f"{status:10}: {badge}")
    
    # Test gauges
    print("\nGauge Indicators:")
    for value in [25, 50, 75, 90]:
        gauge, color = indicators.create_gauge_indicator(value, 100, 8)
        print(f"{value:3}%:      {gauge}")
    
    # Test trend arrows
    print("\nTrend Arrows:")
    test_cases = [(50, 40), (50, 50), (50, 60)]
    for current, previous in test_cases:
        arrow, color = indicators.create_trend_arrow(current, previous)
        print(f"{previous} → {current}: {arrow}")
    
    # Test byte formatting
    print("\nByte Formatting:")
    test_bytes = [512, 1024, 1048576, 1073741824]
    for bytes_val in test_bytes:
        formatted, indicator = indicators.format_bytes_with_indicator(bytes_val)
        print(f"{bytes_val:>10} bytes: {formatted:>8} {indicator}")
    
    print("\nVisual indicators test completed!")

if __name__ == "__main__":
    test_visual_indicators()