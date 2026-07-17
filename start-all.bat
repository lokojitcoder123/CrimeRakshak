@echo off
title CrimeRakshak - Project Startup Control Center
cls
echo ======================================================================
echo           CRIMERAKSHAK - SYSTEM STARTUP CONTROL CENTER
echo ======================================================================
echo.

:menu
echo Choose an option to proceed:
echo [1] Quick Start (Start databases and launch servers)
echo [2] Full Setup + Run (Start databases, init DBs, ingest data, seed, and launch servers)
echo [3] Database Setup Only (Init database schemas, run ingestion and seed)
echo [4] Start Application Servers Only (FastAPI backend + Next.js frontend)
echo [5] Stop Databases (docker-compose down)
echo [6] Exit
echo.
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto quickstart
if "%choice%"=="2" goto fullsetup
if "%choice%"=="3" goto dbsetup
if "%choice%"=="4" goto startservers
if "%choice%"=="5" goto stopdb
if "%choice%"=="6" goto exit
echo Invalid choice. Please try again.
echo.
goto menu

:quickstart
echo.
echo === Starting Databases via Docker Compose ===
docker compose up -d
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Failed to run 'docker compose up -d'. Ensure Docker Desktop is running.
    pause
)
goto startservers

:fullsetup
echo.
echo === Starting Databases via Docker Compose ===
docker compose up -d
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to run 'docker compose up -d'. Ensure Docker Desktop is running.
    pause
    goto menu
)

echo.
echo === Initializing Databases ===
echo Running schema migrations, cypher constraints, and seeds...
cd /d "%~dp0backend"
call venv\Scripts\activate.bat
python initialize_db.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Database initialization failed.
    cd /d "%~dp0"
    pause
    goto menu
)

echo.
echo === Seeding RBAC / Initial Superuser ===
python -m app.seed
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Seeding failed.
    cd /d "%~dp0"
    pause
    goto menu
)

echo.
echo === Running Data Ingestion Pipeline ===
python ingest.py
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Data ingestion pipeline failed. Moving forward...
)

cd /d "%~dp0"
goto startservers

:dbsetup
echo.
echo === Initializing Databases ===
cd /d "%~dp0backend"
call venv\Scripts\activate.bat
python initialize_db.py
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Database initialization failed.
    cd /d "%~dp0"
    pause
    goto menu
)

echo.
echo === Seeding RBAC / Initial Superuser ===
python -m app.seed
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Seeding failed.
    cd /d "%~dp0"
    pause
    goto menu
)

echo.
echo === Running Data Ingestion Pipeline ===
python ingest.py
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Data ingestion pipeline failed.
)
cd /d "%~dp0"
echo.
echo Database setup completed successfully!
pause
goto menu

:startservers
echo.
echo === Launching FastAPI Backend ===
start "CrimeRakshak Backend" cmd /c "%~dp0_run-backend.bat"

echo === Launching Next.js Frontend ===
start "CrimeRakshak Frontend" cmd /c "%~dp0_run-frontend.bat"

echo.
echo CrimeRakshak is starting up in separate terminal windows!
echo - Backend: http://localhost:8000
echo - Frontend: http://localhost:3000
echo.
echo Feel free to close this menu.
pause
goto menu

:stopdb
echo.
echo === Stopping Docker Databases ===
docker compose down
echo Databases stopped.
pause
goto menu

:exit
exit
