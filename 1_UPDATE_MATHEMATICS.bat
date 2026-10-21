@echo off
setlocal
cd /d "%~dp0"
rem Backward-compatible update button and drag-and-drop import support.
if "%~1"=="" (
    call "%~dp0PULL_AND_RUN.bat" --update-only
) else (
    call "%~dp0PULL_AND_RUN.bat" --update-only --import-file "%~f1"
)
exit /b %ERRORLEVEL%
