@echo off
cd /d "%~dp0scanner"
echo [%time%] Starting backend... > "%~dp0backend.log"

if not exist ".venv\Scripts\python.exe" (
    echo [%time%] Creating virtual environment... >> "%~dp0backend.log" 2>&1
    python -m venv .venv >> "%~dp0backend.log" 2>&1
)

REM NOTE: we call the venv's python.exe directly instead of running activate.bat.
REM Activating would prepend .venv\Scripts to PATH, and pip's httpx package ships
REM a broken "httpx" CLI stub that would shadow the real ProjectDiscovery httpx
REM recon tool used by the scan pipelines.
".venv\Scripts\python.exe" -m pip install -r requirements.txt >> "%~dp0backend.log" 2>&1
echo [%time%] pip done, launching uvicorn... >> "%~dp0backend.log" 2>&1
REM NOTE: no --reload. uvicorn's StatReload does not reliably restart the worker
REM on Windows here, and a stale worker runs on a Selector event loop where
REM asyncio subprocesses (every scan tool) fail. Plain run keeps the Proactor loop.
".venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 >> "%~dp0backend.log" 2>&1
echo [%time%] uvicorn exited. >> "%~dp0backend.log" 2>&1
pause
