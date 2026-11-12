@echo off
setlocal
set "RC_PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if defined PROCESSOR_ARCHITEW6432 set "RC_PS=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
echo RackClick online20 - abra este archivo con Ejecutar como administrador.
echo Check solo lee. Prepare adquiere y monta. Install abre el instalador nativo.
"%RC_PS%" -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0Install-RackClickOnline.ps1" %*
set "RC_EXIT=%ERRORLEVEL%"
if not "%RC_EXIT%"=="0" echo No se completo la entrada online. Revise el codigo mostrado. No se reintenta automaticamente.
pause
exit /b %RC_EXIT%
