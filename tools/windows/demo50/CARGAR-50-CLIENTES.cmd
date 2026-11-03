@echo off
setlocal
set "RC_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "RC_PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
"%RC_PS%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0Import-RackClickDemo50.ps1" -PlanPath "%~dp0demo50-replay.json" -ExpectedPlanSha256 "a3b44a37d8ca81f2f13d515d26905a520af8f09ffb2cfe498f97d06367bf423a"
set "RC_EXIT=%ERRORLEVEL%"
echo Codigo final: %RC_EXIT%
pause
exit /b %RC_EXIT%
