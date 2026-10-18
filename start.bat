@echo off
title CodeGraph AI Launcher
echo ========================================================
echo   Starting CodeGraph AI (FalkorDB + Backend + Frontend)
echo ========================================================
echo.

cd /d "C:\Users\Rani\Downloads\CODEGRAPH AI"

:: 1. Ensure Docker Desktop is running
echo [1/4] Checking Docker status...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Docker is not running. Launching Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Waiting for Docker engine to initialize (approx 15-25 seconds)...
    :wait_docker
    timeout /t 4 /nobreak >nul
    docker ps >nul 2>&1
    if %errorlevel% neq 0 (
        echo     Still waiting for Docker...
        goto wait_docker
    )
    echo [OK] Docker is now active!
) else (
    echo [OK] Docker is already running.
)

:: 2. Ensure FalkorDB container is running
echo [2/4] Starting FalkorDB database container...
docker start falkordb-server >nul 2>&1
if %errorlevel% neq 0 (
    echo Creating falkordb-server container...
    docker run -d --name falkordb-server -p 6379:6379 -v falkordb_data:/var/lib/falkordb falkordb/falkordb:latest >nul 2>&1
)
echo [OK] FalkorDB is ready on port 6379.

:: 3. Launch FastAPI Backend in background
echo [3/4] Launching FastAPI Backend on http://127.0.0.1:8001...
start "CodeGraph AI - Backend" /min cmd /c "cd /d "C:\Users\Rani\Downloads\CODEGRAPH AI" && set PYTHONPATH=backend&& backend\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8001 --reload"

:: 4. Launch React Dashboard
echo [4/4] Launching Frontend on http://localhost:5173...
start "CodeGraph AI - Frontend" /min cmd /c "cd /d "C:\Users\Rani\Downloads\CODEGRAPH AI\frontend" && npm run dev"

:: Wait 3 seconds for servers to spin up, then open browser automatically
timeout /t 3 /nobreak >nul
echo.
echo ========================================================
echo   CodeGraph AI is now LIVE!
echo   Opening http://localhost:5173 in your browser...
echo ========================================================
start http://localhost:5173

echo.
echo ========================================================
echo All services are running in background!
echo - Web Dashboard:  http://localhost:5173
echo - API Backend:    http://127.0.0.1:8001
echo - API Docs:       http://127.0.0.1:8001/docs
echo - FalkorDB Graph: localhost:6379
echo ========================================================
echo (To shut down everything, double-click stop.bat)
echo.
pause
