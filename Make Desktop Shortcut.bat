@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo.
echo   Creating shortcuts for Local AI Voice Studio...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$target='%~dp0START HERE.bat';" ^
  "$icon='%~dp0voice.ico,0';" ^
  "$ws=New-Object -ComObject WScript.Shell;" ^
  "$made=@();" ^
  "foreach($dir in @([Environment]::GetFolderPath('Desktop'),[Environment]::GetFolderPath('Programs'))){" ^
  "  $lnk=Join-Path $dir 'Local AI Voice Studio.lnk';" ^
  "  $s=$ws.CreateShortcut($lnk);" ^
  "  $s.TargetPath=$target;" ^
  "  $s.WorkingDirectory='%~dp0';" ^
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
  echo   You will never need to type a command again.
  echo.
)

pause
