@echo off
REM Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
rem Arranca el portal y lo abre en el navegador. La primera vez prepara el entorno de Python y el portal ensena la
rem instalacion: solo en este ordenador o compartido con el equipo. Lo elegido queda en los ajustes del
rem usuario de Windows (AppData), fuera de esta carpeta, y actualizar el portal no lo toca.
cd /d "%~dp0"
if not defined PORTAL_PUERTO set "PORTAL_PUERTO=8000"

if not exist ".venv\Scripts\python.exe" (
    python --version >nul 2>&1 || goto :sinpython
    echo Preparando el entorno de Python ^(solo la primera vez, tarda un par de minutos^)...
    python -m venv .venv || goto :error
)
rem Instala las librerias que falten (si ya estan todas, no tarda nada)
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto :error

rem Si ya hay un portal encendido, el nuevo no puede arrancar y el navegador seguiria viendo el viejo
netstat -ano | findstr /r /c:":%PORTAL_PUERTO% .*LISTENING" >nul
if not errorlevel 1 (
    echo Ya hay un portal encendido en http://localhost:%PORTAL_PUERTO% ^(puede ser una version anterior^).
    echo Cierra su ventana negra, o reinicia el ordenador, y vuelve a arrancar.
    pause
    goto :eof
)

set "PORTAL_INSTALADO=1"
echo Portal en http://localhost:%PORTAL_PUERTO%  ^(cierra esta ventana para apagarlo^)
start "" http://localhost:%PORTAL_PUERTO%
".venv\Scripts\python.exe" -m uvicorn portal.main:app --port %PORTAL_PUERTO%
if errorlevel 1 pause
goto :eof

:sinpython
echo El portal necesita Python, y no esta instalado en este ordenador.
echo Se abre la pagina de descarga: instala la ultima version y, en la primera pantalla del instalador,
echo marca "Add python.exe to PATH". Despues, vuelve a hacer doble clic en arrancar.bat.
start "" https://www.python.org/downloads/
pause
goto :eof

:error
echo.
echo No se ha podido preparar el entorno. Comprueba que tienes internet y que Python esta instalado.
pause
