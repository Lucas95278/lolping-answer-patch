@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  set "PATCH_PYTHON=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Install Python 3.9+ from python.org and enable PATH, then try again.
    pause
    exit /b 1
  )
  set "PATCH_PYTHON=python"
)
if not "%~1"=="" goto runargs
echo 1. Install patch
echo 2. Show status
echo 3. Restore original application
set "PATCH_CHOICE="
set /p "PATCH_CHOICE=Select [1]: "
set "PATCH_ACTION=apply"
if "%PATCH_CHOICE%"=="2" set "PATCH_ACTION=status"
if "%PATCH_CHOICE%"=="3" set "PATCH_ACTION=restore"
%PATCH_PYTHON% -m lolping_patch %PATCH_ACTION%
goto finished
:runargs
%PATCH_PYTHON% -m lolping_patch %*
:finished
set "PATCH_RESULT=%errorlevel%"
pause
exit /b %PATCH_RESULT%
