#!/usr/bin/env python3
"""
RetailOps MCP Server Orchestrator/Launcher
Runs all four MCP servers (Catalog Enricher, Forecasting, Replenishment, Pricing Strategy)
concurrently with real-time log streaming, color-coded output, and graceful shutdown.
"""

import os
import sys
import shutil
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List

# Server configuration mapping folder names to display names and colors
SERVERS_CONFIG = {
    "catalog-enricher": {"name": "Catalog Enricher", "color": "\033[96m"},  # Cyan
    "forecasting": {"name": "Forecasting    ", "color": "\033[95m"},       # Magenta
    "replenishment": {"name": "Replenishment  ", "color": "\033[93m"},     # Yellow
    "pricing-strategy": {"name": "Pricing Strategy", "color": "\033[94m"},  # Blue
}

# ANSI Escape Codes for CLI styling
COLOR_RESET = "\033[0m"
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_BOLD = "\033[1m"
COLOR_DIM = "\033[2m"

def init_ansi():
    """Enable ANSI escape codes on Windows consoles if needed."""
    if sys.platform == "win32":
        try:
            # os.system('') enables virtual terminal processing on Windows 10+
            os.system("")
        except Exception:
            pass

def load_environment_variables(root_dir: Path):
    """Load variables from root .env manually if dotenv is not available."""
    # Try using python-dotenv first
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=root_dir / ".env")
        return
    except ImportError:
        pass

    # Fallback: manually parse .env
    env_path = root_dir / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        # Remove quotes if present
                        val = val.strip().strip("'\"")
                        os.environ[key.strip()] = val
        except Exception as e:
            print(f"⚠️  Note: Could not parse .env file: {e}")

class ServerManager:
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.threads: List[threading.Thread] = []
        
        # Directory adaptation (handles being run from root or from within /servers)
        current_dir = Path(__file__).parent.resolve()
        if current_dir.name == "servers":
            self.base_dir = current_dir
            self.root_dir = current_dir.parent
        else:
            self.base_dir = current_dir / "servers"
            self.root_dir = current_dir
            
        self.has_uv = shutil.which("uv") is not None
        self.shutting_down = False

    def get_python_command(self, server_dir: Path) -> List[str]:
        """Determine the best command to run the Python server."""
        # Option 1: Use uv if installed in system path
        if self.has_uv and (server_dir / "uv.lock").exists():
            return ["uv", "run", "server.py"]

        # Option 2: Use local virtual environment python executable
        if sys.platform == "win32":
            venv_python = server_dir / ".venv" / "Scripts" / "python.exe"
        else:
            venv_python = server_dir / ".venv" / "bin" / "python"

        if venv_python.exists():
            return [str(venv_python), "server.py"]

        # Option 3: Fall back to current executing Python
        return [sys.executable, "server.py"]

    def stream_logs(self, process: subprocess.Popen, prefix: str, color: str):
        """Read output from the subprocess line-by-line and print it."""
        try:
            # Read stdout and stderr (which are merged)
            for line in iter(process.stdout.readline, ""):
                if not line:
                    break
                if self.shutting_down:
                    break
                clean_line = line.rstrip("\r\n")
                print(f"{color}[{prefix}]{COLOR_RESET} {clean_line}", flush=True)
        except Exception as e:
            if not self.shutting_down:
                print(f"{COLOR_RED}[Launcher] Error reading logs for {prefix}: {e}{COLOR_RESET}")
        finally:
            try:
                process.stdout.close()
            except Exception:
                pass

    def start_servers(self):
        """Start all four MCP servers concurrently."""
        print(f"\n{COLOR_GREEN}{COLOR_BOLD}==================================================")
        print("         RetailOps MCP Server Orchestrator        ")
        print(f"=================================================={COLOR_RESET}\n")

        # Verify API Key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print(f"⚠️  {COLOR_RED}{COLOR_BOLD}WARNING: OPENROUTER_API_KEY is not set in your environment.{COLOR_RESET}")
            print(f"   Please check your .env file in the root directory.\n")
        else:
            masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
            print(f"🔑 {COLOR_GREEN}OpenRouter API Key found:{COLOR_RESET} {masked_key}")

        print(f"⚙️  {COLOR_DIM}Detection: uv package manager is {'available' if self.has_uv else 'NOT available (falling back to local venvs)'}{COLOR_RESET}\n")
        print("Starting servers...")
        print("-" * 50)

        started_count = 0

        for folder, config in SERVERS_CONFIG.items():
            server_dir = self.base_dir / folder
            display_name = config["name"]
            color = config["color"]

            if not server_dir.exists():
                print(f"⚠️  {COLOR_RED}Skipping {display_name}: Directory '{server_dir}' not found.{COLOR_RESET}")
                continue

            server_file = server_dir / "server.py"
            if not server_file.exists():
                print(f"⚠️  {COLOR_RED}Skipping {display_name}: 'server.py' not found in '{server_dir}'.{COLOR_RESET}")
                continue

            cmd = self.get_python_command(server_dir)
            cmd_str = " ".join(cmd)
            print(f"🚀 Starting {color}{display_name}{COLOR_RESET} using: {COLOR_DIM}{cmd_str}{COLOR_RESET}")

            try:
                # Spawn process with merged stdout/stderr and piped stdin to keep stdio active but isolated
                process = subprocess.Popen(
                    cmd,
                    cwd=server_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,  # Line buffered
                    env=os.environ.copy()
                )
                self.processes.append(process)

                # Store server details on the process object for tracking
                process.server_name = display_name
                process.folder = folder
                process.color = color

                # Start background log streaming thread
                log_thread = threading.Thread(
                    target=self.stream_logs,
                    args=(process, display_name.strip(), color),
                    daemon=True
                )
                log_thread.start()
                self.threads.append(log_thread)
                started_count += 1

            except Exception as e:
                print(f"❌ {COLOR_RED}Failed to start {display_name}: {e}{COLOR_RESET}")

        print("-" * 50)
        if started_count > 0:
            print(f"\n{COLOR_GREEN}✓ Successfully launched {started_count} servers.{COLOR_RESET}")
            print(f"🖥️  Streaming logs concurrently. {COLOR_BOLD}Press Ctrl+C to stop all servers.{COLOR_RESET}\n")
        else:
            print(f"\n❌ {COLOR_RED}No servers could be started. Exiting.{COLOR_RESET}\n")
            sys.exit(1)

    def monitor_servers(self):
        """Monitor running server processes and report crashes."""
        try:
            while not self.shutting_down:
                for process in self.processes:
                    poll_result = process.poll()
                    if poll_result is not None:
                        # Process terminated unexpectedly
                        print(f"\n⚠️  {COLOR_RED}{COLOR_BOLD}Process '{process.server_name.strip()}' (PID: {process.pid}) has stopped with exit code {poll_result}{COLOR_RESET}")
                        self.processes.remove(process)
                        if not self.processes:
                            print(f"All servers have stopped. Exiting.")
                            return
                time.sleep(1)
        except KeyboardInterrupt:
            # Will be caught and handled by clean shutdown
            pass

    def stop_servers(self):
        """Terminate all running processes cleanly."""
        if self.shutting_down:
            return
        self.shutting_down = True
        
        print(f"\n\n{COLOR_GREEN}[Launcher] Shutting down all MCP servers...{COLOR_RESET}")
        
        # Terminate processes
        for process in self.processes:
            if process.poll() is None:
                print(f"Stopping {process.color}{process.server_name.strip()}{COLOR_RESET} (PID: {process.pid})...")
                # Try close stdin first, often prompts fastmcp to exit cleanly
                try:
                    if process.stdin:
                        process.stdin.close()
                except Exception:
                    pass
                
                process.terminate()

        # Wait for processes to exit
        start_wait = time.time()
        running_processes = [p for p in self.processes if p.poll() is None]
        
        while running_processes and (time.time() - start_wait < 3.0):
            time.sleep(0.2)
            running_processes = [p for p in self.processes if p.poll() is None]

        # Force kill if still running
        for process in running_processes:
            print(f"⚠️  {COLOR_RED}{process.server_name.strip()} did not stop. Force killing (PID: {process.pid})...{COLOR_RESET}")
            try:
                process.kill()
                process.wait()
            except Exception:
                pass

        print(f"\n{COLOR_GREEN}[Launcher] All servers stopped.{COLOR_RESET}\n")

def main():
    init_ansi()
    
    # Initialize ServerManager to resolve root_dir first
    manager = ServerManager()
    
    load_environment_variables(manager.root_dir)
    
    def signal_handler(sig, frame):
        manager.stop_servers()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    manager.start_servers()
    manager.monitor_servers()
    manager.stop_servers()

if __name__ == "__main__":
    main()
