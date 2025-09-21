@echo off
echo Starting Gear AI Platform...
echo.

echo [1/2] Starting Backend Server...
start "Gear AI Backend" cmd /k "cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Starting Frontend...
timeout /t 3 /nobreak > nul
start "Gear AI Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Gear AI Platform is starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Press any key to close this window...
pause > nul