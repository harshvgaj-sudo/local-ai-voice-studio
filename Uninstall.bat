@echo off
setlocal EnableExtensions
title Uninstall Local AI Voice Studio
cd /d "%~dp0"

echo.
echo ================================================================
echo    UNINSTALL
echo ================================================================
echo.
echo   This removes the engine and Python (about 670 MB) from this folder.
echo.
echo   Your generated voice files in the "output" folder are KEPT.
echo.
echo   IMPORTANT: close the studio window first.
echo.
choice /C YN /M "   Uninstall now"
if errorlevel 2 exit /b 0

if exist "%~dp0env" rmdir /s /q "%~dp0env" 2>nul
if exist "%~dp0python" rmdir /s /q "%~dp0python" 2>nul
if exist "%~dp0uv-cache" rmdir /s /q "%~dp0uv-cache" 2>nul
if exist "%~dp0uv.exe" del "%~dp0uv.exe" 2>nul
if exist "%~dp0uvx.exe" del "%~dp0uvx.exe" 2>nul
if exist "%~dp0uvw.exe" del "%~dp0uvw.exe" 2>nul
if exist "%~dp0app-template" rmdir /s /q "%~dp0app-template" 2>nul
if exist "%~dp0app-window" rmdir /s /q "%~dp0app-window" 2>nul
if exist "%~dp0studio.log" del "%~dp0studio.log" 2>nul
if exist "%~dp0studio-server.log" del "%~dp0studio-server.log" 2>nul

echo.
echo   [ok] The engine has been removed.
echo.
echo   The voice model itself is in this folder, in the "models" folder.
echo   It is about 340 MB.
echo.
choice /C YN /M "   Delete the voice model too (about 340 MB)"
if errorlevel 2 goto done

if not exist "%~dp0models" (
  echo   Voice model was not found - nothing to delete.
  goto done
)

rem The model is downloaded straight into models\ by the setup file, so there
rem is no shared cache to unpick and nothing else on the disk refers to it.
rem An earlier version of this app fetched the model through Hugging Face and
rem kept it in %USERPROFILE%\.cache\huggingface, which meant the uninstaller
rem had to hunt through shared blobs to find it. That is no longer the case -
rem deleting this one folder is the whole job.
rmdir /s /q "%~dp0models" 2>nul
if exist "%~dp0models" (
  echo   [X] Could not delete the models folder. Close the studio and try again.
) else (
  echo   [ok] Voice model deleted.
)

:done
echo.
echo   Done. This whole folder can now be deleted safely.
echo.
pause
