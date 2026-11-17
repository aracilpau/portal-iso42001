@echo off
REM Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
rem Pone el portal al dia con la ultima version publicada en GitHub: mira si hay una nueva, pregunta, apaga el
rem portal, cambia el programa (no los datos, los ajustes ni las contrasenas) y lo vuelve a arrancar.
cd /d "%~dp0"
if not defined PORTAL_PUERTO set "PORTAL_PUERTO=8000"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
rem Todo en un bloque: Windows lo lee entero antes de empezar, asi no le afecta que se cambie este mismo archivo
(
    echo Mirando en GitHub si hay una version nueva del portal...
    "%PY%" scripts\actualizar.py
    if errorlevel 1 (
        echo.
        pause
        exit /b
    )
    echo.
    echo Arrancando el portal ya actualizado...
    start "Portal ISO 42001" "%~dp0arrancar.bat"
    pause
    exit /b
)
