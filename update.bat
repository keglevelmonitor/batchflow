@echo off
SETLOCAL

SET "PROJECT_DIR=%~dp0"
IF %PROJECT_DIR:~-1%==\ SET PROJECT_DIR=%PROJECT_DIR:~0,-1%
SET "VENV_PYTHON=%PROJECT_DIR%\venv\Scripts\python.exe"

echo --- BatchFlow Update Script ---
echo Starting update in %PROJECT_DIR%

:: 1. Git Pull
echo.
echo [1/2] Pulling latest code...
git pull
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Git pull failed.
    pause
    exit /b
)

:: 2. Update Dependencies
echo.
echo [2/2] Updating dependencies...
IF NOT EXIST "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found. Please run install.bat first.
    pause
    exit /b
)

"%VENV_PYTHON%" -m pip install -r requirements.txt

echo.
echo --- Update Complete ---
pause
