@echo off
setlocal
cd /d "%~dp0"
title ALJABR - Open Atlas
if not exist "aljabr-data.js" (
  echo Missing browser data. Trying to build it...
  where py >nul 2>&1 && (py -3 build.py) || (where python >nul 2>&1 && python build.py)
)
if not exist "aljabr-data.js" (
  echo ERROR: Could not build browser data. Install Python 3 or restore the original package.
  pause
  exit /b 1
)
start "" "%~dp0aljabr.html"
exit /b 0
