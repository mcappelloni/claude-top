#!/usr/bin/env python3
"""Test I/O counter capabilities on this system"""

import psutil
import os
import sys

def test_io_capabilities():
    """Test what I/O monitoring capabilities are available"""
    
    print("Testing I/O Capabilities on Current System")
    print("=" * 50)
    
    # Test current process first
    current_pid = os.getpid()
    print(f"Testing current process (PID: {current_pid})")
    
    try:
        proc = psutil.Process(current_pid)
        
        # Test network I/O
        print("\n1. Network I/O Testing:")
        try:
            net_io = proc.net_io_counters()
            if net_io:
                print(f"   ✓ Network I/O available")
                print(f"     Bytes sent: {net_io.bytes_sent}")
                print(f"     Bytes recv: {net_io.bytes_recv}")
            else:
                print("   ✗ Network I/O returned None")
        except AttributeError:
            print("   ✗ net_io_counters() not available")
        except psutil.AccessDenied:
            print("   ✗ Access denied for network I/O")
        except Exception as e:
            print(f"   ✗ Network I/O error: {e}")
        
        # Test disk I/O  
        print("\n2. Disk I/O Testing:")
        try:
            disk_io = proc.io_counters()
            if disk_io:
                print(f"   ✓ Disk I/O available")
                print(f"     Read bytes: {disk_io.read_bytes}")
                print(f"     Write bytes: {disk_io.write_bytes}")
                print(f"     Read count: {disk_io.read_count}")
                print(f"     Write count: {disk_io.write_count}")
            else:
                print("   ✗ Disk I/O returned None")
        except AttributeError:
            print("   ✗ io_counters() not available")
        except psutil.AccessDenied:
            print("   ✗ Access denied for disk I/O")
        except Exception as e:
            print(f"   ✗ Disk I/O error: {e}")
        
        # Test connections
        print("\n3. Connection Testing:")
        try:
            connections = proc.net_connections()
            print(f"   ✓ Connections available: {len(connections)} connections")
            for i, conn in enumerate(connections[:3]):  # Show first 3
                print(f"     {i+1}. {conn.laddr} -> {conn.raddr} ({conn.status})")
        except psutil.AccessDenied:
            print("   ✗ Access denied for connections")
        except Exception as e:
            print(f"   ✗ Connections error: {e}")
        
        # Test file descriptors (alternative approach)
        print("\n4. File Descriptor Testing:")
        try:
            open_files = proc.open_files()
            print(f"   ✓ Open files available: {len(open_files)} files")
            for i, file in enumerate(open_files[:3]):  # Show first 3
                print(f"     {i+1}. {file.path} (fd: {file.fd})")
        except psutil.AccessDenied:
            print("   ✗ Access denied for file descriptors")
        except Exception as e:
            print(f"   ✗ File descriptors error: {e}")
            
    except Exception as e:
        print(f"Error testing current process: {e}")
    
    # Test Claude processes
    print(f"\n" + "=" * 50)
    print("Testing Claude Processes:")
    
    claude_found = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline', [])
            if cmdline and any('claude' in cmd.lower() for cmd in cmdline):
                cmdline_str = ' '.join(cmdline)
                if 'Claude.app' not in cmdline_str and 'Claude Helper' not in cmdline_str:
                    claude_found = True
                    pid = proc.info['pid']
                    print(f"\nClaude Process PID: {pid}")
                    
                    # Test I/O on Claude process
                    claude_proc = psutil.Process(pid)
                    
                    try:
                        net_io = claude_proc.net_io_counters()
                        print(f"  Network I/O: {net_io}")
                    except Exception as e:
                        print(f"  Network I/O failed: {e}")
                    
                    try:
                        disk_io = claude_proc.io_counters()
                        print(f"  Disk I/O: {disk_io}")
                    except Exception as e:
                        print(f"  Disk I/O failed: {e}")
                    
                    try:
                        open_files = claude_proc.open_files()
                        print(f"  Open files: {len(open_files)}")
                    except Exception as e:
                        print(f"  Open files failed: {e}")
                        
                    break  # Test just one Claude process
        except Exception:
            continue
    
    if not claude_found:
        print("No Claude processes found for testing")
    
    # System capabilities
    print(f"\n" + "=" * 50)
    print("System Information:")
    print(f"Platform: {sys.platform}")
    print(f"Python version: {sys.version}")
    print(f"psutil version: {psutil.__version__}")
    print(f"Running as root: {os.geteuid() == 0 if hasattr(os, 'geteuid') else 'N/A'}")

if __name__ == "__main__":
    test_io_capabilities()