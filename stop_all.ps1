# Function to kill process by port
function Stop-ProcessByPort {
    param([int]$Port, [string]$Name)
    
    $tcpConnection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($tcpConnection) {
        $pids = $tcpConnection | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($p in $pids) {
            try {
                $process = Get-Process -Id $p -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "Stopping $Name (Port $Port, PID: $p)..." -ForegroundColor Yellow
                    Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
                    Write-Host "  Success." -ForegroundColor Green
                }
            } catch {
                Write-Host "  Failed to stop PID ${p}: $_" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "$Name (Port $Port) is not running." -ForegroundColor Gray
    }
}

Write-Host "Stopping Multi-Agent System Services..." -ForegroundColor Cyan
Write-Host "---------------------------------------" -ForegroundColor Cyan

# Stop MCP Servers
Stop-ProcessByPort 8001 "MCP Sales (8001)"
Stop-ProcessByPort 8002 "MCP Supply (8002)"
Stop-ProcessByPort 8003 "MCP HR (8003)"
Stop-ProcessByPort 8004 "MCP Weather (8004)"

# Stop Backend
Stop-ProcessByPort 8000 "Backend API (8000)"

# Stop Frontend
Stop-ProcessByPort 5173 "Frontend (Vite)"

# Close Terminal Windows
Write-Host "`nClosing Terminal Windows..." -ForegroundColor Cyan
function Close-WindowByTitle {
    param([string]$TitlePattern)
    $processes = Get-Process | Where-Object { $_.MainWindowTitle -like $TitlePattern }
    foreach ($p in $processes) {
        Write-Host "  Closing Window: $($p.MainWindowTitle)" -ForegroundColor Yellow
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    }
}

Close-WindowByTitle "MCP - *"
Close-WindowByTitle "Agent Framework *"

Write-Host "`nAll cleanup operations completed." -ForegroundColor Cyan
