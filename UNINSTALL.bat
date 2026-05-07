@echo off
setlocal EnableDelayedExpansion

title Babel — Uninstall
color 0C

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║         BABEL — Uninstall Script               ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  This will remove:
echo    - server\.venv  (Python virtual environment)
echo    - client\node_modules  (Node packages)
echo.
echo  Your source code will NOT be deleted.
echo.
set /p CONFIRM=  Type YES to continue: 

if /i "!CONFIRM!" NEQ "YES" (
    echo  Cancelled.
    pause
    exit /b 0
)

echo.
echo  Removing Python venv...
if exist "%~dp0server\.venv" (
    rmdir /s /q "%~dp0server\.venv"
    echo  [OK] server\.venv removed
) else (
    echo  [SKIP] server\.venv not found
)

echo  Removing Node modules...
if exist "%~dp0client\node_modules" (
    rmdir /s /q "%~dp0client\node_modules"
    echo  [OK] client\node_modules removed
) else (
    echo  [SKIP] client\node_modules not found
)

echo.
echo  ✓ Uninstall complete.
echo.
pause
