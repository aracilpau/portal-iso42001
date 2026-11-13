@echo off
REM Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
rem Cambia la contrasena de una cuenta sin entrar en el portal: para cuando el administrador olvida la suya.
rem Trabaja con el portal instalado en este ordenador (el MySQL si es compartido, su carpeta si es local).
rem Con --prueba, con el portal de prueba (datos-prueba), solo para probarlo.
cd /d "%~dp0"
chcp 65001 >nul

if not exist ".venv\Scripts\python.exe" (
    echo Antes hay que arrancar el portal una vez con arrancar.bat.
    pause
    goto :eof
)

echo Cambiar la contrasena de una cuenta del portal
echo Lo que escribas en la contrasena no se ve en pantalla: es normal.
echo.
set "CORREO="
set /p "CORREO=Correo de la cuenta: "
if "%CORREO%"=="" (
    echo No has escrito ningun correo. No se ha cambiado nada.
    pause
    goto :eof
)
".venv\Scripts\python.exe" scripts\cuentas.py %* clave "%CORREO%"
echo.
pause
