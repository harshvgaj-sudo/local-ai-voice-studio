@echo off
setlocal EnableExtensions
title Uninstall Local AI Voice Studio
cd /d "%~dp0"

echo.
echo ================================================================
echo    UNINSTALL
echo ================================================================
echo.
echo   This removes the engine and Python (about 2 GB) from this folder.
echo.
echo   Your generated voice files in the "output" folder are KEPT.
echo.
echo   IMPORTANT: close the studio first (the black window).
echo.
choice /C YN /M "   Uninstall now"
if errorlevel 2 exit /b 0

if exist "%~dp0env" rmdir /s /q "%~dp0env" 2>nul
if exist "%~dp0python" rmdir /s /q "%~dp0python" 2>nul
if exist "%~dp0uv-cache" rmdir /s /q "%~dp0uv-cache" 2>nul
if exist "%~dp0uv.exe" del "%~dp0uv.exe" 2>nul
if exist "%~dp0uvx.exe" del "%~dp0uvx.exe" 2>nul
if exist "%~dp0uvw.exe" del "%~dp0uvw.exe" 2>nul

echo.
echo   [ok] The engine has been removed.
echo.
echo   The voice model itself is stored by Windows here:
echo   %USERPROFILE%\.cache\huggingface\hub\models--hexgrad--Kokoro-82M
echo.
choice /C YN /M "   Delete the voice model too (about 330 MB)"
if errorlevel 2 goto done
if exist "%USERPROFILE%\.cache\huggingface\hub\models--hexgrad--Kokoro-82M" (
  rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--hexgrad--Kokoro-82M" 2>nul
  echo   [ok] Voice model deleted.
) else (
  echo   Voice model was not found - nothing to delete.
)

:done
echo.
echo   Done. This whole folder can now be deleted safely.
echo.
pause
