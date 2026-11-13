@echo off
REM Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
rem Apaga el portal (puerto 8000), el de prueba (8001) y el local (8002), aunque sus ventanas no esten a la vista.
set ENCONTRADO=
for %%n in (8000 8001 8002) do (
    for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%%n .*LISTENING"') do (
        taskkill /PID %%p /T /F >nul 2>&1
        set ENCONTRADO=1
    )
)
if defined ENCONTRADO (echo Portal apagado.) else (echo No habia ningun portal encendido.)
pause
