<#
.SYNOPSIS
  Civic Watch / Neighborhood Issue Reporter - Share Launcher
  Starts backend (FastAPI), frontend (Vite), and Cloudflare Tunnel.
#>

[Console]::Title = "Civic Watch - Share Launcher"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Resolve repo root
if (Test-Path (Join-Path $ScriptDir "package.json")) {
    $RepoRoot = $ScriptDir
} elseif (Test-Path (Join-Path (Split-Path -Parent (Split-Path -Parent $ScriptDir)) "package.json")) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
} else {
    $RepoRoot = (Get-Location).Path
}

Set-Location $RepoRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Launching Civic Watch & Cloudflare Tunnel             " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Locate Python
$PythonBin = $null
$VenvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPy) {
    $PythonBin = $VenvPy
} else {
    $sysPy = Get-Command python -ErrorAction SilentlyContinue
    if ($sysPy) {
        $PythonBin = $sysPy.Source
    }
}

if (-not $PythonBin) {
    Write-Host "[ERROR] Python was not found in .venv or system PATH!" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# 2. Locate cloudflared
$CloudflaredBin = $null
$rootCf = Join-Path $RepoRoot "cloudflared.exe"
$toolsCf = Join-Path $RepoRoot "tools\share\cloudflared.exe"
if (Test-Path $rootCf) {
    $CloudflaredBin = $rootCf
} elseif (Test-Path $toolsCf) {
    $CloudflaredBin = $toolsCf
} else {
    $sysCf = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($sysCf) {
        $CloudflaredBin = $sysCf.Source
    }
}

if (-not $CloudflaredBin) {
    Write-Host "[ERROR] cloudflared.exe not found in repo root or tools\share\!" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# 3. Verify npm
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCmd) {
    Write-Host "[ERROR] Node.js / npm not found in system PATH!" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

# Helper to probe an HTTP URL
function Test-HttpEndpoint {
    param([string]$Url, [int]$TimeoutSec = 2)
    try {
        $req = [System.Net.HttpWebRequest]::Create($Url)
        $req.Timeout = $TimeoutSec * 1000
        $req.Method = "GET"
        $req.UserAgent = "CivicWatch-HealthProbe"
        $resp = $req.GetResponse()
        $code = [int]$resp.StatusCode
        $resp.Close()
        return ($code -ge 200 -and $code -lt 500)
    } catch [System.Net.WebException] {
        if ($_.Response) {
            $code = [int]$_.Response.StatusCode
            $_.Response.Close()
            return ($code -ge 200 -and $code -lt 500)
        }
        return $false
    } catch {
        return $false
    }
}

function Wait-ForEndpoint {
    param([string]$Url, [string]$Name, [int]$MaxSeconds = 25)
    Write-Host -NoNewline "  Waiting for $Name ($Url) "
    $deadline = [DateTime]::UtcNow.AddSeconds($MaxSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-HttpEndpoint -Url $Url) {
            Write-Host " [READY]" -ForegroundColor Green
            return $true
        }
        Write-Host -NoNewline "."
        Start-Sleep -Seconds 1
    }
    Write-Host " [TIMEOUT]" -ForegroundColor Yellow
    return $false
}

# Helper to stop all lingering cloudflared processes
function Stop-LingeringCloudflared {
    try {
        Get-Process -Name cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    } catch {}
    Start-Sleep -Milliseconds 400
}

# Helper to safely clear/reset log file
function Reset-LogFile {
    param([string]$Path)
    for ($i = 0; $i -lt 5; $i++) {
        try {
            if (Test-Path $Path) {
                Remove-Item -Path $Path -Force -ErrorAction Stop
            }
            [System.IO.File]::WriteAllText($Path, "")
            return
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
}

Stop-LingeringCloudflared

# -------------------------------------------------------------
# Step 1: Start Backend
# -------------------------------------------------------------
$backendUrl = "http://127.0.0.1:8000/docs"
if (Test-HttpEndpoint -Url $backendUrl) {
    Write-Host "[1/3] Backend is already running on port 8000." -ForegroundColor Green
} else {
    Write-Host "[1/3] Starting local backend on port 8000 (FastAPI)..." -ForegroundColor Cyan
    $beArgs = "/k title NIR Backend && `"$PythonBin`" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
    Start-Process -FilePath "cmd.exe" -ArgumentList $beArgs -WorkingDirectory $RepoRoot
    $ready = Wait-ForEndpoint -Url $backendUrl -Name "Backend" -MaxSeconds 30
    if (-not $ready) {
        Write-Host "      (Backend may still be connecting to database...)" -ForegroundColor Yellow
    }
}

# -------------------------------------------------------------
# Step 2: Start Frontend
# -------------------------------------------------------------
$frontendUrl = "http://localhost:5173"
if (Test-HttpEndpoint -Url $frontendUrl) {
    Write-Host "[2/3] Frontend is already running on port 5173." -ForegroundColor Green
} else {
    Write-Host "[2/3] Starting local frontend on port 5173 (Vite)..." -ForegroundColor Cyan
    $feArgs = "/k title NIR Frontend && npm run dev"
    Start-Process -FilePath "cmd.exe" -ArgumentList $feArgs -WorkingDirectory $RepoRoot
    $ready = Wait-ForEndpoint -Url $frontendUrl -Name "Frontend" -MaxSeconds 20
}

# Give one extra second for ports to settle
Start-Sleep -Seconds 1

# -------------------------------------------------------------
# Step 3: Start Cloudflare Tunnel
# -------------------------------------------------------------
Write-Host "[3/3] Creating Cloudflare public tunnel..." -ForegroundColor Cyan

$logFile = Join-Path $RepoRoot "cloudflared.log"
Reset-LogFile -Path $logFile

function Start-TunnelInstance {
    param([string]$Protocol = "http2")
    
    # http2 is preferred for reliability over standard TCP 443, avoiding UDP NAT timeouts
    $argsList = "tunnel --url http://127.0.0.1:5173 --http-host-header localhost:5173 --edge-ip-version auto --protocol $Protocol --logfile `"$logFile`""

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $CloudflaredBin
    $psi.Arguments = $argsList
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    $proc = [System.Diagnostics.Process]::Start($psi)
    return $proc
}

function Get-TunnelUrlFromLog {
    param([string]$Path, [System.Diagnostics.Process]$Proc, [int]$TimeoutSec = 20)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
    $foundUrl = $null

    while ([DateTime]::UtcNow -lt $deadline -and [string]::IsNullOrEmpty($foundUrl) -and -not $Proc.HasExited) {
        if (Test-Path $Path) {
            try {
                $lines = Get-Content -Path $Path -ErrorAction SilentlyContinue
                if ($lines) {
                    foreach ($line in $lines) {
                        if ($line -match '(https://[a-zA-Z0-9-]+\.trycloudflare\.com)') {
                            $foundUrl = $matches[1]
                            break
                        }
                    }
                }
            } catch {}
        }
        if ([string]::IsNullOrEmpty($foundUrl)) {
            Start-Sleep -Milliseconds 250
            Write-Host -NoNewline "."
        }
    }
    return $foundUrl
}

Write-Host -NoNewline "  Requesting trycloudflare.com address (HTTP/2) "
$tunnelProc = Start-TunnelInstance -Protocol "http2"
$tunnelUrl = Get-TunnelUrlFromLog -Path $logFile -Proc $tunnelProc -TimeoutSec 15

# Fallback 1: Try QUIC if HTTP/2 was slow to negotiate
if ([string]::IsNullOrEmpty($tunnelUrl)) {
    Write-Host "`n  Trying tunnel over QUIC protocol..." -ForegroundColor Yellow
    if ($tunnelProc -and -not $tunnelProc.HasExited) {
        $tunnelProc.Kill()
    }
    Stop-LingeringCloudflared
    Reset-LogFile -Path $logFile
    Write-Host -NoNewline "  Requesting address "
    $tunnelProc = Start-TunnelInstance -Protocol "quic"
    $tunnelUrl = Get-TunnelUrlFromLog -Path $logFile -Proc $tunnelProc -TimeoutSec 15
}

Write-Host ""

if ([string]::IsNullOrEmpty($tunnelUrl)) {
    Write-Host "[ERROR] Could not obtain a quick Tunnel URL from Cloudflare." -ForegroundColor Red
    Write-Host "Please check your internet connection or firewall." -ForegroundColor Yellow
    if (Test-Path $logFile) {
        Write-Host "`nRecent logs:" -ForegroundColor Gray
        Get-Content $logFile -Tail 15 -ErrorAction SilentlyContinue
    }
    Read-Host "Press Enter to exit..."
    if ($tunnelProc -and -not $tunnelProc.HasExited) {
        $tunnelProc.Kill()
    }
    exit 1
}

# Save URL to root file
$urlFile = Join-Path $RepoRoot "tunnel-url.txt"
Set-Content -Path $urlFile -Value $tunnelUrl -Force

# Copy URL to clipboard
try {
    Set-Clipboard -Value $tunnelUrl -ErrorAction SilentlyContinue
} catch {}

# Wait for Cloudflare global DNS propagation to prevent DNS_PROBE_FINISHED_NXDOMAIN
try {
    $uri = [System.Uri]$tunnelUrl
    $hostname = $uri.Host
    Write-Host -NoNewline "  Verifying Cloudflare DNS propagation "
    $dnsDeadline = [DateTime]::UtcNow.AddSeconds(20)
    $dnsReady = $false
    while ([DateTime]::UtcNow -lt $dnsDeadline) {
        try {
            $entry = [System.Net.Dns]::GetHostEntry($hostname)
            if ($entry -and $entry.AddressList.Count -gt 0) {
                $dnsReady = $true
                break
            }
        } catch {}
        Write-Host -NoNewline "."
        Start-Sleep -Seconds 1
    }
    if ($dnsReady) {
        Write-Host " [ACTIVE]" -ForegroundColor Green
    } else {
        Write-Host " [PROPAGATING]" -ForegroundColor Yellow
    }
} catch {}

# Open browser
try {
    Start-Process $tunnelUrl
} catch {}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "             CIVIC WATCH / NIR IS LIVE PUBLICLY!                       " -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Public Share URL:  " -NoNewline
Write-Host "$tunnelUrl" -ForegroundColor Cyan -BackgroundColor Black
Write-Host "  Local Frontend:    http://localhost:5173" -ForegroundColor Gray
Write-Host "  Local API Docs:    http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "  * URL automatically copied to clipboard!" -ForegroundColor Green
Write-Host "  * Opened in your default browser!" -ForegroundColor Green
Write-Host "  * Saved to: tunnel-url.txt" -ForegroundColor Green
Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "  Tunnel is active. Press 'Q' or Ctrl+C in this window to stop.        " -ForegroundColor Yellow
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""

$healthCheckCounter = 0
try {
    while ($true) {
        $hasKey = $false
        try {
            if ([Console]::KeyAvailable) {
                $hasKey = $true
            }
        } catch {}

        if ($hasKey) {
            $key = [Console]::ReadKey($true)
            if ($key.Key -eq 'Q' -or $key.Key -eq 'Escape') {
                break
            }
        }

        # Health check every ~3 seconds
        $healthCheckCounter++
        if ($healthCheckCounter -ge 10) {
            $healthCheckCounter = 0
            
            $needsRestart = $false
            if ($tunnelProc.HasExited) {
                Write-Host "`n[!] Cloudflare Tunnel process exited unexpectedly." -ForegroundColor Yellow
                $needsRestart = $true
            } elseif (Test-Path $logFile) {
                $recentLog = Get-Content -Path $logFile -Tail 15 -ErrorAction SilentlyContinue | Out-String
                if ($recentLog -match "Unauthorized: Tunnel not found|Register tunnel error from server side|datagram manager error") {
                    Write-Host "`n[!] Cloudflare Tunnel disconnected from edge (session expired)." -ForegroundColor Yellow
                    $needsRestart = $true
                }
            }

            if ($needsRestart) {
                Write-Host "    Re-establishing fresh Cloudflare tunnel session..." -ForegroundColor Cyan
                if ($tunnelProc -and -not $tunnelProc.HasExited) {
                    $tunnelProc.Kill()
                }
                Stop-LingeringCloudflared
                Reset-LogFile -Path $logFile
                
                $tunnelProc = Start-TunnelInstance -Protocol "http2"
                $newUrl = Get-TunnelUrlFromLog -Path $logFile -Proc $tunnelProc -TimeoutSec 15
                if (-not [string]::IsNullOrEmpty($newUrl)) {
                    $tunnelUrl = $newUrl
                    Set-Content -Path $urlFile -Value $tunnelUrl -Force
                    try { Set-Clipboard -Value $tunnelUrl -ErrorAction SilentlyContinue } catch {}
                    Write-Host "    [RECONNECTED] New Public URL: $tunnelUrl" -ForegroundColor Green
                } else {
                    Write-Host "    [WARNING] Reconnect attempt failed. Will retry..." -ForegroundColor Red
                }
            }
        }

        Start-Sleep -Milliseconds 300
    }
} finally {
    Write-Host "`nStopping Cloudflare Tunnel..." -ForegroundColor Yellow
    if ($tunnelProc -and -not $tunnelProc.HasExited) {
        $tunnelProc.Kill()
    }
    Stop-LingeringCloudflared
    
    Write-Host ""
    $stopServers = $null
    try {
        $stopServers = Read-Host "Do you want to stop the local backend and frontend servers too? (Y/N) [default: Y]"
    } catch {}

    if ($stopServers -ne "n" -and $stopServers -ne "N") {
        Write-Host "Stopping NIR servers..." -ForegroundColor Yellow
        Get-Process -ErrorAction SilentlyContinue | Where-Object { 
            $_.MainWindowTitle -like "*NIR Backend*" -or $_.MainWindowTitle -like "*NIR Frontend*" 
        } | Stop-Process -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Done! Goodbye." -ForegroundColor Green
}
