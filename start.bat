@echo off
title Multimodal AI Chatbot Launcher
echo ========================================================
echo         Starting Multimodal AI Chatbot
echo ========================================================
echo.

cd /d "%~dp0backend"
echo Starting Backend API on http://localhost:8000 ...
start "Chatbot Backend (FastAPI)" cmd /k ".\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

cd /d "%~dp0frontend"
echo Starting Frontend UI on http://localhost:5173 ...
start "Chatbot Frontend (Vite)" cmd /k "npm run dev -- --host 127.0.0.1 --port 5173"

echo.
echo Waiting for servers to initialize...
ping 127.0.0.1 -n 4 >nul

echo Opening browser at http://localhost:5173 ...
start http://localhost:5173

echo.
echo ========================================================
echo Application is running!
echo - Frontend: http://localhost:5173
echo - Backend:  http://localhost:8000
echo - Swagger:  http://localhost:8000/docs
echo ========================================================
