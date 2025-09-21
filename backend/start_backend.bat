@echo off
echo Starting Gear AI Backend Server...
cd /d "%~dp0"
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload