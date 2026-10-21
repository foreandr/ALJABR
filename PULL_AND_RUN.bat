@echo off
setlocal
cd /d "%~dp0"
title ALJABR - Pull and Update Mathematics
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launch.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo ALJABR needs attention. See logs and diagnostics\latest.json.
if not defined ALJABR_NO_PAUSE pause
exit /b %RESULT%
