@echo off
title Concave Insights Support — Starting...
color 0A
cls

echo.
echo  ============================================================
echo   CONCAVE INSIGHTS SUPPORT TICKETING SYSTEM
echo  ============================================================
echo.

cd /d "%~dp0"

:: ── 1. Check Python ──────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python 3.11+ and add it to PATH.
    pause
    exit /b 1
)

:: ── 2. Create venv if missing ────────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo  [1/4] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo        Done.
) else (
    echo  [1/4] Virtual environment already exists. Skipping.
)

:: ── 3. Install / upgrade dependencies ────────────────────────
echo  [2/4] Installing dependencies from requirements.txt...
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
if errorlevel 1 (
    echo  [ERROR] pip install failed. Check requirements.txt and your network.
    pause
    exit /b 1
)
echo        Done.

:: ── 4. Seed database (idempotent — safe to run every time) ───
echo  [3/4] Seeding database (idempotent)...
python -m app.seed
if errorlevel 1 (
    echo  [ERROR] Seed script failed. Check database or model errors above.
    pause
    exit /b 1
)

:: ── 5. Launch server ─────────────────────────────────────────
echo.
echo  [4/4] Starting server...
echo.
echo  ============================================================
echo   Open your browser at:  http://localhost:8000
echo.
echo   Press Ctrl+C in this window to stop the server.
echo  ============================================================
echo.

start "" "http://localhost:8000"

.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo  Server stopped. Press any key to close.
pause >nul
