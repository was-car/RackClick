@echo off
rem RackClick - ENSAYO INTERNO MFA-INIT. No es instalador ni actualizacion.
rem Check (solo lectura):  INICIAR-ENSAYO-MFA.cmd <SHA256-de-SHA256SUMS> [NombreServicio]
rem Run (escribe una carpeta nueva; consola elevada y confirmacion escrita):
rem                        INICIAR-ENSAYO-MFA.cmd run <SHA256-de-SHA256SUMS> [NombreServicio]
setlocal
echo RackClick - ENSAYO INTERNO MFA-INIT (no es instalador ni actualizacion).
set "TRIAL_MODE=Check"
if /i not "%~1"=="run" goto no_run
set "TRIAL_MODE=Run"
shift
:no_run
set "TRIAL_SUMS=%~1"
set "TRIAL_SERVICE=%~2"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Invoke-MfaInitTrial.ps1" -Mode %TRIAL_MODE% -ExpectedSumsSha256 "%TRIAL_SUMS%" -ServiceName "%TRIAL_SERVICE%"
set "TRIAL_RC=%ERRORLEVEL%"
echo Codigo de salida: %TRIAL_RC%
endlocal & exit /b %TRIAL_RC%
