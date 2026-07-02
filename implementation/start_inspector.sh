#!/bin/bash
# Get absolute directory path of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$DIR/.." && pwd )"

PYTHON_EXE="$PROJECT_ROOT/.venv/bin/python"
if [ ! -f "$PYTHON_EXE" ]; then
    # Fallback to Windows virtualenv path if running under git bash/msys
    PYTHON_EXE="$PROJECT_ROOT/.venv/Scripts/python"
fi

SERVER_PY="$DIR/mcp_server.py"

echo "Starting Model Context Protocol Inspector..."
echo "Python: $PYTHON_EXE"
echo "Server: $SERVER_PY"

npx -y @modelcontextprotocol/inspector "$PYTHON_EXE" "$SERVER_PY"
