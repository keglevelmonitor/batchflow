@echo off
SETLOCAL

:: --- Variables ---
SET "PROJECT_DIR=%~dp0"
:: Remove trailing backslash if present
IF %PROJECT_DIR:~-1%==\ SET PROJECT_DIR=%PROJECT_DIR:~0,-1%

SET "VENV_DIR=%PROJECT_DIR%\venv"
SET "DATA_DIR=%USERPROFILE%\batchflow-data"
SET "SHORTCUT_PATH=%USERPROFILE%\Desktop\BatchFlow.lnk"
SET "ICON_PATH=%PROJECT_DIR%\src\assets\batchflow.png"
SET "SCRIPT_PATH=%PROJECT_DIR%\src\batchflow_main.py"

echo.
echo --- [Step 1/3] Configuring Data Directory ---
IF NOT EXIST "%DATA_DIR%" (
    mkdir "%DATA_DIR%"
    echo Created data directory: %DATA_DIR%
) ELSE (
    echo Data directory exists.
)

echo.
echo --- [Step 2/3] Setting up Python Environment ---
IF EXIST "%VENV_DIR%" (
    echo Virtual environment exists. Skipping creation.
) ELSE (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
)

echo Installing dependencies...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements.txt

IF %ERRORLEVEL% NEQ 0 (
    echo [FATAL ERROR] Dependency installation failed.
    pause
    exit /b
)

echo.
echo --- [Step 3/3] Creating Desktop Shortcut ---
:: We use PowerShell to create a proper Windows Shortcut (.lnk)
:: Note: Windows Shortcuts prefer .ico files. Pointing to .png works but might show a generic icon on the desktop file itself.
:: The app window itself WILL show the correct png icon.

set "TARGET=%VENV_DIR%\Scripts\pythonw.exe"
set "ARGS=\"%SCRIPT_PATH%\""

powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%');$s.TargetPath='%TARGET%';$s.Arguments='%ARGS%';$s.WorkingDirectory='%PROJECT_DIR%';$s.IconLocation='%ICON_PATH%';$s.Save()"

echo Shortcut created on Desktop.

echo.
echo Installation successful.
