@echo off
REM ===================================================================
REM  SkillScope - DEMO MODE
REM  Same site, but any unexpected error shows the calm SkillScope page
REM  instead of a Django traceback. Use this one on stage.
REM  Run run.bat at least once first, to do the setup.
REM ===================================================================
cd /d "%~dp0"
set SKILLSCOPE_DEBUG=0

if not exist ".venv\Scripts\python.exe" (
  echo   Not set up yet - run run.bat once first.
  pause
  exit /b 1
)

echo.
echo ==============================================
echo   SkillScope - DEMO MODE
echo   Open  http://localhost:8000
echo   Stop with Ctrl+C
echo ==============================================
echo.
.venv\Scripts\python.exe manage.py runserver 8000
