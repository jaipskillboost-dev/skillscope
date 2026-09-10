@echo off
REM ===================================================================
REM  SkillScope - main menu
REM  Double-click this file. Start with option 1 the first time.
REM ===================================================================
setlocal
cd /d "%~dp0"
title SkillScope

set PY=.venv\Scripts\python.exe

:menu
cls
echo.
echo   ==============================================================
echo                        S K I L L S C O P E
echo                A learning and training platform
echo   ==============================================================
echo.
if exist "%PY%" (
  echo     Setup:  installed
) else (
  echo     Setup:  NOT DONE YET  -  choose option 1 first
)
echo.
echo     1.  Setup  -  check and install everything
echo     2.  Start SkillScope           ^(for building^)
echo     3.  Start SkillScope           ^(for the demo^)
echo     4.  Check status
echo     5.  Reset the demo data
echo     6.  Run the tests
echo     7.  Exit
echo.
echo   --------------------------------------------------------------
set "choice="
set /p choice=  Type a number and press Enter:

if "%choice%"=="1" goto setup
if "%choice%"=="2" goto start_dev
if "%choice%"=="3" goto start_demo
if "%choice%"=="4" goto status
if "%choice%"=="5" goto reset
if "%choice%"=="6" goto tests
if "%choice%"=="7" goto end
goto menu


REM ===================================================================
:setup
cls
echo.
echo   SETUP
echo   =====
echo.
echo   This checks everything SkillScope needs and installs what is
echo   missing. Safe to run again at any time - it never deletes
echo   your data.
echo.

echo   [1/4] Looking for Python...
where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo         Python is not installed, or not on PATH.
  echo.
  echo         Install Python 3.10 or newer from python.org
  echo         During install, tick "Add Python to PATH".
  echo.
  pause
  goto menu
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo         Found Python %%v

echo.
echo   [2/4] Preparing the virtual environment...
if exist "%PY%" (
  echo         Already there.
) else (
  echo         Creating it - this takes a minute...
  python -m venv .venv
  if errorlevel 1 (
    echo         Could not create it. Is Python installed properly?
    pause
    goto menu
  )
  echo         Created.
)

echo.
echo   [3/4] Installing the required packages...
"%PY%" -m pip install --upgrade pip --quiet
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo         Could not install the packages.
  echo         Check your internet connection and try again.
  pause
  goto menu
)

echo.
echo   [4/4] Checking the database and demo data...
echo.
"%PY%" check_setup.py --fix

echo.
echo   --------------------------------------------------------------
pause
goto menu


REM ===================================================================
:start_dev
if not exist "%PY%" ( call :notready & goto menu )
cls
echo.
echo   ==============================================================
echo     SkillScope is starting  -  BUILDING MODE
echo.
echo     Open   http://localhost:8000
echo.
echo     Errors show full technical detail, which helps while you
echo     are working. Use option 3 for the demo instead.
echo.
echo     Stop with Ctrl+C
echo   ==============================================================
echo.
set SKILLSCOPE_DEBUG=1
"%PY%" manage.py runserver 8000
pause
goto menu


REM ===================================================================
:start_demo
if not exist "%PY%" ( call :notready & goto menu )
cls
echo.
echo   ==============================================================
echo     SkillScope is starting  -  DEMO MODE
echo.
echo     Open   http://localhost:8000
echo.
echo     Sign in with any of these  ^(password: skillscope123^)
echo       admin@skillscope.io         Platform admin
echo       rekha.iyer@northline.edu    Institute admin
echo       vikram.c@northline.edu      Trainer
echo.
echo     If anything goes wrong it shows a calm SkillScope page,
echo     never a technical error screen.
echo.
echo     Stop with Ctrl+C
echo   ==============================================================
echo.
set SKILLSCOPE_DEBUG=0
"%PY%" manage.py runserver 8000
pause
goto menu


REM ===================================================================
:status
if not exist "%PY%" ( call :notready & goto menu )
cls
echo.
echo   STATUS
echo   ======
"%PY%" check_setup.py
echo.
pause
goto menu


REM ===================================================================
:reset
if not exist "%PY%" ( call :notready & goto menu )
cls
echo.
echo   RESET THE DEMO DATA
echo   ===================
echo.
echo   This DELETES everything currently in SkillScope - all accounts,
echo   courses, uploads and certificates - and puts back the original
echo   demo data.
echo.
echo   Use it to get a clean slate before presenting.
echo.
set "sure="
set /p sure=  Type YES to continue, or press Enter to cancel:
if /i not "%sure%"=="YES" (
  echo.
  echo   Cancelled. Nothing was changed.
  pause
  goto menu
)
echo.
"%PY%" manage.py seed_demo --force
echo.
pause
goto menu


REM ===================================================================
:tests
if not exist "%PY%" ( call :notready & goto menu )
cls
echo.
echo   RUNNING THE TESTS
echo   =================
echo.
echo   These check marking, certificates, competency scoring, and that
echo   one institute cannot see another's data.
echo.
"%PY%" manage.py test
echo.
pause
goto menu


REM ===================================================================
:notready
echo.
echo   Not set up yet. Choose option 1 first.
echo.
pause
exit /b


:end
endlocal
exit /b 0
