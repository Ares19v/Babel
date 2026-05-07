@echo off
setlocal EnableDelayedExpansion

title Babel — Installation
color 0A

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║          BABEL — Installation Script            ║
echo  ║     Real-Time Multilingual Translator           ║
echo  ╚══════════════════════════════════════════════════╝
echo.

set "ROOT=%~dp0"
set "SERVER=%ROOT%server"
set "CLIENT=%ROOT%client"
set "VENV=%SERVER%\.venv"
set ERRORS=0

:: ── Check Python ─────────────────────────────────────────────────────────────
echo  [1/5] Checking Python 3.10+...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from https://python.org
    set /a ERRORS+=1
    goto :end
)
for /f "tokens=2 delims= " %%V in ('python --version 2^>^&1') do set PY_VER=%%V
echo  [OK] Python !PY_VER!

:: ── Check Node ───────────────────────────────────────────────────────────────
echo  [2/5] Checking Node.js 18+...
node --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Node.js not found. Install from https://nodejs.org
    set /a ERRORS+=1
    goto :end
)
for /f %%V in ('node --version') do set NODE_VER=%%V
echo  [OK] Node !NODE_VER!

:: ── Check ffmpeg ─────────────────────────────────────────────────────────────
echo  [3/5] Checking ffmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo  [WARN] ffmpeg not found — file upload will not work.
    echo         Install from: https://ffmpeg.org/download.html
    echo         Then add to PATH and re-run this script.
    echo.
) else (
    echo  [OK] ffmpeg found
)

:: ── Python venv & packages ───────────────────────────────────────────────────
echo  [4/5] Installing Python backend dependencies...
if not exist "%VENV%" (
    echo       Creating virtual environment...
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo  [ERROR] Failed to create venv.
        set /a ERRORS+=1
        goto :end
    )
)
echo       Installing packages (this may take 2-5 minutes)...
"%VENV%\Scripts\pip" install --quiet --upgrade pip
"%VENV%\Scripts\pip" install --quiet -r "%SERVER%\requirements.txt"
if errorlevel 1 (
    echo  [ERROR] pip install failed.
    set /a ERRORS+=1
    goto :end
)
echo  [OK] Python dependencies installed

:: ── Node packages ────────────────────────────────────────────────────────────
echo  [5/5] Installing frontend dependencies...
cd /d "%CLIENT%"
call npm install --silent
if errorlevel 1 (
    echo  [ERROR] npm install failed.
    set /a ERRORS+=1
    goto :end
)
echo  [OK] Node dependencies installed

:end
echo.
if !ERRORS! EQU 0 (
    echo  ╔══════════════════════════════════════════════════╗
    echo  ║  ✓ Installation complete!                       ║
    echo  ║    Run Run_Project.bat to start Babel.          ║
    echo  ╚══════════════════════════════════════════════════╝
) else (
    echo  ╔══════════════════════════════════════════════════╗
    echo  ║  ✗ Installation finished with errors.           ║
    echo  ║    Fix the errors above and re-run.             ║
    echo  ╚══════════════════════════════════════════════════╝
)
echo.
pause
