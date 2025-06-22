#!/usr/bin/env python3
"""Performance optimization for Claude Top continuous updates"""

import time
import threading
from typing import Dict, List, Optional, Callable
from collections import deque
from dataclasses import dataclass, field

@dataclass
class PerformanceMetrics:
    """Performance metrics tracking"""
    update_times: deque = field(default_factory=lambda: deque(maxlen=100))
    render_times: deque = field(default_factory=lambda: deque(maxlen=100))
    cpu_usage: deque = field(default_factory=lambda: deque(maxlen=50))
    memory_usage: deque = field(default_factory=lambda: deque(maxlen=50))
    frame_rate: float = 0.0
    last_update: float = 0.0

class PerformanceOptimizer:
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.adaptive_update_interval = 1.0
        self.min_update_interval = 0.1
        self.max_update_interval = 5.0
        self.target_frame_rate = 10.0  # FPS
        
        # Caching system
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = 2.0  # Cache TTL in seconds
        
        # Update throttling
        self.throttle_cpu_threshold = 80.0
        self.throttle_memory_threshold = 1000.0  # MB
        self.is_throttled = False
        
        # Selective updates
        self.update_priorities = {
            'critical': 0.1,   # Always update (alerts, errors)
            'high': 0.5,       # Update frequently (process list, status)
            'medium': 1.0,     # Update normally (resource usage)
            'low': 2.0,        # Update less frequently (statistics)
            'background': 5.0  # Update rarely (historical data)
        }
        
        # Background processing
        self.background_tasks = []
        self.background_thread = None
        self.background_running = False
        
    def start_background_processing(self):
        """Start background processing thread"""
        if self.background_thread is None or not self.background_thread.is_alive():
            self.background_running = True
            self.background_thread = threading.Thread(target=self._background_worker)
            self.background_thread.daemon = True
            self.background_thread.start()
    
    def stop_background_processing(self):
        """Stop background processing thread"""
        self.background_running = False
        if self.background_thread and self.background_thread.is_alive():
            self.background_thread.join(timeout=1.0)
    
    def _background_worker(self):
        """Background worker thread for non-critical tasks"""
        while self.background_running:
            try:
                # Process background tasks
                for task in self.background_tasks[:]:
                    if not self.background_running:
                        break
                    
                    try:
                        task()
                        self.background_tasks.remove(task)
                    except Exception as e:
                        # Remove failed tasks
                        if task in self.background_tasks:
                            self.background_tasks.remove(task)
                
                time.sleep(0.1)  # Small delay to prevent CPU spinning
                
            except Exception:
                # Continue on any error
                time.sleep(0.5)
    
    def add_background_task(self, task: Callable):
        """Add a task to be processed in background"""
        self.background_tasks.append(task)
    
    def measure_update_time(self, update_func: Callable) -> any:
        """Measure and track update time"""
        start_time = time.time()
        result = update_func()
        end_time = time.time()
        
        update_time = end_time - start_time
        self.metrics.update_times.append(update_time)
        
        # Calculate frame rate
        if self.metrics.last_update > 0:
            frame_interval = end_time - self.metrics.last_update
            if frame_interval > 0:
                self.metrics.frame_rate = 1.0 / frame_interval
        
        self.metrics.last_update = end_time
        
        # Adjust update interval based on performance
        self._adjust_update_interval()
        
        return result
    
    def measure_render_time(self, render_func: Callable) -> any:
        """Measure and track render time"""
        start_time = time.time()
        result = render_func()
        end_time = time.time()
        
        render_time = end_time - start_time
        self.metrics.render_times.append(render_time)
        
        return result
    
    def _adjust_update_interval(self):
        """Dynamically adjust update interval based on performance"""
        if len(self.metrics.update_times) < 5:
            return
        
        # Calculate average update time
        avg_update_time = sum(self.metrics.update_times) / len(self.metrics.update_times)
        
        # If updates are taking too long, increase interval
        if avg_update_time > 0.5:  # 500ms is too slow
            self.adaptive_update_interval = min(
                self.adaptive_update_interval * 1.2,
                self.max_update_interval
            )
        elif avg_update_time < 0.1:  # Under 100ms is good
            self.adaptive_update_interval = max(
                self.adaptive_update_interval * 0.9,
                self.min_update_interval
            )
    
    def should_update(self, priority: str = 'medium') -> bool:
        """Check if component should update based on priority and performance"""
        current_time = time.time()
        interval = self.update_priorities.get(priority, 1.0)
        
        # Apply adaptive interval for non-critical updates
        if priority not in ['critical']:
            interval = max(interval, self.adaptive_update_interval)
        
        # Apply throttling if system is under stress
        if self.is_throttled and priority in ['low', 'background']:
            interval *= 2.0
        
        cache_key = f"last_update_{priority}"
        last_update = self.cache_timestamps.get(cache_key, 0)
        
        if current_time - last_update >= interval:
            self.cache_timestamps[cache_key] = current_time
            return True
        
        return False
    
    def cache_get(self, key: str) -> any:
        """Get cached value if still valid"""
        current_time = time.time()
        
        if key in self.cache and key in self.cache_timestamps:
            if current_time - self.cache_timestamps[key] < self.cache_ttl:
                return self.cache[key]
        
        return None
    
    def cache_set(self, key: str, value: any):
        """Set cached value with timestamp"""
        self.cache[key] = value
        self.cache_timestamps[key] = time.time()
    
    def cache_clear(self, pattern: Optional[str] = None):
        """Clear cache entries matching pattern"""
        if pattern is None:
            self.cache.clear()
            self.cache_timestamps.clear()
        else:
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                self.cache.pop(key, None)
                self.cache_timestamps.pop(key, None)
    
    def update_system_metrics(self, cpu_percent: float, memory_mb: float):
        """Update system performance metrics"""
        self.metrics.cpu_usage.append(cpu_percent)
        self.metrics.memory_usage.append(memory_mb)
        
        # Determine if system is under stress
        recent_cpu = list(self.metrics.cpu_usage)[-5:] if self.metrics.cpu_usage else [0]
        recent_memory = list(self.metrics.memory_usage)[-5:] if self.metrics.memory_usage else [0]
        
        avg_cpu = sum(recent_cpu) / len(recent_cpu)
        avg_memory = sum(recent_memory) / len(recent_memory)
        
        # Enable throttling if system is under stress
        self.is_throttled = (
            avg_cpu > self.throttle_cpu_threshold or 
            avg_memory > self.throttle_memory_threshold
        )
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary statistics"""
        if not self.metrics.update_times:
            return {'status': 'no_data'}
        
        avg_update_time = sum(self.metrics.update_times) / len(self.metrics.update_times)
        avg_render_time = sum(self.metrics.render_times) / len(self.metrics.render_times) if self.metrics.render_times else 0
        
        return {
            'status': 'throttled' if self.is_throttled else 'normal',
            'frame_rate': self.metrics.frame_rate,
            'avg_update_time': avg_update_time * 1000,  # Convert to ms
            'avg_render_time': avg_render_time * 1000,   # Convert to ms
            'adaptive_interval': self.adaptive_update_interval,
            'cache_size': len(self.cache),
            'background_tasks': len(self.background_tasks)
        }
    
    def optimize_curses_refresh(self, stdscr, regions: List[tuple] = None):
        """Optimize curses screen refreshes by updating only changed regions"""
        if regions:
            # Partial refresh for specific regions
            for y, x, height, width in regions:
                try:
                    stdscr.refresh(y, x, y, x, y + height, x + width)
                except:
                    # Fall back to full refresh on error
                    stdscr.refresh()
                    break
        else:
            # Standard full refresh
            stdscr.refresh()
    
    def batch_screen_updates(self, update_functions: List[Callable]):
        """Batch multiple screen updates to reduce flicker"""
        # Collect all updates before applying
        updates = []
        for update_func in update_functions:
            try:
                updates.append(update_func)
            except Exception:
                continue
        
        # Apply all updates together
        for update in updates:
            try:
                update()
            except Exception:
                continue
    
    def reduce_update_frequency_on_idle(self, idle_time: float):
        """Reduce update frequency when system is idle"""
        if idle_time > 30:  # 30 seconds of idle
            self.adaptive_update_interval = min(
                self.adaptive_update_interval * 1.5,
                self.max_update_interval
            )
        elif idle_time < 5:  # Active again
            self.adaptive_update_interval = max(
                self.adaptive_update_interval * 0.8,
                self.min_update_interval
            )
    
    def memory_cleanup(self):
        """Perform memory cleanup to prevent memory leaks"""
        # Clear old cache entries
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items()
            if current_time - timestamp > self.cache_ttl * 2
        ]
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
        
        # Trim metrics to prevent unbounded growth
        if len(self.metrics.update_times) > 100:
            # Keep only the most recent entries
            self.metrics.update_times = deque(
                list(self.metrics.update_times)[-50:], maxlen=100
            )
        
        if len(self.metrics.render_times) > 100:
            self.metrics.render_times = deque(
                list(self.metrics.render_times)[-50:], maxlen=100
            )

def test_performance_optimizer():
    """Test performance optimization functionality"""
    print("Testing Performance Optimizer")
    print("=" * 40)
    
    optimizer = PerformanceOptimizer()
    
    # Test caching
    optimizer.cache_set("test_key", "test_value")
    cached_value = optimizer.cache_get("test_key")
    print(f"Cache test: {cached_value == 'test_value'}")
    
    # Test update timing
    def dummy_update():
        time.sleep(0.01)  # Simulate work
        return "updated"
    
    result = optimizer.measure_update_time(dummy_update)
    print(f"Update time measured: {len(optimizer.metrics.update_times)} samples")
    
    # Test system metrics
    optimizer.update_system_metrics(45.0, 512.0)
    print(f"System metrics updated: throttled={optimizer.is_throttled}")
    
    # Test priority-based updates
    should_update_critical = optimizer.should_update('critical')
    should_update_background = optimizer.should_update('background')
    print(f"Update priorities: critical={should_update_critical}, background={should_update_background}")
    
    # Test performance summary
    summary = optimizer.get_performance_summary()
    print(f"Performance summary: {summary['status']}, FPS: {summary['frame_rate']:.1f}")
    
    # Test background processing
    optimizer.start_background_processing()
    
    task_completed = False
    def test_task():
        nonlocal task_completed
        task_completed = True
    
    optimizer.add_background_task(test_task)
    time.sleep(0.2)  # Wait for background processing
    
    print(f"Background task completed: {task_completed}")
    
    optimizer.stop_background_processing()
    print("Performance optimizer test completed!")

if __name__ == "__main__":
    test_performance_optimizer()