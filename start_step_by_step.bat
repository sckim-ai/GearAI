@echo off
echo ====================================
echo    Gear AI Platform Setup Guide
echo ====================================
echo.

echo Step 1: Starting Backend Server...
echo --------------------------------
echo Opening new window for backend...
start "Gear AI Backend" cmd /k "echo Starting Backend Server... && cd /d %~dp0backend && uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo Step 2: Waiting 5 seconds for backend to start...
timeout /t 5 /nobreak

echo.
echo Step 3: Testing backend connection...
curl -s http://127.0.0.1:8000/ >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Backend is running on http://127.0.0.1:8000
) else (
    echo ✗ Backend connection failed
    echo Please check the backend window for errors
    pause
    exit /b 1
)

echo.
echo Step 4: Starting Frontend Server...
echo ---------------------------------
echo Opening new window for frontend...
start "Gear AI Frontend" cmd /k "echo Starting Frontend Server... && cd /d %~dp0frontend && npm run dev"

echo.
echo Step 5: Waiting for frontend to start...
timeout /t 5 /nobreak

echo.
echo ====================================
echo    Gear AI Platform is Ready!
echo ====================================
echo.
echo ✓ Backend:  http://127.0.0.1:8000
echo ✓ Frontend: http://localhost:5173
echo ✓ API Docs: http://127.0.0.1:8000/docs
echo.
echo Open your browser and go to:
echo http://localhost:5173
echo.
echo Press any key to open the frontend automatically...
pause >nul
start http://localhost:5173
echo.
echo Setup completed! Both servers are running.
echo Close this window when you're done.
pause >nul