@echo off
SETLOCAL EnableDelayedExpansion

:: --- Configuration ---
SET "INSTALL_DIR=%USERPROFILE%\batchflow"
SET "REPO_URL=https://github.com/keglevelmonitor/batchflow.git"

TITLE BatchFlow Auto-Installer

echo ========================================
echo       BatchFlow Windows Installer
echo ========================================
echo.

:: 1. Check if Git/Python are installed
where git >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Git is not installed. Please install Git for Windows.
    pause
    exit /b
)
where python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed. Please install Python from python.org.
    echo         Make sure to check "Add Python to PATH".
    pause
    exit /b
)

:: 2. Check for existing install
IF EXIST "%INSTALL_DIR%" (
    echo Existing installation detected at:
    echo %INSTALL_DIR%
    echo.
    echo Updating existing code...
    cd /d "%INSTALL_DIR%"
    git pull
) ELSE (
    echo Cloning repository to %INSTALL_DIR%...
    git clone %REPO_URL% "%INSTALL_DIR%"
    cd /d "%INSTALL_DIR%"
)

:: 3. Run the Main Installer
echo.
echo Launching main configuration script...
call install.bat

echo.
echo ========================================
echo        Setup Complete!
echo ========================================
pause
