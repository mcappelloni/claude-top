#!/usr/bin/env python3
"""Enhanced process management for Claude Top"""

import os
import signal
import psutil
import curses
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ProcessInfo:
    """Extended process information"""
    pid: int
    name: str
    nice: int
    status: str
    parent_pid: int
    children: List[int]
    cpu_percent: float
    memory_mb: float
    open_files: int
    connections: int
    is_zombie: bool
    is_orphaned: bool
    runtime: timedelta

class ProcessManager:
    def __init__(self):
        self.cleanup_enabled = True
        self.auto_cleanup_zombies = True
        self.auto_cleanup_orphans = False  # More dangerous, disabled by default
        self.last_cleanup = datetime.now()
        self.cleanup_interval = 300  # 5 minutes
        
    def get_process_info(self, pid: int) -> Optional[ProcessInfo]:
        """Get detailed process information"""
        try:
            proc = psutil.Process(pid)
            
            # Get process details
            name = proc.name()
            nice = proc.nice()
            status = proc.status()
            create_time = datetime.fromtimestamp(proc.create_time())
            runtime = datetime.now() - create_time
            
            # Get parent and children
            parent_pid = proc.ppid()
            children = [child.pid for child in proc.children()]
            
            # Get resource usage
            cpu_percent = proc.cpu_percent()
            memory_mb = proc.memory_info().rss / 1024 / 1024
            
            # Get file handles and connections
            try:
                open_files = len(proc.open_files())
            except psutil.AccessDenied:
                open_files = 0
            
            try:
                connections = len(proc.net_connections())
            except psutil.AccessDenied:
                connections = 0
            
            # Check for problematic states
            is_zombie = status == 'zombie'
            is_orphaned = parent_pid == 1 and pid != 1  # Parent is init
            
            return ProcessInfo(
                pid=pid,
                name=name,
                nice=nice,
                status=status,
                parent_pid=parent_pid,
                children=children,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                open_files=open_files,
                connections=connections,
                is_zombie=is_zombie,
                is_orphaned=is_orphaned,
                runtime=runtime
            )
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    def adjust_process_priority(self, pid: int, nice_value: int) -> Tuple[bool, str]:
        """Adjust process priority (nice value)"""
        try:
            proc = psutil.Process(pid)
            old_nice = proc.nice()
            proc.nice(nice_value)
            return True, f"Priority changed from {old_nice} to {nice_value}"
        except psutil.NoSuchProcess:
            return False, f"Process {pid} no longer exists"
        except psutil.AccessDenied:
            return False, f"Access denied - cannot change priority for process {pid}"
        except Exception as e:
            return False, f"Error changing priority: {str(e)}"
    
    def find_zombie_processes(self) -> List[int]:
        """Find all zombie processes"""
        zombies = []
        for proc in psutil.process_iter(['pid', 'status']):
            try:
                if proc.info['status'] == 'zombie':
                    zombies.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return zombies
    
    def find_orphaned_claude_processes(self) -> List[int]:
        """Find orphaned Claude processes (parent is init)"""
        orphans = []
        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'cmdline']):
            try:
                # Check if this is a Claude process
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('claude' in cmd.lower() for cmd in cmdline):
                    # Check if orphaned (parent is init/1)
                    if proc.info['ppid'] == 1 and proc.info['pid'] != 1:
                        orphans.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return orphans
    
    def cleanup_zombie_processes(self) -> List[Tuple[int, bool, str]]:
        """Attempt to clean up zombie processes"""
        results = []
        zombies = self.find_zombie_processes()
        
        for pid in zombies:
            try:
                # Try to get parent process to handle the zombie
                proc = psutil.Process(pid)
                parent_pid = proc.ppid()
                
                if parent_pid > 1:  # Don't mess with init's children directly
                    try:
                        parent = psutil.Process(parent_pid)
                        # Send SIGCHLD to parent to trigger cleanup
                        parent.send_signal(signal.SIGCHLD)
                        results.append((pid, True, f"Sent SIGCHLD to parent {parent_pid}"))
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        results.append((pid, False, f"Cannot signal parent {parent_pid}"))
                else:
                    results.append((pid, False, "Zombie has init as parent"))
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                results.append((pid, False, "Process no longer accessible"))
        
        return results
    
    def cleanup_orphaned_processes(self, pids: List[int]) -> List[Tuple[int, bool, str]]:
        """Clean up specified orphaned processes"""
        results = []
        
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                
                # First try graceful termination
                proc.terminate()
                results.append((pid, True, "Terminated gracefully"))
                
            except psutil.NoSuchProcess:
                results.append((pid, True, "Process no longer exists"))
            except psutil.AccessDenied:
                results.append((pid, False, "Access denied"))
            except Exception as e:
                results.append((pid, False, f"Error: {str(e)}"))
        
        return results
    
    def get_process_tree(self, root_pid: int) -> Dict:
        """Get process tree starting from root_pid"""
        try:
            root = psutil.Process(root_pid)
            tree = {
                'pid': root_pid,
                'name': root.name(),
                'status': root.status(),
                'cpu': root.cpu_percent(),
                'memory': root.memory_info().rss / 1024 / 1024,
                'children': []
            }
            
            for child in root.children(recursive=False):
                tree['children'].append(self.get_process_tree(child.pid))
            
            return tree
            
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {'pid': root_pid, 'error': 'Process not accessible'}
    
    def auto_cleanup(self) -> Dict[str, List]:
        """Perform automatic cleanup if enabled and due"""
        results = {
            'zombies_cleaned': [],
            'orphans_found': [],
            'actions_taken': []
        }
        
        if not self.cleanup_enabled:
            return results
        
        now = datetime.now()
        if (now - self.last_cleanup).total_seconds() < self.cleanup_interval:
            return results
        
        self.last_cleanup = now
        
        # Clean up zombies if enabled
        if self.auto_cleanup_zombies:
            zombie_results = self.cleanup_zombie_processes()
            results['zombies_cleaned'] = zombie_results
            if zombie_results:
                results['actions_taken'].append(f"Cleaned {len(zombie_results)} zombies")
        
        # Find orphans (but don't auto-clean unless specifically enabled)
        orphans = self.find_orphaned_claude_processes()
        results['orphans_found'] = orphans
        
        if self.auto_cleanup_orphans and orphans:
            orphan_results = self.cleanup_orphaned_processes(orphans)
            results['actions_taken'].append(f"Cleaned {len(orphan_results)} orphans")
        
        return results
    
    def show_priority_dialog(self, stdscr, current_pid: int, current_nice: int) -> Optional[int]:
        """Show dialog to adjust process priority"""
        height, width = stdscr.getmaxyx()
        
        dialog_text = [
            "Adjust Process Priority",
            "",
            f"Process PID: {current_pid}",
            f"Current Nice: {current_nice}",
            "",
            "Nice values range from -20 (highest priority) to 19 (lowest priority)",
            "Lower values = higher priority",
            "Note: Lowering nice value may require sudo privileges",
            "",
            "Enter new nice value (-20 to 19):",
            "",
            "ESC to cancel"
        ]
        
        # Calculate dialog dimensions
        box_height = len(dialog_text) + 4
        box_width = max(len(line) for line in dialog_text) + 6
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        # Draw dialog
        stdscr.attron(curses.color_pair(4))
        for y in range(box_height):
            stdscr.addstr(start_y + y, start_x, " " * box_width)
        
        for i, line in enumerate(dialog_text):
            stdscr.addstr(start_y + i + 2, start_x + 3, line)
        stdscr.attroff(curses.color_pair(4))
        
        # Input field
        input_y = start_y + len(dialog_text) - 1
        input_x = start_x + 35
        
        stdscr.refresh()
        
        # Handle input
        nice_input = ""
        curses.curs_set(1)  # Show cursor
        
        try:
            while True:
                key = stdscr.getch()
                
                if key == 27:  # ESC
                    return None
                elif key == ord('\n'):  # Enter
                    try:
                        nice_value = int(nice_input)
                        if -20 <= nice_value <= 19:
                            return nice_value
                        else:
                            # Show error and continue
                            stdscr.addstr(input_y + 2, start_x + 3, "Value must be between -20 and 19")
                            stdscr.refresh()
                    except ValueError:
                        stdscr.addstr(input_y + 2, start_x + 3, "Please enter a valid number")
                        stdscr.refresh()
                elif key == curses.KEY_BACKSPACE or key == 127:
                    if nice_input:
                        nice_input = nice_input[:-1]
                        stdscr.addstr(input_y, input_x, "    ")  # Clear
                        stdscr.addstr(input_y, input_x, nice_input)
                        stdscr.refresh()
                elif key >= ord('0') and key <= ord('9') or key == ord('-'):
                    if len(nice_input) < 3:  # Limit input length
                        nice_input += chr(key)
                        stdscr.addstr(input_y, input_x, nice_input)
                        stdscr.refresh()
                        
        finally:
            curses.curs_set(0)  # Hide cursor
    
    def show_cleanup_dialog(self, stdscr) -> Optional[str]:
        """Show process cleanup options dialog"""
        height, width = stdscr.getmaxyx()
        
        # Get current problematic processes
        zombies = self.find_zombie_processes()
        orphans = self.find_orphaned_claude_processes()
        
        dialog_text = [
            "Process Cleanup Options",
            "",
            f"Found {len(zombies)} zombie processes",
            f"Found {len(orphans)} orphaned Claude processes",
            "",
            "Choose cleanup action:",
            "",
            "1. Clean up zombie processes",
            "2. Clean up orphaned Claude processes (careful!)",
            "3. Both zombie and orphaned processes",
            "4. Toggle auto-cleanup settings",
            "",
            "ESC to cancel"
        ]
        
        # Calculate dialog dimensions
        box_height = len(dialog_text) + 4
        box_width = max(len(line) for line in dialog_text) + 6
        start_y = (height - box_height) // 2
        start_x = (width - box_width) // 2
        
        # Draw dialog
        stdscr.attron(curses.color_pair(4))
        for y in range(box_height):
            stdscr.addstr(start_y + y, start_x, " " * box_width)
        
        for i, line in enumerate(dialog_text):
            stdscr.addstr(start_y + i + 2, start_x + 3, line)
        stdscr.attroff(curses.color_pair(4))
        
        stdscr.refresh()
        
        # Handle selection
        while True:
            key = stdscr.getch()
            
            if key == 27:  # ESC
                return None
            elif key == ord('1'):
                return "zombies"
            elif key == ord('2'):
                return "orphans"
            elif key == ord('3'):
                return "both"
            elif key == ord('4'):
                return "settings"

def test_process_management():
    """Test process management functionality"""
    print("Testing Process Management")
    print("=" * 40)
    
    manager = ProcessManager()
    
    # Test current process info
    current_pid = os.getpid()
    info = manager.get_process_info(current_pid)
    
    if info:
        print(f"Current process info:")
        print(f"  PID: {info.pid}")
        print(f"  Name: {info.name}")
        print(f"  Nice: {info.nice}")
        print(f"  Status: {info.status}")
        print(f"  Memory: {info.memory_mb:.1f}MB")
        print(f"  Runtime: {info.runtime}")
        print(f"  Children: {len(info.children)}")
        print(f"  Is zombie: {info.is_zombie}")
        print(f"  Is orphaned: {info.is_orphaned}")
    
    # Test finding problematic processes
    zombies = manager.find_zombie_processes()
    orphans = manager.find_orphaned_claude_processes()
    
    print(f"\nFound {len(zombies)} zombie processes")
    print(f"Found {len(orphans)} orphaned Claude processes")
    
    # Test auto cleanup (dry run)
    print("\nAuto cleanup results:")
    results = manager.auto_cleanup()
    for action in results.get('actions_taken', []):
        print(f"  {action}")
    
    print("Process management test completed!")

if __name__ == "__main__":
    test_process_management()