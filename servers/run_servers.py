#!/usr/bin/env python3
"""
MCP Server Launcher
Runs all MCP servers concurrently from their respective directories.
"""

import subprocess
import sys
import signal
import os
from pathlib import Path
from typing import List

# Define all server directories
SERVERS = [
    "catalog-enricher",
    "forecasting",
    "pricing-strategy",
    "replenishment"
]

class ServerManager:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.base_dir = Path(__file__).parent
        
    def start_servers(self):
        """Start all MCP servers."""
        print("Starting MCP servers...")
        print("-" * 50)
        
        for server in SERVERS:
            server_dir = self.base_dir / server
            
            if not server_dir.exists():
                print(f"⚠️  Warning: {server} directory not found, skipping...")
                continue
            
            server_file = server_dir / "server.py"
            if not server_file.exists():
                print(f"⚠️  Warning: {server}/server.py not found, skipping...")
                continue
            
            try:
                # Start the server using uv run
                process = subprocess.Popen(
                    ["uv", "run", "server.py"],
                    cwd=server_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                self.processes.append(process)
                print(f"✓ Started {server} (PID: {process.pid})")
            except Exception as e:
                print(f"✗ Failed to start {server}: {e}")
        
        print("-" * 50)
        print(f"Running {len(self.processes)} servers. Press Ctrl+C to stop all.\n")
    
    def monitor_servers(self):
        """Monitor servers and display their output."""
        try:
            while True:
                for i, process in enumerate(self.processes):
                    # Check if process is still running
                    if process.poll() is not None:
                        print(f"\n⚠️  Server {SERVERS[i]} (PID: {process.pid}) has stopped")
                        stderr = process.stderr.read() if process.stderr else ""
                        if stderr:
                            print(f"Error output: {stderr}")
                
                # Small delay to prevent CPU spinning
                import time
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\nReceived shutdown signal...")
            self.stop_servers()
    
    def stop_servers(self):
        """Stop all running servers."""
        print("Stopping all servers...")
        
        for i, process in enumerate(self.processes):
            if process.poll() is None:  # Still running
                print(f"Stopping {SERVERS[i]} (PID: {process.pid})...")
                process.terminate()
                
                try:
                    process.wait(timeout=5)
                    print(f"✓ {SERVERS[i]} stopped")
                except subprocess.TimeoutExpired:
                    print(f"Force killing {SERVERS[i]}...")
                    process.kill()
                    process.wait()
        
        print("\nAll servers stopped.")

def main():
    """Main entry point."""
    manager = ServerManager()
    
    # Setup signal handlers for clean shutdown
    def signal_handler(sig, frame):
        manager.stop_servers()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start and monitor servers
    manager.start_servers()
    
    if not manager.processes:
        print("No servers were started. Exiting.")
        sys.exit(1)
    
    manager.monitor_servers()

if __name__ == "__main__":
    main()