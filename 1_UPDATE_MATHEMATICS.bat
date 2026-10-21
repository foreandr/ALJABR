@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title ALJABR - Fetch Real Mathlib Mathematics

echo ================================================================
echo ALJABR 1 - UPDATE MATHEMATICS FROM MATHLIB VIA LEAN GRAPH
echo ================================================================
echo.
echo This downloads/builds real Mathlib and extracts its Lean Graph.
echo First run can require many gigabytes and a long build.
echo Lean 4 will be installed automatically if missing.
echo Git and Python 3 are still required.
echo.
if not "%~1"=="" goto importfile
where git >nul 2>&1 || (echo ERROR: Git is not installed or not on PATH. & goto fail)
where lake >nul 2>&1 && goto lean_ready
if exist "%USERPROFILE%\.elan\bin\lake.exe" goto add_lean_path
echo Lean 4 / Lake not found. Installing Lean automatically...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_lean.ps1"
if errorlevel 1 (echo ERROR: Automatic Lean installation failed. & goto fail)
:add_lean_path
set "PATH=%USERPROFILE%\.elan\bin;%PATH%"
:lean_ready
where lake >nul 2>&1 || (echo ERROR: lake still not available after installation. & goto fail)
where py >nul 2>&1 && (set "PY=py -3") || (where python >nul 2>&1 && (set "PY=python"))
if not defined PY (echo ERROR: Python 3 is not installed. & goto fail)
rem Lean Graph currently targets Lean 4.29.0. Keep Mathlib on that matching tag.
set "MATHLIB_TAG=v4.29.0"
if not exist "tools\mathlib4\.git" (
  echo Cloning Mathlib4 at compatible release %MATHLIB_TAG%...
  git clone --depth 1 --branch %MATHLIB_TAG% https://github.com/leanprover-community/mathlib4.git "tools\mathlib4" || goto fail
) else (
  echo Selecting Mathlib4 compatible release %MATHLIB_TAG%...
  rem Previously generated lakefile modifications must be reverted before checkout.
  git -C "tools\mathlib4" restore lakefile.toml lakefile.lean 2>nul
  git -C "tools\mathlib4" fetch --depth 1 origin tag %MATHLIB_TAG% || goto fail
  git -C "tools\mathlib4" -c advice.detachedHead=false checkout -f tags/%MATHLIB_TAG% || goto fail
)
if not exist "tools\lean-graph\.git" (
  echo Cloning lean-graph...
  git clone --depth 1 https://github.com/aurasoph/lean-graph.git "tools\lean-graph" || goto fail
) else (
  echo Updating lean-graph...
  git -C "tools\lean-graph" pull --ff-only || goto fail
)
echo.
echo Downloading pinned Mathlib %MATHLIB_TAG% prebuilt artifacts...
pushd "tools\mathlib4"
call lake exe cache get || (popd & goto fail)
popd
rem The current author documents lakefile.lean local dependency. Prepare a
rem wrapper project next to Mathlib so their source is never overwritten.
echo Saving Mathlib locked dependency revisions...
%PY% verify_lock.py save || goto fail
echo Attaching Lean Graph locally...
%PY% setup_lean.py || goto fail
echo Resolving ONLY Lean Graph; keeping original Mathlib dependencies...
pushd "tools\mathlib4"
call lake update leanGraph --keep-toolchain || (popd & goto fail)
popd
%PY% verify_lock.py check || (
  echo ERROR: Lake upgraded Mathlib dependencies unexpectedly.
  echo This package is intentionally refusing a broken mixed-version build.
  goto fail
)
pushd "tools\mathlib4"
echo Building Lean Graph using the pinned Mathlib toolchain...
call lake build graph || (popd & goto fail)
if not exist "..\..\data" mkdir "..\..\data"
echo Exporting unified NDJSON...
call lake exe graph --mode unified --to Mathlib "..\..\data\mathlib_unified.ndjson" || (popd & goto fail)
popd
if not exist "data\mathlib_unified.ndjson" (echo ERROR: Export file missing. & goto fail)
:importfile
if not "%~1"=="" (
  if not exist "%~1" (echo ERROR: File not found: %~1 & goto fail)
  echo Importing supplied Lean Graph export...
  copy /y "%~1" "data\mathlib_unified.ndjson" >nul || goto fail
)
where py >nul 2>&1 && (set "PY=py -3") || (where python >nul 2>&1 && (set "PY=python"))
if not defined PY (echo ERROR: Python 3 missing. & goto fail)
%PY% import_lean.py "data\mathlib_unified.ndjson" || goto fail
%PY% build.py || goto fail
echo.
echo SUCCESS - New real Mathlib data is ready. Double-click 2_OPEN_ALJABR.bat.
pause
exit /b 0
:fail
echo.
echo FAILED - Previous successful mathematics data was preserved.
echo See README.md for setup requirements and error details.
pause
exit /b 1
