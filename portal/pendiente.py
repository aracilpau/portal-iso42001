# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Lo que está pendiente en un espacio: el seguimiento con sus ajustes y lo que sale en «Lo siguiente» de Inicio.

Lo usan el portal (Inicio) y los avisos por correo, que funcionan sin el portal
encendido: por eso no depende de la web, solo de la base de datos y de qué día es.
"""
from datetime import date
from pathlib import Path

from portal import db, seguimiento
from portal import guia as guia_portal


def antelacion(bd: Path, e: int) -> int:
    # Un solo valor para todo el espacio; si un día va por requisito, se cambia aquí
    return int(db.ajuste(bd, e, "antelacion", str(seguimiento.ANTELACION)))


def plazo_general(bd: Path, e: int) -> int:
    return int(db.ajuste(bd, e, "plazo_general", str(seguimiento.PLAZO_GENERAL)))


def estado(bd: Path, espacio, hoy: date) -> seguimiento.Seguimiento:
    e = espacio["id"]
    # Con el MySQL, las siete lecturas a la vez: un viaje en vez de ocho
    decisiones, marcas, plazos, ajustes, sistemas, lineas, recordatorios = db.a_la_vez(
        lambda: db.decisiones(bd, e), lambda: db.marcas(bd, e), lambda: db.plazos(bd, e), lambda: db.ajustes(bd, e),
        lambda: db.sistemas(bd, e), lambda: db.marcas_sistema(bd, e), lambda: db.recordatorios(bd, e))
    return seguimiento.Seguimiento(
        marcas, plazos=plazos, hoy=hoy, excluidos={c for c, d in decisiones.items() if not d.aplica},
        plazo_general=int(ajustes.get("plazo_general", seguimiento.PLAZO_GENERAL)),
        antelacion=int(ajustes.get("antelacion", seguimiento.ANTELACION)),
        sistemas=sistemas, lineas=lineas, recordatorios=recordatorios,
        inicio=min(date.fromisoformat(espacio["creado"][:10]), hoy))


# --- «¿Ha pasado algo?» ---

def preguntar_cada(bd: Path, e: int) -> int:
    return int(db.ajuste(bd, e, "preguntar_cada", str(seguimiento.PREGUNTAR_POR_DEFECTO)))


def proxima_pregunta(bd: Path, e: int, est: seguimiento.Seguimiento) -> date | None:
    contestada = db.ajuste(bd, e, "eventos_contestado", "")
    return seguimiento.proxima_pregunta(preguntar_cada(bd, e), est.inicio,
                                        date.fromisoformat(contestada) if contestada else None)


def afectados(sit: guia_portal.Situacion, est: seguimiento.Seguimiento):
    """Los requisitos de la situación que cuentan (no los controles que no aplican), cada uno con lo
    que se reabriría."""
    return [(r, est.a_reabrir(r)) for r in sit.requisitos if est.aplica(r.codigo)]


# --- Sistemas dados de alta o vueltos a activar con la pregunta de reabrir sin contestar ---
# «id:como» separados por comas, en los ajustes del espacio

def altas_pendientes(bd: Path, e: int) -> dict[int, str]:
    texto = db.ajuste(bd, e, "altas_pendientes", "")
    return {int(i): como for i, como in (x.split(":") for x in texto.split(",") if x)}


def preguntas_alta(bd: Path, e: int, est: seguimiento.Seguimiento) -> list[tuple[db.Sistema, str]]:
    """Las que siguen en pie: sistemas activos y con algo de toda la empresa que reabrir."""
    if not any(lista for _, lista in afectados(guia_portal.ALTA, est)):
        return []
    activos = {x.id: x for x in est.sistemas}
    return [(activos[i], como) for i, como in altas_pendientes(bd, e).items() if i in activos]


# --- Los avisos ---

def avisa(bd: Path, e: int, clave: str) -> bool:
    return db.ajuste(bd, e, clave, "1") == "1"


def pendientes(bd: Path, e: int, est: seguimiento.Seguimiento) -> dict:
    """Lo que sale en «Lo siguiente» de Inicio: solo lo que se ha elegido que avise."""
    return {
        "vencidos": est.avisos(seguimiento.VENCIDO) if avisa(bd, e, "avisar_vencidos") else [],
        "pronto": est.avisos(seguimiento.VENCE_PRONTO) if avisa(bd, e, "avisar_pronto") else [],
        "recordatorios": est.recordatorios_hoy() if avisa(bd, e, "avisar_recordatorios") else [],
        # «¿Ha pasado algo?»: una lista de uno, o vacía, para que cuente en el número
        "pregunta": [f] if avisa(bd, e, "avisar_recordatorios") and (f := proxima_pregunta(bd, e, est)) and f <= est.hoy else [],
        # Sistemas nuevos o vueltos a activar con la pregunta sin contestar
        "altas": preguntas_alta(bd, e, est),
    }
