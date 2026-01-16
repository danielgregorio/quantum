#!/usr/bin/env python3
"""
Build Windows Executable for Quantum Admin Installer
Creates setup.exe from install.py using PyInstaller
"""

import os
import sys
import subprocess
import platform

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        print("✓ PyInstaller found")
        return True
    except ImportError:
        print("✗ PyInstaller not found")
        return False

def install_pyinstaller():
    """Install PyInstaller"""
    print("\n→ Installing PyInstaller...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install PyInstaller")
        return False

def build_executable():
    """Build Windows executable"""
    print("\n→ Building Windows executable...")

    # PyInstaller options
    options = [
        "install.py",
        "--name=quantum-admin-setup",
        "--onefile",
        "--windowed" if platform.system() == "Windows" else "--console",
        "--icon=NONE",
        "--add-data=INSTALL.md:.",
        "--hidden-import=rich",
        "--hidden-import=rich.console",
        "--hidden-import=rich.panel",
        "--hidden-import=rich.progress",
        "--hidden-import=rich.prompt",
        "--hidden-import=rich.table",
        "--hidden-import=rich.syntax",
    ]

    try:
        subprocess.check_call([sys.executable, "-m", "PyInstaller"] + options)
        print("\n✓ Executable built successfully!")
        print("\n  Output: dist/quantum-admin-setup.exe")
        return True
    except subprocess.CalledProcessError:
        print("\n✗ Failed to build executable")
        return False

def main():
    """Main function"""
    print("=" * 70)
    print("  Quantum Admin - Windows Executable Builder")
    print("=" * 70)
    print()

    if platform.system() != "Windows":
        print("⚠ Warning: Building on non-Windows platform")
        print("  The executable will still work on Windows")
        print()

    # Check PyInstaller
    if not check_pyinstaller():
        if not install_pyinstaller():
            sys.exit(1)

    # Build
    if build_executable():
        print("\n" + "=" * 70)
        print("  Build Complete!")
        print("=" * 70)
        print()
        print("To distribute:")
        print("  1. Copy dist/quantum-admin-setup.exe to target machine")
        print("  2. Run setup.exe")
        print("  3. Follow the interactive installer")
        print()
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
