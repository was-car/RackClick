@echo off
setlocal
cd /d "%~dp0"
set "RACKCLICK_PREP_EXIT=1"
if not exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" goto end
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0Invoke-RackClickHostPreparation.ps1" -Role Server
set "RACKCLICK_PREP_EXIT=%ERRORLEVEL%"
:end
echo.
echo Codigo de salida: %RACKCLICK_PREP_EXIT%. Consulte LEEME-PRIMERO.html.
pause
exit /b %RACKCLICK_PREP_EXIT%
