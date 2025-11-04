#!/usr/bin/env python3
"""
MCP Service Health Check Utility
Provides comprehensive health checking for MCP services
"""

import os
import sys
import time
import socket
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from dotenv import load_dotenv

load_dotenv()


class ServiceStatus(Enum):
    """Service health status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    NOT_STARTED = "not_started"


@dataclass
class HealthCheckResult:
    """Health check result for a service"""
    service_name: str
    port: int
    status: ServiceStatus
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    details: Optional[Dict] = None


class MCPHealthChecker:
    """Health checker for MCP services"""
    
    def __init__(self):
        self.ports = {
            "math": int(os.getenv("MATH_HTTP_PORT", "8000")),
            "search": int(os.getenv("SEARCH_HTTP_PORT", "8001")),
            "trade": int(os.getenv("TRADE_HTTP_PORT", "8002")),
            "price": int(os.getenv("GETPRICE_HTTP_PORT", "8003")),
        }
        
        self.service_names = {
            "math": "Math",
            "search": "Search",
            "trade": "TradeTools",
            "price": "LocalPrices",
        }
    
    def _test_socket_connection(self, port: int, timeout: float) -> Tuple[int, float]:
        """
        Test socket connection to a port
        Returns: (result_code, response_time_ms)
        Result code 0 means success, non-zero means failure
        """
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        response_time = (time.time() - start_time) * 1000
        return result, response_time
    
    def check_port_open(self, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open and accepting connections"""
        try:
            result, _ = self._test_socket_connection(port, timeout)
            return result == 0
        except Exception:
            return False
    
    def check_service_connection(self, port: int, timeout: float = 2.0) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Check service connection status
        Returns: (is_connected, response_time_ms, error_message)
        
        Note: FastMCP services don't expose a /health endpoint by default,
        so we verify the port is responding to connections.
        """
        try:
            result, response_time = self._test_socket_connection(port, timeout)
            
            if result == 0:
                return True, response_time, None
            else:
                return False, response_time, f"Connection failed (error code: {result})"
        except socket.timeout:
            return False, None, "Connection timeout"
        except Exception as e:
            return False, None, str(e)
    
    def check_service(self, service_id: str) -> HealthCheckResult:
        """Perform comprehensive health check for a service"""
        # Validate service_id
        if service_id not in self.service_names:
            raise ValueError(f"Invalid service_id: {service_id}. Must be one of: {list(self.service_names.keys())}")
        
        service_name = self.service_names[service_id]
        port = self.ports[service_id]
        
        # First check if port is open
        if not self.check_port_open(port):
            return HealthCheckResult(
                service_name=service_name,
                port=port,
                status=ServiceStatus.NOT_STARTED,
                error_message="Port not open"
            )
        
        # Then check service connection
        is_connected, response_time, error_msg = self.check_service_connection(port)
        
        if is_connected:
            status = ServiceStatus.HEALTHY
        elif error_msg:
            status = ServiceStatus.UNHEALTHY
        else:
            status = ServiceStatus.UNKNOWN
        
        return HealthCheckResult(
            service_name=service_name,
            port=port,
            status=status,
            response_time_ms=response_time,
            error_message=error_msg
        )
    
    def check_all_services(self) -> List[HealthCheckResult]:
        """Check health of all services"""
        results = []
        for service_id in self.ports.keys():
            result = self.check_service(service_id)
            results.append(result)
        return results
    
    def print_health_report(self, results: List[HealthCheckResult], verbose: bool = False):
        """Print health check report"""
        print("=" * 70)
        print("🏥 MCP Services Health Check Report")
        print("=" * 70)
        print()
        
        healthy_count = sum(1 for r in results if r.status == ServiceStatus.HEALTHY)
        total_count = len(results)
        
        for result in results:
            if result.status == ServiceStatus.HEALTHY:
                icon = "✅"
                status_text = "HEALTHY"
            elif result.status == ServiceStatus.UNHEALTHY:
                icon = "⚠️"
                status_text = "UNHEALTHY"
            elif result.status == ServiceStatus.NOT_STARTED:
                icon = "❌"
                status_text = "NOT STARTED"
            else:
                icon = "❓"
                status_text = "UNKNOWN"
            
            print(f"{icon} {result.service_name:<15} Port: {result.port:<6} Status: {status_text}")
            
            if verbose or result.status != ServiceStatus.HEALTHY:
                if result.response_time_ms is not None:
                    print(f"   Response time: {result.response_time_ms:.2f}ms")
                if result.error_message:
                    print(f"   Error: {result.error_message}")
            print()
        
        print("=" * 70)
        print(f"Summary: {healthy_count}/{total_count} services healthy")
        print("=" * 70)
        
        if healthy_count < total_count:
            print()
            print("💡 Troubleshooting tips:")
            print("   1. Check if services are started: python agent_tools/start_mcp_services.py")
            print("   2. Check service logs in: ../logs/")
            print("   3. Verify port availability with: netstat -tlnp | grep <port>")
            print("   4. Check environment variables in .env file")
        
        return healthy_count == total_count


def main():
    """Main function"""
    import argparse
    
    # Get available services dynamically
    checker = MCPHealthChecker()
    available_services = list(checker.ports.keys())
    
    parser = argparse.ArgumentParser(description="MCP Services Health Checker")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-w", "--watch", type=int, metavar="SECONDS", help="Watch mode: check every N seconds")
    parser.add_argument("-s", "--service", choices=available_services, help="Check specific service only")
    
    args = parser.parse_args()
    
    if args.watch:
        print(f"🔄 Starting health check in watch mode (checking every {args.watch} seconds)")
        print("Press Ctrl+C to stop")
        print()
        
        try:
            while True:
                results = checker.check_all_services()
                checker.print_health_report(results, verbose=args.verbose)
                print(f"\n⏰ Next check in {args.watch} seconds...\n")
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\n\n✋ Health check stopped by user")
            sys.exit(0)
    else:
        if args.service:
            result = checker.check_service(args.service)
            results = [result]
        else:
            results = checker.check_all_services()
        
        all_healthy = checker.print_health_report(results, verbose=args.verbose)
        sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    main()
