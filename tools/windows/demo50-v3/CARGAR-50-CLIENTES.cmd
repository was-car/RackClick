@echo off
setlocal
set "RC_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "RC_PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%RC_PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0Import-RackClickDemo50.ps1" -PlanPath "%~dp0demo50-replay.json" -ExpectedPlanSha256 "44f7fca5dd78b10de1a5efbb51f34cff488974ed264bfcf9ea72059b1194216d"
set "RC_EXIT=%ERRORLEVEL%"
echo Codigo final: %RC_EXIT%
pause
exit /b %RC_EXIT%
