#!/bin/bash

# Source .env to get ports if needed, but we hardcode/pass them to server.py or server.py reads them.
# The server.py files currently have hardcoded ports in the __main__ block (8001, 8002) which matches .env.

echo "Starting Industry Query Server on port 8001..."
python3 mcp_servers/industry_query/server.py > logs/industry_server.log 2>&1 &
echo $! > logs/industry_server.pid

echo "Starting Deep Analysis Server on port 8002..."
python3 mcp_servers/deep_analysis/server.py > logs/deep_analysis_server.log 2>&1 &
echo $! > logs/deep_analysis_server.pid

echo "MCP Servers started."
