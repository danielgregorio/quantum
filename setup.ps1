#Requires -Version 5.1
<#
.SYNOPSIS
    Quantum Admin - Native PowerShell Installer
.DESCRIPTION
    Enterprise-grade installation for Windows systems
.NOTES
    Author: Quantum Team
    Version: 1.0
#>

# Set error action
$ErrorActionPreference = "Stop"

# Enable TLS 1.2 for secure downloads
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

###############################################################################
# Colors and Formatting
###############################################################################

function Write-Banner {
    Clear-Host
    Write-Host ""
    Write-Host "   ██████╗ ██╗   ██╗ █████╗ ███╗   ██╗████████╗██╗   ██╗███╗   ███╗" -ForegroundColor Cyan
    Write-Host "  ██╔═══██╗██║   ██║██╔══██╗████╗  ██║╚══██╔══╝██║   ██║████╗ ████║" -ForegroundColor Cyan
    Write-Host "  ██║   ██║██║   ██║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║" -ForegroundColor Cyan
    Write-Host "  ██║▄▄ ██║██║   ██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║" -ForegroundColor Cyan
    Write-Host "  ╚██████╔╝╚██████╔╝██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║" -ForegroundColor Cyan
    Write-Host "   ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "           A D M I N   -   W I N D O W S   I N S T A L L E R" -ForegroundColor White
    Write-Host "              Enterprise Administration Interface" -ForegroundColor Blue
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Yellow
    Write-Host ""
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✓ " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "  ✗ " -ForegroundColor Red -NoNewline
    Write-Host $Message -ForegroundColor Red
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "  ⚠ " -ForegroundColor Yellow -NoNewline
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "  → " -ForegroundColor Cyan -NoNewline
    Write-Host $Message
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  $Message" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
}

###############################################################################
# Admin Check
###############################################################################

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

###############################################################################
# Python Detection and Installation
###############################################################################

function Test-Python {
    Write-Info "Checking Python installation..."

    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]

            if ($major -ge 3 -and $minor -ge 9) {
                Write-Success "Python $($matches[1]).$($matches[2]).$($matches[3]) (OK)"
                return $true
            } else {
                Write-Warning-Custom "Python $($matches[1]).$($matches[2]).$($matches[3]) (Need 3.9+)"
                return $false
            }
        }
    } catch {
        Write-Error-Custom "Python not found"
        return $false
    }
}

function Install-Python {
    Write-Host ""
    Write-Host "Python 3.9+ is required but not found." -ForegroundColor Yellow

    $response = Read-Host "Would you like to download and install Python now? (Y/N)"

    if ($response -notmatch '^[Yy]') {
        Write-Error-Custom "Installation cancelled."
        exit 1
    }

    Write-Info "Downloading Python installer..."

    $pythonUrl = "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"

    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath

        Write-Info "Installing Python (this may take a few minutes)..."
        Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1" -Wait

        # Refresh environment variables
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

        Write-Success "Python installed successfully"
        Remove-Item $installerPath -Force

    } catch {
        Write-Error-Custom "Failed to install Python: $_"
        exit 1
    }
}

function Test-Git {
    Write-Info "Checking Git installation..."

    try {
        $gitVersion = git --version 2>&1
        if ($gitVersion -match "git version (.+)") {
            Write-Success "Git $($matches[1]) (OK)"
            return $true
        }
    } catch {
        Write-Warning-Custom "Git not found (optional)"
        return $false
    }
}

function Test-Docker {
    Write-Info "Checking Docker installation..."

    try {
        $dockerVersion = docker --version 2>&1
        docker ps 2>&1 | Out-Null

        if ($LASTEXITCODE -eq 0) {
            if ($dockerVersion -match "Docker version (.+),") {
                Write-Success "Docker $($matches[1]) (running)"
                return $true
            }
        } else {
            Write-Warning-Custom "Docker (installed but not running)"
            return $false
        }
    } catch {
        Write-Warning-Custom "Docker not found (optional)"
        return $false
    }
}

function Test-Ports {
    Write-Info "Checking port availability..."

    $ports = @(8000, 5432, 6379)

    foreach ($port in $ports) {
        $tcpConnection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue

        if ($tcpConnection) {
            Write-Warning-Custom "Port $port in use"
        } else {
            Write-Success "Port $port available"
        }
    }
}

###############################################################################
# System Verification
###############################################################################

function Test-System {
    Write-Step "STEP 1: System Verification"

    Write-Info "Operating System: Windows $([Environment]::OSVersion.Version.ToString())"
    Write-Info "Architecture: $([Environment]::Is64BitOperatingSystem ? '64-bit' : '32-bit')"
    Write-Host ""

    $pythonOk = Test-Python
    if (-not $pythonOk) {
        Install-Python
    }

    Test-Git
    Test-Docker
    Test-Ports

    Write-Host ""
    Write-Success "System verification complete!"
    Start-Sleep -Seconds 1
}

###############################################################################
# Installation Menu
###############################################################################

function Show-Menu {
    Write-Step "STEP 2: Installation Method"

    Write-Host "Choose installation method:" -ForegroundColor White
    Write-Host ""
    Write-Host "  1) " -ForegroundColor Cyan -NoNewline
    Write-Host "Interactive Installer " -NoNewline
    Write-Host "(Recommended)" -ForegroundColor Green
    Write-Host "     Full wizard with step-by-step configuration"
    Write-Host ""
    Write-Host "  2) " -ForegroundColor Cyan -NoNewline
    Write-Host "Quick Install"
    Write-Host "     Auto-install with default settings (SQLite, dev mode)"
    Write-Host ""
    Write-Host "  3) " -ForegroundColor Cyan -NoNewline
    Write-Host "Docker Compose"
    Write-Host "     Full stack with PostgreSQL and Redis containers"
    Write-Host ""
    Write-Host "  4) " -ForegroundColor Cyan -NoNewline
    Write-Host "Manual Setup"
    Write-Host "     Install dependencies only, configure manually"
    Write-Host ""
    Write-Host "  Q) Quit"
    Write-Host ""
}

###############################################################################
# Installation Methods
###############################################################################

function Start-InteractiveInstall {
    Write-Step "Interactive Installation"

    Write-Info "Launching interactive installer..."
    Write-Host ""

    # Install Rich if needed
    try {
        python -c "import rich" 2>&1 | Out-Null
    } catch {
        Write-Info "Installing Rich terminal library..."
        python -m pip install rich --quiet
    }

    # Run Python installer
    python install.py
}

function Start-QuickInstall {
    Write-Step "Quick Installation"

    # Install dependencies
    Write-Info "Installing Python dependencies..."
    Set-Location quantum_admin
    python -m pip install -r requirements.txt --quiet
    Set-Location ..

    # Generate secret key
    $secretKey = -join ((48..57) + (97..102) | Get-Random -Count 64 | ForEach-Object {[char]$_})

    # Create .env file
    Write-Info "Creating configuration file..."
    @"
DATABASE_URL=sqlite:///quantum_admin.db
JWT_SECRET_KEY=$secretKey
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@quantum.local
REDIS_ENABLED=false
DEBUG=true
"@ | Out-File -FilePath ".env" -Encoding utf8

    Write-Host ""
    Write-Success "Quick installation complete!"
    Show-Completion
}

function Start-DockerInstall {
    Write-Step "Docker Compose Installation"

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error-Custom "Docker not found. Please install Docker Desktop first."
        return
    }

    Write-Info "Starting Docker Compose stack..."
    docker-compose up -d

    Write-Host ""
    Write-Success "Docker stack started!"
    Write-Host ""
    Write-Host "Services running:" -ForegroundColor White
    docker-compose ps

    Show-Completion
}

function Start-ManualInstall {
    Write-Step "Manual Installation"

    Write-Info "Installing Python dependencies..."
    Set-Location quantum_admin
    python -m pip install -r requirements.txt
    Set-Location ..

    Write-Host ""
    Write-Success "Dependencies installed!"
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor White
    Write-Host "  1. Copy .env.example to .env"
    Write-Host "  2. Edit .env with your configuration"
    Write-Host "  3. Run: python quantum-cli.py start"
}

###############################################################################
# Completion
###############################################################################

function Show-Completion {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║                                                                   ║" -ForegroundColor Green
    Write-Host "║               🎉  INSTALLATION COMPLETE!  🎉                     ║" -ForegroundColor Green
    Write-Host "║                                                                   ║" -ForegroundColor Green
    Write-Host "╚═══════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""

    Write-Host "Next Steps:" -ForegroundColor White
    Write-Host ""
    Write-Host "  1. Start the server:" -ForegroundColor Cyan
    Write-Host "     python quantum-cli.py start" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  2. Access the admin interface:" -ForegroundColor Cyan
    Write-Host "     http://localhost:8000/static/login.html" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  3. Default credentials:" -ForegroundColor Cyan
    Write-Host "     Username: admin" -ForegroundColor Yellow
    Write-Host "     Password: admin123" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor White
    Write-Host ""
    Write-Host "  python quantum-cli.py status   - Check server status" -ForegroundColor Cyan
    Write-Host "  python quantum-cli.py logs     - View logs" -ForegroundColor Cyan
    Write-Host "  python quantum-cli.py stop     - Stop server" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Documentation:" -ForegroundColor White
    Write-Host "  http://localhost:8000/docs     - API Documentation" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Thank you for choosing Quantum Admin!" -ForegroundColor Blue
    Write-Host ""
}

###############################################################################
# Main
###############################################################################

function Main {
    Write-Banner

    Write-Host "Welcome to Quantum Admin Installer!" -ForegroundColor White
    Write-Host ""
    Write-Host "This script will help you install and configure Quantum Admin."
    Write-Host ""

    # Check admin privileges
    if (-not (Test-Administrator)) {
        Write-Warning-Custom "Not running as Administrator. Some features may be limited."
        Write-Host ""
    }

    $response = Read-Host "Ready to begin? (Y/N)"

    if ($response -notmatch '^[Yy]') {
        Write-Host ""
        Write-Host "Installation cancelled." -ForegroundColor Yellow
        exit 0
    }

    Test-System

    while ($true) {
        Show-Menu
        $choice = Read-Host "Select option [1-4, Q]"

        switch ($choice.ToUpper()) {
            "1" {
                Start-InteractiveInstall
                break
            }
            "2" {
                Start-QuickInstall
                break
            }
            "3" {
                Start-DockerInstall
                break
            }
            "4" {
                Start-ManualInstall
                break
            }
            "Q" {
                Write-Host ""
                Write-Host "Installation cancelled." -ForegroundColor Yellow
                exit 0
            }
            default {
                Write-Host ""
                Write-Error-Custom "Invalid option. Please try again."
                Start-Sleep -Seconds 1
            }
        }
    }
}

# Run main function
try {
    Main
} catch {
    Write-Host ""
    Write-Error-Custom "Installation failed: $_"
    Write-Host ""
    Write-Host "Please report this issue to: https://github.com/quantum/admin/issues" -ForegroundColor Yellow
    exit 1
}
