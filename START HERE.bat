@echo off
rem ============================================================================
rem  LOCAL AI VOICE STUDIO - LAUNCHER
rem
rem  HOW TO START THIS APP
rem  ---------------------
rem  Double-click this file. That is the whole instruction.
rem
rem  What happens next:
rem    1. this text window disappears immediately
rem    2. the studio window opens, looking like a normal program
rem    3. closing that window stops the studio
rem
rem  You can delete this file, or the whole folder it came in, as soon as the
rem  setup has finished. Everything the app needs lives in the studio folder,
rem  and the desktop shortcut points straight at the launcher inside it - not
rem  at whatever file you first downloaded.
rem ============================================================================

setlocal EnableExtensions
set "APP_DIR=%~dp0"
set "PY=%APP_DIR%env\Scripts\pythonw.exe"
set "PYW=%APP_DIR%env\Scripts\pythonw.exe"

if exist "%APP_DIR%env\.ready" goto silent
goto setup

rem ---------------------------------------------------------------------------
rem  SETUP - only ever needed once. This part needs a visible window, because
rem  it downloads about 540 MB and has to be able to explain itself if something
rem  goes wrong.
rem ---------------------------------------------------------------------------
:setup
title Local AI Voice Studio - Setup
set "VENV=%APP_DIR%env"
set "PYTHON_EXE=%VENV%\Scripts\python.exe"
set "MARKER=%VENV%\.ready"
set "WHEELS=%APP_DIR%wheels"
set "UV=%APP_DIR%uv.exe"
set "UV_ZIP=%APP_DIR%uv-download.zip"
set "UV_URL=https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"

rem Everything stays inside this folder. Nothing is installed system-wide.
set "UV_PYTHON_INSTALL_DIR=%APP_DIR%python"
set "UV_CACHE_DIR=%APP_DIR%uv-cache"
set "UV_PYTHON_PREFERENCE=only-managed"
set "UV_LINK_MODE=copy"

cls
echo ================================================================
echo    LOCAL AI VOICE STUDIO  -  FIRST TIME SETUP
echo    Tech Tips Dhanwala MH
echo ================================================================
echo.
echo   Good news: you only ever do this ONCE.
echo.
echo   You do NOT need Python. You do NOT need to install anything
echo   yourself. This file does all of it for you.
echo.
echo   It downloads about 540 MB and takes roughly 3 to 10 minutes
echo   depending on your internet speed.
echo.
echo   Do NOT close this window until it says READY TO RECORD.
echo.
echo ================================================================
echo.
pause

rem ------------------------------------------------- STEP 1: get the tool
if exist "%UV%" goto step2
call :banner "STEP 1 OF 4   Getting the setup tool"
where curl >nul 2>&1
if errorlevel 1 goto fail_net
curl -L -f --retry 3 -o "%UV_ZIP%" "%UV_URL%"
if not exist "%UV_ZIP%" goto fail_net
tar -xf "%UV_ZIP%" -C "%APP_DIR%" 2>nul
if not exist "%UV%" powershell -NoProfile -Command "Expand-Archive -LiteralPath '%UV_ZIP%' -DestinationPath '%APP_DIR%' -Force" >nul 2>&1
if exist "%UV_ZIP%" del "%UV_ZIP%"
if not exist "%UV%" goto fail_net
echo   [ok] Setup tool ready.

rem ------------------------------------------------ STEP 2: get Python 3.12
:step2
call :banner "STEP 2 OF 4   Getting Python 3.12"
echo   (this app needs Python 3.12 specifically - newer versions
echo    break one of the AI libraries it depends on)
echo.
"%UV%" python install 3.12
if errorlevel 1 goto fail_python
echo   [ok] Python 3.12 ready.

rem -------------------------------------- STEP 3: install the voice engine
call :banner "STEP 3 OF 4   Installing the voice engine"
rem --seed also installs pip, which is used for the offline install below.
"%UV%" venv --seed --python 3.12 "%VENV%"
if not exist "%PYTHON_EXE%" goto fail_engine
call :pip_install
if errorlevel 1 goto fail_engine
"%PYTHON_EXE%" -c "import gradio, soundfile, kokoro_onnx, onnxruntime, numpy" >nul 2>&1
if errorlevel 1 goto fail_engine

rem Pre-compile the bytecode for every library just installed.
rem
rem This looks like a micro-optimisation. It is not. Measured on a clean
rem install: without this step the FIRST launch spends about 14 extra
rem seconds compiling 6,198 .py files, so the window takes about 21
rem seconds to appear - and 13 of those seconds look like the app doing
rem nothing at all. With the bytecode pre-compiled the first launch is
rem about 8 seconds, the same as every launch after it.
rem
rem It costs about 27 seconds here, once, unattended - and about 100 MB
rem of disk. Failures are deliberately ignored: if this does not work the
rem app still runs correctly, it is just slower on its very first start.
echo   Preparing the engine for a fast first start...
"%PYTHON_EXE%" -m compileall -q -j 0 "%APP_DIR%env\Lib\site-packages" >nul 2>&1

echo   [ok] Voice engine installed.

rem --------------------------- STEP 4: fetch the voice model
call :banner "STEP 4 OF 4   Downloading the AI voice model"
echo   This is the part that makes the studio work with no internet.
echo   It happens once, and then it is yours forever.
echo.
"%PYTHON_EXE%" "%APP_DIR%_warmup.py"
if errorlevel 1 goto fail_model

"%UV%" cache clean >nul 2>&1
rem The wheels and the setup tool have done their job and are no longer
rem needed. Removing them now keeps the folder small.
rd /s /q "%WHEELS%" 2>nul
if exist "%UV%" del "%UV%" >nul 2>&1
if exist "%APP_DIR%uvx.exe" del "%APP_DIR%uvx.exe" >nul 2>&1
if exist "%APP_DIR%uvw.exe" del "%APP_DIR%uvw.exe" >nul 2>&1

rem ======================================================================
rem  DO NOT DELETE %APP_DIR%python. It looks like a leftover. It is not.
rem
rem  A Python "virtual environment" does NOT contain the standard library.
rem  env\pyvenv.cfg records the real interpreter it belongs to:
rem
rem      home = ...\LocalVoiceStudio\python\cpython-3.12-windows-x86_64-none
rem
rem  and env\Scripts\pythonw.exe is a small launcher that starts THAT
rem  interpreter. Delete the interpreter and the launcher has nothing to
rem  start. The failure is silent and total: the desktop icon does nothing,
rem  the app writes no log, and all Windows reports is
rem
rem      uv trampoline failed to spawn Python child process
rem      Caused by: entity not found (os error 2)
rem
rem  An earlier version of this file did delete it, and that broke every
rem  install while every test still passed - because the tests ran against
rem  a folder where the cleanup step had never been executed.
rem
rem  It is about 120 MB, and it is not optional. It is the thing that runs.
rem ======================================================================
echo ready>"%MARKER%"

rem The installer had to create the desktop icon before setup ran, so it
rem points at this .bat - the only file that existed then. Now that
rem env\pythonw.exe and .ready are both in place, replace it with the
rem version that points straight at pythonw.exe. That is the difference
rem between a black window on every launch and none at all, and without
rem this step the installer's viewers would never get the good one.
call "%~dp0Make Desktop Shortcut.bat" /quiet

cls
echo ================================================================
echo    READY TO RECORD
echo ================================================================
echo.
echo   Everything is installed and the voice model is on your PC.
echo.
echo   From now on: double-click the "Local AI Voice Studio" icon on
echo   your desktop, or this file again. Either one opens the studio
echo   in about 7 seconds, and it needs no internet at all.
echo.
echo   Starting the studio now...
echo.
ping -n 6 127.0.0.1 >nul
goto silent

rem ---------------------------------------------------------------------------
rem  NORMAL LAUNCH - pythonw.exe, so there is no console window at all.
rem
rem  Two things matter here and both were measured:
rem
rem  1. pythonw.exe, not python.exe. pythonw is the GUI-subsystem build, so
rem     Windows never gives it a console. python.exe would show a black window
rem     for the whole session.
rem
rem  2. "start" without /b. With /b the child stays attached to this console,
rem     and closing this window can take the studio down with it. Without /b
rem     the studio is a separate process with its own lifetime - closing this
rem     window, or the folder, changes nothing. That is the difference between
rem     "it died when I closed the terminal" and "it just keeps running".
rem
rem  The desktop shortcut goes one better and points straight at pythonw.exe,
rem  so it never opens a console even for a moment. This file is the fallback
rem  for when somebody runs it from inside the folder.
rem ---------------------------------------------------------------------------
:silent
if not exist "%APP_DIR%env\.ready" goto fail_engine
cd /d "%APP_DIR%"
set "VIRTUAL_ENV=%APP_DIR%env"
set "HF_HUB_OFFLINE=1"
set "HF_HUB_DISABLE_TELEMETRY=1"
set "GRADIO_ANALYTICS_ENABLED=False"
set "ONNXRUNTIME_LOG_SEVERITY_LEVEL=3"

if not exist "%PYW%" set "PYW=%PY%"

rem Launch it and let go. "start" without /b makes the studio a separate
rem process with its own lifetime, so closing this window - or deleting
rem this file - changes nothing about the studio already running.
rem
rem There is deliberately NO "did it start?" loop here. An earlier version
rem waited for port 7860 and, when it did not appear in time, started the
rem studio AGAIN with a visible window. That turned one slow start into two
rem studios fighting over one port. The wait was also unreliable: "timeout
rem /t 1" is not always Windows' timeout.exe, and where it is not (a Git
rem or MSYS install earlier on PATH) it rejects /t and returns instantly,
rem collapsing the whole 20 second loop into about one second.
rem
rem Everything that can go wrong is now reported from inside the app, with
rem a real Windows dialog box that a non-technical viewer can act on. The
rem launcher only has to start it and get out of the way.
start "" /d "%APP_DIR%" "%PYW%" "%APP_DIR%local_voice_app.py"
exit /b 0

rem ---------------------------------------------------------------- helpers
:banner
echo.
echo ----------------------------------------------------------------
echo    %~1
echo ----------------------------------------------------------------
echo.
exit /b 0

:pip_install
rem A big wheel can be locked for a moment by antivirus real-time scanning.
rem That is transient, so try a few times before giving up.
rem
rem If a local wheels\ folder is present the install is done entirely from
rem disk - no package index is contacted at all. The studio works either way.
if exist "%WHEELS%" (
  echo   Installing from the bundled files - no internet needed...
  "%UV%" pip install --python "%PYTHON_EXE%" --no-index --find-links "%WHEELS%" -r "%APP_DIR%requirements.txt"
  if not errorlevel 1 exit /b 0
  echo   Bundled files incomplete - falling back to the internet...
)
set "TRY=0"
:try_pip
set /a TRY+=1
"%UV%" pip install --python "%PYTHON_EXE%" -r "%APP_DIR%requirements.txt"
if not errorlevel 1 exit /b 0
if %TRY% GEQ 3 exit /b 1
echo.
echo   The download was interrupted. Trying again (%TRY% of 3)...
echo.
ping -n 4 127.0.0.1 >nul
goto try_pip

:fail_net
call :banner "COULD NOT DOWNLOAD THE SETUP TOOL"
echo   Your internet connection may be down, or a firewall is
echo   blocking the download.
echo.
echo   Check your connection and double-click this file again.
echo.
pause
exit /b 1

:fail_python
call :banner "COULD NOT SET UP PYTHON"
echo   The setup tool could not prepare Python 3.12.
echo.
echo   Please double-click "Repair Setup.bat" and try again.
echo.
pause
exit /b 1

:fail_engine
call :banner "COULD NOT INSTALL THE VOICE ENGINE"
echo   The download was probably interrupted.
echo.
echo   Please double-click "Repair Setup.bat" and try again.
echo.
pause
exit /b 1

:fail_model
call :banner "COULD NOT DOWNLOAD THE VOICE MODEL"
echo   The engine is installed, but the voice model did not finish
echo   downloading.
echo.
echo   Just double-click this file again. The download carries on from
echo   where it stopped instead of starting the whole file over, so you
echo   do not lose the part you already have.
echo.
pause
exit /b 1

:fail_run
call :banner "THE STUDIO STOPPED UNEXPECTEDLY"
echo   Read the last few lines above - they explain what happened.
echo.
echo   Most common fix: double-click "Repair Setup.bat".
echo.
pause
exit /b 1
