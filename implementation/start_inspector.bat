@echo off
REM Get absolute path to project root (parent directory of implementation)
for %%i in ("%~dp0..") do set "PROJECT_ROOT=%%~fi"

set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "SERVER_PY=%~dp0mcp_server.py"

echo Starting Model Context Protocol Inspector...
echo Python: %PYTHON_EXE%
echo Server: %SERVER_PY%

npx -y @modelcontextprotocol/inspector "%PYTHON_EXE%" "%SERVER_PY%"
