@echo off
setlocal
set "RC_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "RC_PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
echo RackClick - cambiar la IP de la instalacion. Ejecutalo como administrador.
echo.
"%RC_PS%" -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Cambiar-IP-RackClick.ps1"
set "RC_EXIT=%ERRORLEVEL%"
echo.
pause
exit /b %RC_EXIT%
