#!/bin/bash
echo "Stopping local server..."
pkill -f "python3 -m http.server"
echo "Server stopped."
