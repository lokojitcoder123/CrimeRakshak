@echo off
setlocal enabledelayedexpansion
:: ========================================================
::   CrimeRakshak - START EVERYTHING (one click)
::   Starts database, backend and frontend. Runs first-time
::   setup automatically if it hasn't been done yet.
:: ========================================================
echo ========================================================
echo            CrimeRakshak - Starting all services
echo ========================================================
echo.

cd /d "%~dp0"

:: --- 1. Prerequisites ---
:: --- Check Python ---
set PYTHON_CMD=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
        echo [INFO] Python command not found in PATH, fallback to 'py' launcher.
    ) else (
        echo [ERROR] Python is not installed or not in PATH.
        pause
        exit /b 1
    )
)

:: --- Check Docker ---
docker info >nul 2>&1
if %errorlevel% equ 0 goto docker_ok

echo [WARNING] Docker is not running.
echo [INFO] Attempting to launch Docker Desktop automatically...
if not exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
    echo [ERROR] Docker Desktop is not running and was not found in the default path.
    echo Please start Docker Desktop manually and rerun this script.
    pause
    exit /b 1
)

start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo [INFO] Waiting for Docker to start (this may take up to a minute)...
set DOCKER_OK=0
for /L %%i in (1,1,30) do (
    if !DOCKER_OK! equ 0 (
        docker info >nul 2>&1
        if !errorlevel! equ 0 (
            set DOCKER_OK=1
        ) else (
            timeout /t 3 >nul
        )
    )
)

if !DOCKER_OK! equ 0 (
    echo [ERROR] Docker did not start in time. Please start Docker Desktop manually.
    pause
    exit /b 1
)

:docker_ok


:: --- 1b. Port Cleanup ---
echo [INFO] Stopping any existing instances running on ports 8000 or 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo [INFO] Stopping backend process with PID %%a...
    taskkill /f /pid %%a
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    echo [INFO] Stopping frontend process with PID %%a...
    taskkill /f /pid %%a
)
:: Fallback to make absolutely sure everything is terminated
taskkill /f /im uvicorn.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1


:: --- 2. Env file ---
if not exist backend\.env (
    if exist .env.example (
        echo [INFO] Creating backend\.env from .env.example...
        copy .env.example backend\.env >nul
        echo [WARNING] Set GEMINI_API_KEY in backend\.env before using the AI chat.
    )
)

:: --- 3. Start PostgreSQL only (Neo4j is not used; saves memory) ---
echo [INFO] Starting PostgreSQL database...
docker compose up -d postgres
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start PostgreSQL container.
    pause
    exit /b 1
)

echo [INFO] Waiting for PostgreSQL to be ready...
set PG_OK=0
for /L %%i in (1,1,20) do (
    docker exec crimerakshak-postgres pg_isready -U user -d crimerakshak >nul 2>&1
    if !errorlevel! equ 0 (
        set PG_OK=1
        goto pg_ready
    )
    timeout /t 2 >nul
)
:pg_ready
if !PG_OK! equ 0 (
    echo [WARNING] PostgreSQL did not report ready in time; continuing anyway.
) else (
    echo [SUCCESS] PostgreSQL is ready.
)

:: --- 4. Python virtual environment ---
if not exist backend\venv\Scripts\python.exe (
    echo [INFO] Creating Python virtual environment...
    %PYTHON_CMD% -m venv backend\venv
    echo [INFO] Installing backend dependencies (first time, may take a while)...
    backend\venv\Scripts\python.exe -m pip install --upgrade pip >nul
    backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install backend dependencies.
        pause
        exit /b 1
    )
)

:: --- 5. Initialize database (idempotent: safe to run every time) ---
echo [INFO] Ensuring database schema, migrations and seed data...
docker exec -i crimerakshak-postgres psql -U user -d crimerakshak < db\schema.sql >nul 2>&1
cd backend
venv\Scripts\python.exe -m alembic upgrade head
venv\Scripts\python.exe -m app.seed
echo [INFO] Building CSV analytics database (DuckDB)...
venv\Scripts\python.exe -m app.chat.data.loader
cd ..

:: --- 6. Frontend dependencies ---
node --version >nul 2>&1
set NODE_READY=%errorlevel%
if %NODE_READY% equ 0 (
    if not exist frontend\node_modules (
        echo [INFO] Installing frontend dependencies (first time)...
        cd frontend
        call npm install
        cd ..
    )
)

:: --- 7. Launch services ---
:: Launched via helper scripts to avoid nested-quote issues with the
:: space in the project path ("crime ai").
echo [INFO] Launching Backend API...
start "CrimeRakshak Backend API" "%~dp0_run-backend.bat"

if %NODE_READY% equ 0 (
    echo [INFO] Launching Frontend UI...
    start "CrimeRakshak Frontend UI" "%~dp0_run-frontend.bat"
) else (
    echo [WARNING] Node.js not found - skipping frontend. Install Node.js to run the UI.
)

echo.
echo ========================================================
echo             CrimeRakshak is starting!
echo ========================================================
if %NODE_READY% equ 0 (
    echo   [Frontend UI]  - http://localhost:3000/ai-assistant
) else (
    echo   [Frontend UI]  - NOT RUNNING (Node.js was not found)
)
echo   [Backend API]  - http://localhost:8000
echo   [API Docs]     - http://localhost:8000/docs
echo   [Login]        - username: admin
echo ========================================================
if %NODE_READY% neq 0 (
    echo [WARNING] Node.js was not found. Please install Node.js (v18+) to run the frontend.
    echo.
)
echo Servers run in their own windows. Close those windows to stop them.
echo To stop the database:  docker compose down
echo.
pause
