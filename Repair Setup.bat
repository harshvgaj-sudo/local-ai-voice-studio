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
echo   It deletes the downloaded setup (about 670 MB) and installs it
echo   again from scratch. Takes 3 to 10 minutes.
echo.
echo   Your generated voice files in the "output" folder are KEPT.
echo.
echo   IMPORTANT: close the studio window first, or this cannot clean
echo   up properly.
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
  echo   running. Close the studio window and run this file again.
  echo.
  pause
  exit /b 1
)

echo   [ok] Cleaned.
echo.
echo   Starting the setup again...
rem ping, not timeout. Windows' timeout.exe aborts immediately when its
rem stdin is redirected, and a Git-for-Windows install puts a GNU timeout
rem earlier on PATH that rejects /t outright. Either way the pause silently
rem does not happen. ping always sleeps.
ping -n 4 127.0.0.1 >nul
call "%~dp0START HERE.bat"
