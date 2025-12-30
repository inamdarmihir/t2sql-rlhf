@echo off
echo Starting Text2SQL Development Servers...
echo.

REM Check if Qdrant is running
docker ps | findstr qdrant >nul
if errorlevel 1 (
    echo Starting Qdrant...
    docker run -d -p 6333:6333 -p 6334:6334 --name qdrant qdrant/qdrant
    timeout /t 5 /nobreak >nul
)

echo Qdrant: Running on port 6333
echo.

REM Start backend in new window
echo Starting Backend API...
start "Text2SQL Backend" cmd /k "cd backend && python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo Starting Frontend UI...
start "Text2SQL Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo Services Starting...
echo ========================================
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo Qdrant:   http://localhost:6333
echo ========================================
echo.
echo Press any key to open browser...
pause >nul
start http://localhost:3000
