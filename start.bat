@echo off
echo.
echo  ╔══════════════════════════════════════╗
echo  ║       BABEL — Real-Time Translator   ║
echo  ╚══════════════════════════════════════╝
echo.

REM Check for ffmpeg
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo  [!] WARNING: ffmpeg not found in PATH.
    echo      File upload will not work.
    echo      Install from: https://ffmpeg.org/download.html
    echo.
)

echo  [1/2] Starting Babel server on http://localhost:8000 ...
start "Babel Server" cmd /k "cd /d %~dp0server && .venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo  [2/2] Starting React frontend on http://localhost:5173 ...
start "Babel Client" cmd /k "cd /d %~dp0client && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo  ✓ Babel is running!
echo    Server:   http://localhost:8000
echo    Frontend: http://localhost:5173
echo    API docs: http://localhost:8000/docs
echo.
echo  Press any key to open in browser...
pause >nul
start http://localhost:5173
