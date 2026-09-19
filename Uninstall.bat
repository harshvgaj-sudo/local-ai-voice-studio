@echo off
setlocal EnableExtensions
title Uninstall Local AI Voice Studio
cd /d "%~dp0"

echo.
echo ================================================================
echo    UNINSTALL
echo ================================================================
echo.
echo   This removes the engine and Python (about 1.1 GB) from this folder.
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

set "HUB=%USERPROFILE%\.cache\huggingface\hub"
set "MODEL=%HUB%\models--hexgrad--Kokoro-82M"

if not exist "%MODEL%" (
  echo   Voice model was not found - nothing to delete.
  goto done
)

rem 1. remove the model folder itself
rmdir /s /q "%MODEL%" 2>nul

rem 2. remove the shared blob data that belongs to that model.
rem Newer huggingface_hub keeps the real file bytes in a shared "blobs"
rem folder, and a matching .refs file records which model each blob belongs
rem to. Deleting ONLY the model folder would leave the 330 MB on disk AND
rem make the next run skip the download entirely - so the blobs must go too.
rem A blob is only deleted when its .refs file actually names this model, so
rem every other model in your cache is left untouched.
set "N=0"
if exist "%HUB%\blobs" (
  for /r "%HUB%\blobs" %%F in (*.refs) do (
    findstr /m /c:"models--hexgrad--Kokoro-82M" "%%F" >nul 2>&1
    if not errorlevel 1 (
      del /q "%%~dpnF" >nul 2>&1
      del /q "%%F" >nul 2>&1
      set /a N+=1
    )
  )
)
echo   [ok] Voice model deleted.  (%N% cached file blocks freed)

:done
echo.
echo   Done. This whole folder can now be deleted safely.
echo.
pause
