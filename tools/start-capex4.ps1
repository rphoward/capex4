param(
    [switch] $NoBrowser,
    [switch] $NoWait
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$SrcPath = Join-Path $RepoRoot "src"
$LogDir = Join-Path $RepoRoot "tmp"
$LogPath = Join-Path $LogDir "capex4-server.log"
$ErrorLogPath = Join-Path $LogDir "capex4-server-error.log"

function Test-PortAvailable {
    param([int] $Port)

    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $listener) {
            $listener.Stop()
        }
    }
}

function Select-CapexPort {
    foreach ($port in 3000..3099) {
        if (Test-PortAvailable -Port $port) {
            return $port
        }
    }

    throw "No available localhost port found in 3000..3099."
}

function Wait-ForReady {
    param(
        [string] $ReadyUrl,
        [System.Diagnostics.Process] $Process
    )

    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        if ($Process.HasExited) {
            throw "The CapEx server stopped before it became ready. See $LogPath."
        }

        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $ReadyUrl -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return
            }
        } catch {
            Start-Sleep -Milliseconds 350
        }
    }

    throw "The CapEx server did not become ready within 20 seconds. See $LogPath."
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

$port = Select-CapexPort
$appUrl = "http://127.0.0.1:$port/"
$readyUrl = "http://127.0.0.1:$port/ready"

$env:PYTHONPATH = $SrcPath
$env:RENTAL_CAPEX_PYTHON_HOST = "127.0.0.1"
$env:RENTAL_CAPEX_PYTHON_PORT = [string] $port

Write-Host "Starting Rental CapEx app on $appUrl"
Write-Host "Server log: $LogPath"

$server = Start-Process `
    -FilePath "python" `
    -ArgumentList @("-B", "-m", "capex3.infrastructure.server", "--host", "127.0.0.1", "--port", [string] $port) `
    -WorkingDirectory $RepoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $LogPath `
    -RedirectStandardError $ErrorLogPath `
    -PassThru

try {
    Wait-ForReady -ReadyUrl $readyUrl -Process $server
    if (-not $NoBrowser) {
        Start-Process $appUrl
    }

    Write-Host ""
    Write-Host "Rental CapEx is running."
    Write-Host "Browser URL: $appUrl"
    if ($NoWait) {
        return
    }
    Write-Host "Press Escape in this window to stop the app."
    do {
        $key = [Console]::ReadKey($true)
    } while ($key.Key -ne [ConsoleKey]::Escape)
} finally {
    if ($null -ne $server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id
        Write-Host "Stopped Rental CapEx."
    }
}
