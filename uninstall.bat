@echo off
SETLOCAL EnableDelayedExpansion

SET "APP_DIR=%USERPROFILE%\batchflow"
SET "DATA_DIR=%USERPROFILE%\batchflow-data"
SET "SHORTCUT_PATH=%USERPROFILE%\Desktop\BatchFlow.lnk"

echo ==========================================
echo        BatchFlow Uninstaller
echo ==========================================
echo.
echo Please choose an option:
echo.
echo   [1] APP ONLY  - Deletes Application folder. Keeps data.
echo   [2] FULL WIPE - Deletes App AND Data.
echo   [3] CANCEL    - Exit.
echo.
set /p choice="Enter choice (1/2/3): "

IF "%choice%"=="1" GOTO REMOVE_APP
IF "%choice%"=="2" GOTO REMOVE_ALL
GOTO END

:REMOVE_ALL
echo.
echo Removing Data Directory...
IF EXIST "%DATA_DIR%" (
    rmdir /s /q "%DATA_DIR%"
    echo Deleted %DATA_DIR%
)

:REMOVE_APP
echo.
echo Removing Desktop Shortcut...
IF EXIST "%SHORTCUT_PATH%" del "%SHORTCUT_PATH%"

echo Removing Application Directory...
IF EXIST "%APP_DIR%" (
    :: Use a trick to remove the directory itself
    rmdir /s /q "%APP_DIR%"
    echo Deleted %APP_DIR%
)

echo.
echo ==========================================
echo      Uninstallation Complete
echo ==========================================
pause
exit /b

:END
echo Cancelled.
pause
