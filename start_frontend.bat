@echo off
cd /d "%~dp0frontend"
echo [%time%] Installing npm packages... > "%~dp0frontend.log"
npm install >> "%~dp0frontend.log" 2>&1
echo [%time%] Starting Next.js on http://localhost:3000 ... >> "%~dp0frontend.log" 2>&1
npm run dev >> "%~dp0frontend.log" 2>&1
echo [%time%] Next.js exited. >> "%~dp0frontend.log" 2>&1
pause
