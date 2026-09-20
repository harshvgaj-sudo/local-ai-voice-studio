@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem /quiet is passed by the setup, which calls this as its final step. It
rem suppresses only the final pause - the [ok] lines still print, because
rem "your desktop icon was created" is useful information mid-setup.
if /i "%~1"=="/quiet" set "QUIET=1"

rem ============================================================================
rem  Creates the desktop and Start Menu icons.
rem
rem  The shortcut points straight at pythonw.exe, NOT at a .bat file. That is
rem  the difference between "a black window flashes every time" and "it opens
rem  like a normal program":
rem
rem    pointing at START HERE.bat  -> Windows opens a console first, then the
rem                                   studio, so there is always a black window
rem    pointing at pythonw.exe     -> pythonw is the GUI-subsystem build, so
rem                                   Windows never allocates a console at all
rem
rem  The setup file runs this automatically. It is here so it can be re-run if
rem  the icons are ever deleted.
rem ============================================================================

set "APPDIR=%~dp0"
set "PYW=%APPDIR%env\Scripts\pythonw.exe"
set "PY=%APPDIR%env\Scripts\python.exe"

if not exist "%PYW%" set "PYW=%PY%"

echo.
echo   Creating shortcuts for Local AI Voice Studio...
echo.

if not exist "%APPDIR%env\.ready" (
  echo   NOTE: setup has not finished yet, so the shortcut will start the
  echo   setup the first time you use it. That is fine.
  echo.
  set "PYW=%APPDIR%START HERE.bat"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$target='%PYW%';" ^
  "$args_='\"%APPDIR%local_voice_app.py\"';" ^
  "$icon='%APPDIR%voice.ico,0';" ^
  "$ws=New-Object -ComObject WScript.Shell;" ^
  "$made=@();" ^
  "foreach($dir in @([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'))){" ^
  "  $lnk=Join-Path $dir 'Local AI Voice Studio.lnk';" ^
  "  $s=$ws.CreateShortcut($lnk);" ^
  "  $s.TargetPath=$target;" ^
  "  if($target -like '*.exe'){ $s.Arguments=$args_ };" ^
  "  $s.WorkingDirectory='%APPDIR%';" ^
  "  $s.IconLocation=$icon;" ^
  "  $s.Description='Free offline AI voice generator that runs on this PC';" ^
  "  $s.Save(); $made+=$lnk };" ^
  "$made | ForEach-Object { Write-Host ('  [ok] ' + $_) }"

if errorlevel 1 (
  echo.
  echo   Shortcuts could not be created automatically.
  echo   You can still run the app by double-clicking
  echo   "START HERE.bat" in this folder.
  echo.
) else (
  echo.
  echo ================================================================
  echo    DONE
  echo ================================================================
  echo.
  echo   To open the studio from now on, either:
  echo     - double-click the new desktop icon, or
  echo     - press the Windows key, type "voice", press Enter.
  echo.
  echo   The icon opens the studio with no black window at all, and you
  echo   can close this folder or any terminal - it keeps running.
  echo.
)

if not defined QUIET pause
