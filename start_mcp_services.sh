#!/bin/bash

# Source .env to get ports if needed, but we hardcode/pass them to server.py or server.py reads them.
# The server.py files currently have hardcoded ports in the __main__ block (8001, 8002) which matches .env.

echo "Starting Tourism Query Server on port 8001..."
python mcp_servers/tourism_query/server.py > logs/tourism_server.log 2>&1 &
echo $! > logs/tourism_server.pid

echo "Starting Deep Analysis Server on port 8002..."
python mcp_servers/deep_analysis/server.py > logs/deep_analysis_server.log 2>&1 &
echo $! > logs/deep_analysis_server.pid

echo "MCP Servers started."
