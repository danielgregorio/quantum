@echo off
REM Quantum Admin - Windows Batch Installer Launcher
REM This script launches the PowerShell installer

echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║                                                                   ║
echo ║                     Quantum Admin Installer                      ║
echo ║                                                                   ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.

REM Check PowerShell version
powershell -Command "if ($PSVersionTable.PSVersion.Major -lt 5) { Write-Host 'PowerShell 5.1+ required' -ForegroundColor Red; exit 1 }"
if errorlevel 1 (
    echo ERROR: PowerShell 5.1 or higher is required
    echo Please update PowerShell from: https://aka.ms/powershell
    pause
    exit /b 1
)

echo Launching PowerShell installer...
echo.

REM Run PowerShell script with execution policy bypass
powershell -ExecutionPolicy Bypass -File "%~dp0setup.ps1"

if errorlevel 1 (
    echo.
    echo ERROR: Installation failed
    pause
    exit /b 1
)

echo.
pause
