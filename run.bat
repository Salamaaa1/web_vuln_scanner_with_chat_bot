@echo off
REM ============================================================
REM  Auto-Pentest — one-click launcher (Windows)
REM  Pulls the 4 images from Docker Hub, wires them together,
REM  and starts the whole stack. Just double-click this file
REM  (or run it in a terminal). Requires Docker Desktop running.
REM ============================================================
setlocal
REM Always work from the folder this script lives in, so ".env" is found even
REM when the file is double-clicked from another directory.
cd /d "%~dp0"

set NET=pentest-net
set MONGO=salamaaa11/auto-pentest-mongodb:latest
set REDIS=salamaaa11/auto-pentest-redis:latest
set SCANNER=salamaaa11/auto-pentest-scanner:latest
set FRONTEND=salamaaa11/auto-pentest-frontend:latest

echo [1/6] Pulling images from Docker Hub...
docker pull %MONGO%    || goto :err
docker pull %REDIS%    || goto :err
docker pull %SCANNER%  || goto :err
docker pull %FRONTEND% || goto :err

echo [2/6] Creating private network...
docker network create %NET% 2>nul

echo [3/6] Removing any previous containers...
docker rm -f pentest-mongodb pentest-redis pentest-scanner pentest-frontend 2>nul

echo [4/6] Starting MongoDB and Redis...
docker run -d --name pentest-mongodb --network %NET% -p 27017:27017 -v pentest_mongo_data:/data/db --restart unless-stopped %MONGO% || goto :err
docker run -d --name pentest-redis   --network %NET% -p 6379:6379  -v pentest_redis_data:/data --restart unless-stopped %REDIS% || goto :err

echo [5/6] Waiting for MongoDB to be ready...
:waitmongo
docker exec pentest-mongodb mongosh --quiet --eval "db.adminCommand('ping')" >nul 2>&1
if errorlevel 1 (
  timeout /t 2 /nobreak >nul
  goto waitmongo
)

REM Load the AI key from .env if present (optional — enables the Assistant IA tab).
REM "eol=#" skips comment lines in the .env file.
set NVIDIA_API_KEY=
set NVIDIA_MODEL=deepseek-ai/deepseek-v4-flash
if exist .env (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do (
    if /i "%%A"=="NVIDIA_API_KEY" set NVIDIA_API_KEY=%%B
    if /i "%%A"=="NVIDIA_MODEL" set NVIDIA_MODEL=%%B
  )
)
if defined NVIDIA_API_KEY (
  set AI_STATUS=enabled
) else (
  set AI_STATUS=disabled ^(add NVIDIA_API_KEY to .env^)
)

echo [6/6] Starting scanner API and frontend...
docker run -d --name pentest-scanner --network %NET% -p 8000:8000 ^
  -e MONGODB_URL=mongodb://pentest-mongodb:27017 ^
  -e DATABASE_NAME=scanner ^
  -e REDIS_URL=redis://pentest-redis:6379 ^
  -e NMAP_TOP_PORTS=1000 -e NMAP_TIMING=-T4 ^
  -e NVIDIA_API_KEY=%NVIDIA_API_KEY% ^
  -e NVIDIA_MODEL=%NVIDIA_MODEL% ^
  --restart unless-stopped %SCANNER% || goto :err
docker run -d --name pentest-frontend --network %NET% -p 3000:3000 --restart unless-stopped %FRONTEND% || goto :err

echo.
echo ============================================================
echo   Auto-Pentest is starting up.
echo   Open http://localhost:3000 in your browser.
echo   (The scanner API is on http://localhost:8000)
echo   Assistant IA : %AI_STATUS%
echo   To stop everything, run stop.bat
echo ============================================================
endlocal
exit /b 0

:err
echo.
echo ERROR: a step failed. Is Docker Desktop running?
endlocal
exit /b 1
