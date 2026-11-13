# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Los avisos por correo del portal.

Lo lanza la tarea de Windows «Portal ISO 42001 - avisos» el día 1 y cada lunes, aunque el portal esté cerrado: manda lo
que toque con los datos de verdad, los del MySQL, nunca los del portal de prueba. Si otro ordenador ya lo ha
mandado, no lo repite.

    python scripts/avisos.py              manda lo que toque hoy
    python scripts/avisos.py --local      lo mismo, con el portal local (datos/)
    python scripts/avisos.py --programar  crea la tarea de Windows (lo hace programar-avisos.bat)
"""
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from portal import avisos, config, db, servidor  # noqa: E402

if __name__ == "__main__":
    if "--programar" in sys.argv:
        print(avisos.programar(RAIZ, date.today()))
    elif "--local" in sys.argv:
        avisos.ejecutar(config.DATOS_LOCAL, date.today(), avisos.Envio())
    else:
        db.usar_servidor(servidor.leer(config.SECRETOS))
        try:
            avisos.ejecutar(config.DATOS_SERVIDOR, date.today(), avisos.Envio())
        except servidor.SinConexion as error:
            avisos.Envio().notificacion("Portal ISO 42001: los avisos no han salido", str(error))
