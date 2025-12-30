@echo off
echo ========================================
echo Text2SQL Docker Setup
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env file...
    copy .env.example .env
    echo.
    echo Please edit .env and add your OPENAI_API_KEY
    echo Then run this script again.
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Building Docker images...
docker-compose build

echo.
echo Starting services...
docker-compose up -d

echo.
echo Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

echo.
echo ========================================
echo Services are running!
echo ========================================
echo Frontend:  http://localhost:3000
echo Backend:   http://localhost:8000
echo API Docs:  http://localhost:8000/docs
echo Qdrant:    http://localhost:6333/dashboard
echo ========================================
echo.
echo To view logs: docker-compose logs -f
echo To stop:      docker-compose down
echo.
pause
