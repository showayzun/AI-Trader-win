#!/usr/bin/env python3
"""
MCP Service Startup Script (Python Version)
Start all four MCP services: Math, Search, TradeTools, LocalPrices
"""

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class MCPServiceManager:
    # Log formatting constants
    LOG_SEPARATOR_LENGTH = 60
    LOG_SEPARATOR = "=" * LOG_SEPARATOR_LENGTH
    
    def __init__(self):
        self.services = {}
        self.running = True

        # Set default ports
        self.ports = {
            "math": int(os.getenv("MATH_HTTP_PORT", "8000")),
            "search": int(os.getenv("SEARCH_HTTP_PORT", "8001")),
            "trade": int(os.getenv("TRADE_HTTP_PORT", "8002")),
            "price": int(os.getenv("GETPRICE_HTTP_PORT", "8003")),
        }

        # Service configurations
        self.service_configs = {
            "math": {"script": "tool_math.py", "name": "Math", "port": self.ports["math"]},
            "search": {"script": "tool_jina_search.py", "name": "Search", "port": self.ports["search"]},
            "trade": {"script": "tool_trade.py", "name": "TradeTools", "port": self.ports["trade"]},
            "price": {"script": "tool_get_price_local.py", "name": "LocalPrices", "port": self.ports["price"]},
        }

        # Create logs directory (relative to script location)
        script_dir = Path(__file__).parent
        self.log_dir = (script_dir / "../logs").resolve()
        self.log_dir.mkdir(exist_ok=True)

        # Set signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        print("\n🛑 Received stop signal, shutting down all services...")
        self.stop_all_services()
        sys.exit(0)

    def is_port_available(self, port):
        """Check if a port is available"""
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            return result != 0  # Port is available if connection failed
        except:
            return False

    def check_port_conflicts(self):
        """Check for port conflicts before starting services"""
        conflicts = []
        for service_id, config in self.service_configs.items():
            port = config["port"]
            if not self.is_port_available(port):
                conflicts.append((config["name"], port))

        if conflicts:
            print("⚠️  Port conflicts detected:")
            for name, port in conflicts:
                print(f"   - {name}: Port {port} is already in use")

            import socket

            response = input("\n❓ Do you want to automatically find available ports? (y/n): ")
            if response.lower() == "y":
                for service_id, config in self.service_configs.items():
                    port = config["port"]
                    if not self.is_port_available(port):
                        # Find next available port
                        new_port = port
                        while not self.is_port_available(new_port):
                            new_port += 1
                            if new_port > port + 100:  # Limit search range
                                print(f"❌ Could not find available port for {config['name']}")
                                return False
                        print(f"   ✅ {config['name']}: Changed port from {port} to {new_port}")
                        config["port"] = new_port
                        self.ports[service_id] = new_port
                return True
            else:
                print("\n💡 Tip: Stop the conflicting services or change port configuration")
                return False
        return True

    def start_service(self, service_id, config, retry=3):
        """Start a single service with retry logic"""
        script_path = config["script"]
        service_name = config["name"]
        port = config["port"]

        if not Path(script_path).exists():
            print(f"❌ Script file not found: {script_path}")
            return False

        for attempt in range(retry):
            try:
                # Start service process
                log_file = self.log_dir / f"{service_id}.log"
                with open(log_file, "w" if attempt == 0 else "a") as f:
                    if attempt > 0:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        f.write(f"\n{self.LOG_SEPARATOR}\n")
                        f.write(f"Retry attempt {attempt} at {timestamp}\n")
                        f.write(f"{self.LOG_SEPARATOR}\n\n")
                    
                    process = subprocess.Popen(
                        [sys.executable, script_path], 
                        stdout=f, 
                        stderr=subprocess.STDOUT, 
                        cwd=os.getcwd(),
                        env={**os.environ, "PYTHONUNBUFFERED": "1"}
                    )

                self.services[service_id] = {"process": process, "name": service_name, "port": port, "log_file": log_file}

                # Wait a moment to check if process starts successfully
                time.sleep(0.5)
                if process.poll() is None:
                    print(f"✅ {service_name} service started (PID: {process.pid}, Port: {port})")
                    return True
                else:
                    print(f"⚠️  {service_name} service exited immediately (attempt {attempt + 1}/{retry})")
                    if attempt < retry - 1:
                        print(f"   Retrying in 1 second...")
                        time.sleep(1)
                    else:
                        print(f"   Check log file: {log_file}")

            except Exception as e:
                print(f"❌ Failed to start {service_name} service (attempt {attempt + 1}/{retry}): {e}")
                if attempt < retry - 1:
                    time.sleep(1)
        
        return False

    def check_service_health(self, service_id, timeout=2):
        """Check service health status with improved diagnostics"""
        if service_id not in self.services:
            return False

        service = self.services[service_id]
        process = service["process"]
        port = service["port"]

        # Check if process is still running
        if process.poll() is not None:
            print(f"   ⚠️  {service['name']} process terminated (exit code: {process.poll()})")
            return False

        # Check if port is responding
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(("localhost", port))
            sock.close()
            
            if result == 0:
                return True
            else:
                print(f"   ⚠️  {service['name']} port {port} not responding (error code: {result})")
                return False
        except Exception as e:
            print(f"   ⚠️  {service['name']} health check error: {e}")
            return False

    def start_all_services(self):
        """Start all services"""
        print("🚀 Starting MCP services...")
        print("=" * 50)

        # Check for port conflicts
        if not self.check_port_conflicts():
            print("\n❌ Cannot start services due to port conflicts")
            return

        print(f"\n📊 Port configuration:")
        for service_id, config in self.service_configs.items():
            print(f"  - {config['name']}: {config['port']}")

        print("\n🔄 Starting services...")

        # Start all services
        success_count = 0
        for service_id, config in self.service_configs.items():
            if self.start_service(service_id, config):
                success_count += 1

        if success_count == 0:
            print("\n❌ No services started successfully")
            return

        # Wait for services to start
        print("\n⏳ Waiting for services to initialize...")
        time.sleep(3)

        # Check service status
        print("\n🔍 Checking service health...")
        healthy_count = self.check_all_services()

        if healthy_count > 0:
            print(f"\n🎉 {healthy_count}/{len(self.services)} MCP services running!")
            self.print_service_info()
            
            # Provide health check command
            print(f"\n💡 To check service health anytime, run:")
            print(f"   python agent_tools/check_mcp_health.py")
            print(f"   python agent_tools/check_mcp_health.py -v  # verbose mode")
            print(f"   python agent_tools/check_mcp_health.py -w 5  # watch mode (check every 5s)")
            
            # Keep running
            self.keep_alive()
        else:
            print("\n❌ All services failed to start properly")
            print("\n📋 Troubleshooting steps:")
            print("  1. Check log files in ../logs/ directory")
            print("  2. Verify all dependencies are installed: pip install -r requirements.txt")
            print("  3. Check if ports are available")
            print("  4. Run health check: python agent_tools/check_mcp_health.py")
            self.stop_all_services()

    def check_all_services(self):
        """Check all service status and return count of healthy services"""
        healthy_count = 0
        for service_id, service in self.services.items():
            if self.check_service_health(service_id):
                print(f"✅ {service['name']} service running normally")
                healthy_count += 1
            else:
                print(f"❌ {service['name']} service failed to start")
                print(f"   Please check logs: {service['log_file']}")
        return healthy_count

    def print_service_info(self):
        """Print service information"""
        print("\n📋 Service information:")
        for service_id, service in self.services.items():
            print(f"  - {service['name']}: http://localhost:{service['port']} (PID: {service['process'].pid})")

        print(f"\n📁 Log files location: {self.log_dir.absolute()}")
        print("\n🛑 Press Ctrl+C to stop all services")

    def keep_alive(self):
        """Keep services running"""
        try:
            while self.running:
                time.sleep(5)

                # Check service status
                stopped_services = []
                for service_id, service in self.services.items():
                    if service["process"].poll() is not None:
                        stopped_services.append(service["name"])

                if stopped_services:
                    print(f"\n⚠️  Following service(s) stopped unexpectedly: {', '.join(stopped_services)}")
                    print(f"📋 Active services: {len(self.services) - len(stopped_services)}/{len(self.services)}")

                    # Only stop all if all services have failed
                    if len(stopped_services) == len(self.services):
                        print("❌ All services have stopped, shutting down...")
                        self.running = False
                        break

        except KeyboardInterrupt:
            pass
        finally:
            self.stop_all_services()

    def stop_all_services(self):
        """Stop all services"""
        print("\n🛑 Stopping all services...")

        for service_id, service in self.services.items():
            try:
                service["process"].terminate()
                service["process"].wait(timeout=5)
                print(f"✅ {service['name']} service stopped")
            except subprocess.TimeoutExpired:
                service["process"].kill()
                print(f"🔨 {service['name']} service force stopped")
            except Exception as e:
                print(f"❌ Error stopping {service['name']} service: {e}")

        print("✅ All services stopped")

    def status(self):
        """Display service status"""
        print("📊 MCP Service Status Check")
        print("=" * 50)
        
        # Check port availability
        running_count = 0
        for service_id, config in self.service_configs.items():
            port = config['port']
            port_open = not self.is_port_available(port)
            
            if port_open:
                print(f"✅ {config['name']:<15} Port: {port:<6} Status: RUNNING")
                running_count += 1
            else:
                print(f"❌ {config['name']:<15} Port: {port:<6} Status: NOT STARTED")
        
        print("=" * 50)
        print(f"Summary: {running_count}/{len(self.service_configs)} services running")
        
        if running_count == 0:
            print("\n💡 To start services, run:")
            print("   python agent_tools/start_mcp_services.py")
        elif running_count < len(self.service_configs):
            print("\n⚠️  Some services are not running")
            print("   Check logs in ../logs/ directory")
        
        print("\n🔍 For detailed health check, run:")
        print("   python agent_tools/check_mcp_health.py -v")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MCP Service Manager - Start and manage MCP services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_mcp_services.py              # Start all services
  python start_mcp_services.py status       # Check service status
  python start_mcp_services.py --help       # Show this help message

For detailed health checks:
  python check_mcp_health.py -v             # Verbose health check
  python check_mcp_health.py -w 5           # Watch mode (check every 5s)
        """
    )
    
    parser.add_argument(
        "command",
        nargs="?",
        choices=["status"],
        help="Command to execute (default: start services)"
    )
    
    args = parser.parse_args()
    
    if args.command == "status":
        # Status check mode
        manager = MCPServiceManager()
        manager.status()
    else:
        # Startup mode
        manager = MCPServiceManager()
        manager.start_all_services()


if __name__ == "__main__":
    main()
