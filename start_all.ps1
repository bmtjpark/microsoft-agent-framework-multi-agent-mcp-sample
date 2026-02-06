# Set PYTHONPATH to project root
$env:PYTHONPATH = $PSScriptRoot

# Activate virtual environment
& ".\.venv\Scripts\Activate.ps1"

# Function to start a process in a new window
function Start-ServerWindow {
    param(
        [string]$Title,
        [string]$Command
    )
    # Set window title, set PYTHONPATH, activate venv, and run command
    $Args = "-NoExit", "-Command", "& { `$Host.UI.RawUI.WindowTitle = '$Title'; `$env:PYTHONPATH = '$PSScriptRoot'; & '$PSScriptRoot\.venv\Scripts\Activate.ps1'; $Command }"
    Start-Process powershell -ArgumentList $Args
}

Write-Host "Initializing Multi-Agent System..." -ForegroundColor Cyan

# 1. Start MCP Servers
Write-Host "1. Starting MCP Servers..." -ForegroundColor Green
Start-ServerWindow "MCP - Sales CRM (8001)" "python src/mcp/mcp-sales-crm/sales_server.py --sse"
Start-ServerWindow "MCP - Supply Chain (8002)" "python src/mcp/mcp-supply-chain/supply_server.py --sse"
Start-ServerWindow "MCP - HR Policy (8003)" "python src/mcp/mcp-hr-policy/hr_server.py --sse"
Start-ServerWindow "MCP - Weather (8004)" "python src/mcp/mcp-weather/weather_server.py --sse"

# 2. Start Backend
Write-Host "2. Starting Backend API..." -ForegroundColor Green
Start-ServerWindow "Agent Framework Backend (8000)" "uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload"

# 3. Start Frontend
Write-Host "3. Starting Frontend..." -ForegroundColor Green
Start-ServerWindow "Agent Framework Frontend" "npm run dev --prefix src/frontend"

Write-Host "`nAll services launched in separate windows." -ForegroundColor Yellow
Write-Host "Use 'stop_all.ps1' to stop all services." -ForegroundColor Gray
