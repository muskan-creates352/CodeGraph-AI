@echo off
title Stop CodeGraph AI
echo Stopping CodeGraph AI background services...

:: Kill processes on port 8001 (Backend) and port 5173 (Frontend)
powershell -Command "Get-NetTCPConnection -LocalPort 8001, 5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [OK] CodeGraph AI backend and frontend stopped safely.
echo.
echo Note: FalkorDB container is left running for fast reuse.
echo (To stop FalkorDB as well, run: docker stop falkordb-server)
echo.
pause
