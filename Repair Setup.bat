@echo off
setlocal EnableExtensions
title Repair Local AI Voice Studio
cd /d "%~dp0"

echo.
echo ================================================================
echo    REPAIR
echo ================================================================
echo.
echo   Use this if the studio ever stops working, or if you saw an
echo   error while it was setting up.
echo.
echo   It deletes the downloaded setup (about 2 GB) and installs it
echo   again from scratch. Takes 5 to 15 minutes.
echo.
echo   Your generated voice files in the "output" folder are KEPT.
echo.
echo   IMPORTANT: close the studio first (the black window that says
echo   "Local AI Voice Studio") or this cannot clean up properly.
echo.
choice /C YN /M "   Repair now"
if errorlevel 2 exit /b 0

echo.
echo   Removing the old setup...
if exist "%~dp0env" rmdir /s /q "%~dp0env" 2>nul
if exist "%~dp0python" rmdir /s /q "%~dp0python" 2>nul
if exist "%~dp0uv-cache" rmdir /s /q "%~dp0uv-cache" 2>nul
if exist "%~dp0uv.exe" del "%~dp0uv.exe" 2>nul
if exist "%~dp0uvx.exe" del "%~dp0uvx.exe" 2>nul
if exist "%~dp0uvw.exe" del "%~dp0uvw.exe" 2>nul

echo.
if exist "%~dp0env" (
  echo   Some files could not be removed - the studio is probably still
  echo   running. Close the black "Local AI Voice Studio" window and
  echo   run this file again.
  echo.
  pause
  exit /b 1
)

echo   [ok] Cleaned.
echo.
echo   Starting the setup again...
timeout /t 3 >nul
call "%~dp0START HERE.bat"
