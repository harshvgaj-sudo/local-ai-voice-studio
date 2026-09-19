@echo off
setlocal EnableExtensions
title Local AI Voice Studio
cd /d "%~dp0"

rem ---------------------------------------------------------------- settings
set "APP_DIR=%~dp0"
set "VENV=%APP_DIR%env"
set "PY=%VENV%\Scripts\python.exe"
set "MARKER=%VENV%\.ready"
set "UV=%APP_DIR%uv.exe"
set "UV_ZIP=%APP_DIR%uv-download.zip"
set "UV_URL=https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"

rem Everything stays inside this folder. Nothing is installed system-wide.
set "UV_PYTHON_INSTALL_DIR=%APP_DIR%python"
set "UV_CACHE_DIR=%APP_DIR%uv-cache"
set "UV_PYTHON_PREFERENCE=only-managed"
set "UV_LINK_MODE=copy"
set "HF_HUB_DISABLE_TELEMETRY=1"
set "GRADIO_ANALYTICS_ENABLED=False"

if exist "%MARKER%" goto launch

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
echo   It downloads about 1.5 GB and takes roughly 5 to 15 minutes
echo   depending on your internet speed.
echo.
echo   Do NOT close this window until it says READY TO RECORD.
echo.
echo ================================================================
echo.
pause

rem ------------------------------------------------- STEP 1: get the tool
if exist "%UV%" goto step2
call :banner "STEP 1 OF 3   Getting the setup tool"
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
call :banner "STEP 2 OF 3   Getting Python 3.12"
echo   (this app needs Python 3.12 specifically - newer versions
echo    break one of the AI libraries it depends on)
echo.
"%UV%" python install 3.12
if errorlevel 1 goto fail_python
echo   [ok] Python 3.12 ready.

rem -------------------------------------- STEP 3: install the voice engine
call :banner "STEP 3 OF 3   Installing the voice engine"
echo   This is the big download. You can leave it alone and come back.
echo.
rem --seed also installs pip, which the language data step below needs.
"%UV%" venv --seed --python 3.12 "%VENV%"
if not exist "%PY%" goto fail_engine
"%UV%" pip install --python "%PY%" -r "%APP_DIR%requirements.txt"
if errorlevel 1 goto fail_engine
"%PY%" -c "import kokoro, soundfile, gradio" >nul 2>&1
if errorlevel 1 goto fail_engine
echo   [ok] Voice engine installed.
echo.
echo   Installing the language data it reads your text with...
"%PY%" -m spacy download en_core_web_sm
if errorlevel 1 goto fail_engine
echo   [ok] Language data installed.

rem --------------------------- STEP 3b: fetch the voice model, like Subtitle Edit
call :banner "STEP 3b   Downloading the AI voice model"
echo   This is the part that makes the studio work with no internet.
echo   It happens once, and then it is yours forever.
echo.
"%PY%" "%APP_DIR%_warmup.py"
if errorlevel 1 goto fail_model

"%UV%" cache clean >nul 2>&1
echo ready>"%MARKER%"

cls
echo ================================================================
echo    READY TO RECORD
echo ================================================================
echo.
echo   Everything is installed and the voice model is on your PC.
echo.
echo   From now on: just double-click "START HERE.bat"
echo   (or the desktop icon). It takes about a minute to open, because
echo   it loads a real AI model into memory - and it needs no internet
echo   at all.
echo.
echo   Starting the studio now...
echo.
timeout /t 5 >nul
goto launch

rem -------------------------------------------------------------- launching
:launch
cd /d "%APP_DIR%"
if not exist "%PY%" goto fail_engine
set "VIRTUAL_ENV=%VENV%"
"%PY%" "%APP_DIR%local_voice_app.py"
if errorlevel 1 goto fail_run
exit /b 0

rem ---------------------------------------------------------------- helpers
:banner
echo.
echo ----------------------------------------------------------------
echo    %~1
echo ----------------------------------------------------------------
echo.
exit /b 0

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
echo   Just double-click this file again - it will pick up where
echo   it left off.
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
