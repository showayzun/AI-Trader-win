# MCP Service Health Check

## Overview

This document describes the MCP (Model Context Protocol) service health check and management tools.

## Tools

### 1. start_mcp_services.py

Main script to start and manage MCP services.

**Features:**
- Start all MCP services (Math, Search, TradeTools, LocalPrices)
- Check service status
- Automatic port conflict detection and resolution
- Service retry logic with error reporting
- Improved error diagnostics

**Usage:**

```bash
# Start all services
python agent_tools/start_mcp_services.py

# Check service status
python agent_tools/start_mcp_services.py status

# Get help
python agent_tools/start_mcp_services.py --help
```

**Enhancements:**
- ✅ Retry logic: Services automatically retry up to 3 times on failure
- ✅ Better error messages: Shows detailed error information and log file locations
- ✅ Port conflict resolution: Automatically detects and offers to resolve port conflicts
- ✅ Process health monitoring: Checks both process status and port responsiveness

### 2. check_mcp_health.py

Comprehensive health check utility for MCP services.

**Features:**
- Check health of all services or specific service
- Detailed diagnostics including response times
- Watch mode for continuous monitoring
- Verbose mode for detailed information

**Usage:**

```bash
# Check all services
python agent_tools/check_mcp_health.py

# Verbose mode with detailed information
python agent_tools/check_mcp_health.py -v

# Watch mode - continuous monitoring every 5 seconds
python agent_tools/check_mcp_health.py -w 5

# Check specific service only
python agent_tools/check_mcp_health.py -s math
python agent_tools/check_mcp_health.py -s search

# Get help
python agent_tools/check_mcp_health.py --help
```

**Health Check Details:**
- ✅ Port availability check
- ✅ Socket connection test (validates service is listening)
- ✅ Response time measurement
- ✅ Detailed error reporting

## Service Status

### Service States

- **HEALTHY** ✅ - Service is running and responding normally
- **UNHEALTHY** ⚠️ - Service is running but not responding properly
- **NOT STARTED** ❌ - Service is not running
- **UNKNOWN** ❓ - Unable to determine service status

## Troubleshooting

### Common Issues

#### 1. "spawn uvx ENOENT" Error

This error occurs when the `uvx` command is not found. This typically means:
- The `uv` package manager is not installed
- The command is not in your PATH

**Solution:**
- The MCP services in this project don't require `uvx`
- Use the Python-based services instead: `python agent_tools/start_mcp_services.py`

#### 2. Port Already in Use

If a port is already in use:
1. The startup script will detect the conflict
2. You'll be prompted to automatically find available ports
3. Or you can manually stop the conflicting service

**Check which process is using a port:**
```bash
# Linux/Mac
lsof -i :8000

# Or
netstat -tlnp | grep 8000
```

#### 3. Service Fails to Start

If a service fails to start:
1. Check the log files in the `logs/` directory (relative to project root)
2. Verify dependencies are installed: `pip install -r requirements.txt`
3. Check environment variables in `.env` file
4. Run health check for detailed diagnostics: `python agent_tools/check_mcp_health.py -v`

#### 4. Service Exits Immediately

If a service exits immediately after starting:
1. Check the service log file for error messages
2. Verify Python version compatibility (requires Python 3.10+)
3. Check for missing dependencies
4. Ensure no conflicting processes on the same port

## Configuration

### Environment Variables

Configure service ports in your `.env` file:

```bash
MATH_HTTP_PORT=8000
SEARCH_HTTP_PORT=8001
TRADE_HTTP_PORT=8002
GETPRICE_HTTP_PORT=8003
```

### Default Ports

| Service      | Default Port |
|-------------|-------------|
| Math        | 8000        |
| Search      | 8001        |
| TradeTools  | 8002        |
| LocalPrices | 8003        |

## Service Endpoints

Each service exposes an MCP endpoint:
- Math: `http://localhost:8000/mcp`
- Search: `http://localhost:8001/mcp`
- TradeTools: `http://localhost:8002/mcp`
- LocalPrices: `http://localhost:8003/mcp`

## Best Practices

1. **Always check service health** after starting services
   ```bash
   python agent_tools/check_mcp_health.py -v
   ```

2. **Use watch mode** during development to monitor service health
   ```bash
   python agent_tools/check_mcp_health.py -w 10
   ```

3. **Check logs** when services fail
   ```bash
   tail -f logs/math.log
   tail -f logs/search.log
   tail -f logs/trade.log
   tail -f logs/price.log
   ```

4. **Stop services gracefully** with Ctrl+C when running interactively

## Exit Codes

### start_mcp_services.py
- `0`: Success (all services started or status checked)
- `1`: Failure (port conflicts or other errors)

### check_mcp_health.py
- `0`: All services healthy
- `1`: One or more services unhealthy

## Quick Reference

```bash
# Start services
python agent_tools/start_mcp_services.py

# Check status
python agent_tools/start_mcp_services.py status

# Health check
python agent_tools/check_mcp_health.py

# Detailed health check
python agent_tools/check_mcp_health.py -v

# Monitor continuously
python agent_tools/check_mcp_health.py -w 5

# Check specific service
python agent_tools/check_mcp_health.py -s math
```
