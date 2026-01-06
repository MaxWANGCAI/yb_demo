#!/bin/bash

echo "Stopping MCP Servers..."

if [ -f logs/tourism_server.pid ]; then
    pid=$(cat logs/tourism_server.pid)
    kill $pid
    rm logs/tourism_server.pid
    echo "Stopped Tourism Server (PID $pid)"
else
    echo "Tourism Server PID file not found."
fi

if [ -f logs/deep_analysis_server.pid ]; then
    pid=$(cat logs/deep_analysis_server.pid)
    kill $pid
    rm logs/deep_analysis_server.pid
    echo "Stopped Deep Analysis Server (PID $pid)"
else
    echo "Deep Analysis Server PID file not found."
fi

echo "MCP Servers stopped."
