@echo off
setlocal EnableDelayedExpansion

title Babel — Real-Time Translator
color 0B

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║        BABEL — Real-Time Translator             ║
echo  ║     Powered by Whisper large-v3-turbo           ║
echo  ╚══════════════════════════════════════════════════╝
echo.

set "ROOT=%~dp0"
set "SERVER=%ROOT%server"
set "CLIENT=%ROOT%client"
set "VENV=%SERVER%\.venv"

:: ── Dependency checks ─────────────────────────────────────────────────────────
set USE_VENV=0
set "UVICORN_CMD=python -m uvicorn"
if exist "%VENV%\Scripts\activate.bat" (
    set USE_VENV=1
    set "UVICORN_CMD=.venv\Scripts\uvicorn"
)

if not exist "%CLIENT%\node_modules" (
    echo  [ERROR] Node modules not installed.
    echo          Please run INSTALL.bat first.
    echo.
    pause
    exit /b 1
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo  [WARN] ffmpeg not found — file upload will not work.
    echo         Install from https://ffmpeg.org and add to PATH.
    echo.
)

:: ── Start Backend ─────────────────────────────────────────────────────────────
echo  [1/2] Starting Babel backend on http://localhost:8000...
start "Babel — Backend" cmd /k "title Babel Backend && cd /d "%SERVER%" && %UVICORN_CMD% main:app --host 127.0.0.1 --port 8000"

:: Wait for backend to be ready (poll health endpoint)
echo  [wait] Waiting for backend to load model (up to 60s)...
set READY=0
for /L %%i in (1,1,30) do (
    timeout /t 2 /nobreak >nul
    curl -sf http://localhost:8000/health >nul 2>&1
    if not errorlevel 1 (
        set READY=1
        goto :backend_ready
    )
)
:backend_ready

if !READY! EQU 0 (
    echo  [WARN] Backend may still be loading. Continuing anyway...
) else (
    echo  [OK]   Backend ready!
)

:: ── Start Frontend ────────────────────────────────────────────────────────────
echo  [2/2] Starting frontend on http://localhost:5173...
start "Babel — Frontend" cmd /k "title Babel Frontend && cd /d "%CLIENT%" && npm run dev"

timeout /t 3 /nobreak >nul

:: ── Open browser ──────────────────────────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║  ✓ Babel is running!                           ║
echo  ║                                                 ║
echo  ║    App:      http://localhost:5173              ║
echo  ║    API:      http://localhost:8000              ║
echo  ║    Swagger:  http://localhost:8000/docs         ║
echo  ╚══════════════════════════════════════════════════╝
echo.
echo  Opening browser...
start http://localhost:5173

echo  Close this window or press Ctrl+C to stop watching.
echo  (The backend and frontend windows run independently.)
echo.
pause
