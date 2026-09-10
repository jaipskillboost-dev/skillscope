@echo off
REM ===================================================================
REM  SkillScope - double-click to start.
REM
REM  First run sets everything up (a few minutes). Later runs are quick.
REM  Then open http://localhost:8000
REM  Press Ctrl+C in this window to stop.
REM
REM  If your MySQL password is not "springstudent", set it first:
REM      set SKILLSCOPE_DB_PASSWORD=yourpassword
REM ===================================================================
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo   Python is not installed, or not on PATH.
  echo   Install Python 3.10 or newer from python.org and tick
  echo   "Add Python to PATH" during setup.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo   First run - setting up. This takes a few minutes.
  echo.
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install --upgrade pip --quiet
  .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
  if errorlevel 1 (
    echo   Could not install the required packages. Check your connection.
    pause
    exit /b 1
  )
)

echo   Preparing the database...
.venv\Scripts\python.exe setup_db.py
if errorlevel 1 ( pause & exit /b 1 )

.venv\Scripts\python.exe manage.py migrate --noinput
if errorlevel 1 ( pause & exit /b 1 )

REM Load the demo data the first time only. Does nothing if already present.
.venv\Scripts\python.exe manage.py seed_demo

echo.
echo ==============================================
echo   SkillScope is running.
echo   Open  http://localhost:8000
echo.
echo   admin@skillscope.io      / skillscope123
echo   rekha.iyer@northline.edu / skillscope123
echo   vikram.c@northline.edu   / skillscope123
echo.
echo   Stop with Ctrl+C
echo ==============================================
echo.
.venv\Scripts\python.exe manage.py runserver 8000
