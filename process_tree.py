#!/usr/bin/env python3
"""Process tree discovery and tracking for Claude instances"""

import psutil
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class ProcessNode:
    pid: int
    parent_pid: Optional[int]
    name: str
    command: str
    cpu_percent: float
    memory_mb: float
    working_dir: str
    status: str
    depth: int = 0
    children: List['ProcessNode'] = field(default_factory=list)

class ProcessTreeTracker:
    def __init__(self):
        self.known_pids: Set[int] = set()
        self.pid_history: Dict[int, List[Dict]] = defaultdict(list)
    
    def discover_process_tree(self, root_pid: int, max_depth: int = 3) -> Optional[ProcessNode]:
        """Discover the complete process tree starting from a root PID"""
        try:
            root_proc = psutil.Process(root_pid)
            root_node = self.create_process_node(root_proc, 0)
            
            # Build the tree recursively
            self._build_tree(root_node, max_depth)
            
            return root_node
        except psutil.NoSuchProcess:
            return None
    
    def create_process_node(self, proc: psutil.Process, depth: int) -> ProcessNode:
        """Create a ProcessNode from a psutil.Process"""
        try:
            # Get process information
            info = proc.as_dict(['pid', 'ppid', 'name', 'cmdline', 'cwd', 'status'])
            
            # Memory and CPU
            memory_info = proc.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            cpu_percent = proc.cpu_percent()
            
            # Command line
            cmdline = info.get('cmdline', [])
            command = ' '.join(cmdline) if cmdline else info.get('name', 'unknown')
            
            # Working directory
            working_dir = info.get('cwd', 'Unknown')
            if not working_dir:
                try:
                    working_dir = proc.cwd()
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    working_dir = 'Unknown'
            
            return ProcessNode(
                pid=info['pid'],
                parent_pid=info.get('ppid'),
                name=info.get('name', 'unknown'),
                command=command,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                working_dir=working_dir,
                status=info.get('status', 'unknown'),
                depth=depth
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Return minimal node if access is denied
            return ProcessNode(
                pid=proc.pid,
                parent_pid=None,
                name='inaccessible',
                command='<access denied>',
                cpu_percent=0.0,
                memory_mb=0.0,
                working_dir='Unknown',
                status='unknown',
                depth=depth
            )
    
    def _build_tree(self, node: ProcessNode, max_depth: int):
        """Recursively build the process tree"""
        if node.depth >= max_depth:
            return
        
        try:
            proc = psutil.Process(node.pid)
            children = proc.children(recursive=False)
            
            for child_proc in children:
                try:
                    child_node = self.create_process_node(child_proc, node.depth + 1)
                    node.children.append(child_node)
                    
                    # Recursively build child trees
                    self._build_tree(child_node, max_depth)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    def find_related_processes(self, claude_pids: List[int]) -> Dict[int, ProcessNode]:
        """Find all processes related to Claude instances"""
        trees = {}
        
        for pid in claude_pids:
            tree = self.discover_process_tree(pid)
            if tree:
                trees[pid] = tree
        
        return trees
    
    def analyze_subprocess_activity(self, tree: ProcessNode) -> Dict[str, any]:
        """Analyze subprocess activity within a process tree"""
        analysis = {
            'total_processes': 0,
            'total_cpu': 0.0,
            'total_memory': 0.0,
            'subprocess_types': defaultdict(int),
            'active_subprocesses': [],
            'max_depth': 0
        }
        
        def analyze_node(node: ProcessNode):
            analysis['total_processes'] += 1
            analysis['total_cpu'] += node.cpu_percent
            analysis['total_memory'] += node.memory_mb
            analysis['max_depth'] = max(analysis['max_depth'], node.depth)
            
            # Categorize subprocess types
            if 'python' in node.name.lower():
                analysis['subprocess_types']['Python'] += 1
            elif 'node' in node.name.lower() or 'npm' in node.command.lower():
                analysis['subprocess_types']['Node.js'] += 1
            elif any(term in node.command.lower() for term in ['git', 'ssh', 'curl', 'wget']):
                analysis['subprocess_types']['System Tools'] += 1
            elif 'docker' in node.command.lower():
                analysis['subprocess_types']['Docker'] += 1
            else:
                analysis['subprocess_types']['Other'] += 1
            
            # Track active subprocesses (high CPU or memory)
            if node.cpu_percent > 1.0 or node.memory_mb > 10.0:
                analysis['active_subprocesses'].append({
                    'pid': node.pid,
                    'name': node.name,
                    'cpu': node.cpu_percent,
                    'memory': node.memory_mb,
                    'depth': node.depth
                })
            
            # Recursively analyze children
            for child in node.children:
                analyze_node(child)
        
        analyze_node(tree)
        return analysis
    
    def print_process_tree(self, tree: ProcessNode, show_details: bool = False):
        """Print a visual representation of the process tree"""
        def print_node(node: ProcessNode, prefix: str = "", is_last: bool = True):
            # Tree symbols
            current_prefix = "└── " if is_last else "├── "
            next_prefix = prefix + ("    " if is_last else "│   ")
            
            # Process info
            if show_details:
                info = f"{node.name} (PID: {node.pid}) - CPU: {node.cpu_percent:.1f}%, Mem: {node.memory_mb:.1f}MB"
            else:
                info = f"{node.name} (PID: {node.pid})"
            
            print(f"{prefix}{current_prefix}{info}")
            
            # Print command if not too long
            if show_details and len(node.command) > len(node.name):
                cmd = node.command[:60] + "..." if len(node.command) > 60 else node.command
                print(f"{next_prefix}└─ {cmd}")
            
            # Print children
            for i, child in enumerate(node.children):
                is_last_child = i == len(node.children) - 1
                print_node(child, next_prefix, is_last_child)
        
        print_node(tree)

def test_process_tree():
    """Test process tree discovery with Claude processes"""
    print("Testing Process Tree Discovery")
    print("=" * 50)
    
    tracker = ProcessTreeTracker()
    
    # Find Claude processes
    claude_pids = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any('claude' in cmd.lower() for cmd in cmdline):
                cmdline_str = ' '.join(cmdline)
                if 'Claude.app' not in cmdline_str and 'Claude Helper' not in cmdline_str:
                    claude_pids.append(proc.info['pid'])
        except:
            continue
    
    print(f"Found {len(claude_pids)} Claude processes: {claude_pids}")
    
    # Discover process trees
    trees = tracker.find_related_processes(claude_pids[:3])  # Limit to first 3 for testing
    
    for pid, tree in trees.items():
        print(f"\n" + "=" * 50)
        print(f"Process Tree for Claude PID {pid}:")
        print("=" * 50)
        
        tracker.print_process_tree(tree, show_details=True)
        
        # Analyze subprocess activity
        analysis = tracker.analyze_subprocess_activity(tree)
        print(f"\nTree Analysis:")
        print(f"  Total Processes: {analysis['total_processes']}")
        print(f"  Total CPU: {analysis['total_cpu']:.1f}%")
        print(f"  Total Memory: {analysis['total_memory']:.1f}MB")
        print(f"  Max Depth: {analysis['max_depth']}")
        print(f"  Subprocess Types: {dict(analysis['subprocess_types'])}")
        
        if analysis['active_subprocesses']:
            print(f"  Active Subprocesses:")
            for sub in analysis['active_subprocesses'][:5]:  # Show top 5
                print(f"    - {sub['name']} (PID: {sub['pid']}) - CPU: {sub['cpu']:.1f}%, Mem: {sub['memory']:.1f}MB")

if __name__ == "__main__":
    test_process_tree()