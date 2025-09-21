@echo off
echo Testing Gear AI Platform Connection...
echo.

echo [1/3] Testing Backend Server...
curl -s http://127.0.0.1:8000/ >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Backend is running on http://127.0.0.1:8000
    curl -s http://127.0.0.1:8000/
    echo.
) else (
    echo ✗ Backend is not running
    echo Please start backend first: cd backend && uv run uvicorn main:app --host 127.0.0.1 --port 8000
    echo.
)

echo [2/3] Testing API Endpoints...
curl -s http://127.0.0.1:8000/api/agents/available >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ API endpoints are working
    echo Available agents:
    curl -s http://127.0.0.1:8000/api/agents/available
    echo.
) else (
    echo ✗ API endpoints are not responding
    echo.
)

echo [3/3] Testing Frontend...
curl -s http://localhost:5173/ >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Frontend is running on http://localhost:5173
) else (
    echo ✗ Frontend is not running
    echo Please start frontend: cd frontend && npm run dev
)

echo.
echo Test completed!
pause