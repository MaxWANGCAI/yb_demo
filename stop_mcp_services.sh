#!/bin/bash

echo "Stopping MCP Servers..."

if [ -f logs/industry_server.pid ]; then
    pid=$(cat logs/industry_server.pid)
    kill $pid
    rm logs/industry_server.pid
    echo "Stopped Industry Server (PID $pid)"
else
    echo "Industry Server PID file not found."
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
