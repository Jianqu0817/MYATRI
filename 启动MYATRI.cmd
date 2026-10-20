@echo off
setlocal
title MYATRI
set "MYATRI_POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
"%MYATRI_POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_myatri.ps1" %*
set "MYATRI_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %MYATRI_EXIT%
