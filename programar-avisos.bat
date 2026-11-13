@echo off
REM Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
rem Programa los avisos por correo: crea la tarea de Windows (dia 1 y lunes a las 9:00) y el enlace
rem que usa la notificacion. Se puede volver a ejecutar: sustituye la tarea anterior.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Arranca antes el portal una vez con arrancar.bat: prepara lo que hace falta.
    pause
    goto :eof
)
rem Instala las librerias que falten (si ya estan todas, no tarda nada)
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
".venv\Scripts\python.exe" scripts\avisos.py --programar
pause
