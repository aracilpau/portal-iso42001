# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Los avisos por correo y notificación de Windows.

Nada sale de verdad: el Outlook y las notificaciones son de mentira (conftest.py).
"""
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from conftest import EnvioDeMentira, en_portal
from portal import avisos, db, guia, pendiente, seguimiento
from portal.main import crear_app

LUNES = date(2026, 10, 5)
JUEVES_DIA_1 = date(2026, 10, 1)
LUNES_DIA_1 = date(2026, 6, 1)
VENCIDO, ESTA_SEMANA, MAS_ADELANTE = "4.1.a", "4.1.b", "4.1.c"


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


def espacio(bd):
    return db.espacios(bd)[0]


def con_vencimiento(bd, punto, vence):
    e = espacio(bd)["id"]
    db.marcar(bd, e, punto, date(2025, 1, 1))
    db.recolocar(bd, e, punto, vence)


def activar(bd, desde=date(2026, 1, 1), para="carlos@empresa.com"):
    e = espacio(bd)["id"]
    db.guardar_ajuste(bd, e, avisos.ACTIVADOS, "1")
    db.guardar_ajuste(bd, e, avisos.DESDE, desde.isoformat())
    db.guardar_ajuste(bd, e, avisos.PARA, para)


def acciones(bd):
    return [(f["accion"], f["detalle"]) for f in db.actividad(bd, espacio(bd)["id"])]


# --- Piezas: qué toca según la fecha ---

DESDE = date(2026, 1, 1)


def test_el_dia_1_toca_el_resumen_del_mes():
    assert avisos.que_toca(JUEVES_DIA_1, DESDE, "2026-09-01", "2026-09-28") == avisos.Toca(mes=JUEVES_DIA_1)


def test_el_lunes_toca_la_semana():
    assert avisos.que_toca(LUNES, DESDE, "2026-10-01", "2026-09-28") == avisos.Toca(semana=LUNES)


def test_si_el_dia_1_es_lunes_tocan_los_dos_a_la_vez():
    assert avisos.que_toca(LUNES_DIA_1, DESDE, "2026-05-01", "2026-05-25") == avisos.Toca(mes=LUNES_DIA_1,
                                                                                         semana=LUNES_DIA_1)


def test_un_lunes_perdido_sale_el_martes():
    assert avisos.que_toca(date(2026, 10, 6), DESDE, "2026-10-01", "2026-09-28") == avisos.Toca(semana=LUNES)


def test_lo_ya_mandado_no_se_repite():
    assert not avisos.que_toca(date(2026, 10, 6), DESDE, "2026-10-01", "2026-10-05")


def test_al_activarlos_no_llega_uno_atrasado():
    miercoles = date(2026, 10, 7)
    assert not avisos.que_toca(miercoles, miercoles, "", "")
    assert avisos.que_toca(LUNES, LUNES, "", "") == avisos.Toca(semana=LUNES)  # activados ese mismo lunes, sí


# --- Piezas: qué dice ---

def mensaje(bd, hoy, toca):
    est = pendiente.estado(bd, espacio(bd), hoy)
    return avisos.mensaje(est, pendiente.pendientes(bd, espacio(bd)["id"], est), toca)


def test_sin_nada_el_lunes_dice_que_no_vence_nada_y_el_dia_1_todo_al_dia(bd):
    m = mensaje(bd, LUNES_DIA_1, avisos.Toca(mes=LUNES_DIA_1, semana=LUNES_DIA_1))
    assert "Esta semana no vence nada." in m.html and "Todo al día." in m.html
    assert m.asunto == "[Portal ISO 42001] Avisos: resumen del mes y esta semana"
    assert m.corto == "Resumen del mes: todo al día; esta semana no vence nada."


def test_el_lunes_lleva_lo_vencido_y_lo_de_esta_semana_pero_no_lo_de_mas_adelante(bd):
    con_vencimiento(bd, VENCIDO, date(2026, 9, 20))
    con_vencimiento(bd, ESTA_SEMANA, date(2026, 10, 9))
    con_vencimiento(bd, MAS_ADELANTE, date(2026, 10, 20))
    m = mensaje(bd, LUNES, avisos.Toca(semana=LUNES))
    assert "Ya vencido" in m.html and "punto 4.1.a" in m.html and "venció el 20/09/2026" in m.html
    assert "Esta semana (del 05/10 al 11/10)" in m.html and "punto 4.1.b" in m.html and "vence el 09/10/2026" in m.html
    assert "4.1.c" not in m.html
    assert m.corto == "1 vence esta semana; 1 vencido."
    assert guia.requisito("4.1").titulo in m.html


def test_lo_que_vence_el_lunes_y_se_manda_el_martes_ya_va_como_vencido(bd):
    con_vencimiento(bd, ESTA_SEMANA, LUNES)
    m = mensaje(bd, date(2026, 10, 6), avisos.Toca(semana=LUNES))
    assert "Ya vencido" in m.html and "Esta semana no vence" not in m.html


def test_una_linea_de_sistema_no_lleva_el_nombre_del_sistema():
    req = guia.requisito("4.1")
    a = seguimiento.Aviso(req, req.puntos[0], SimpleNamespace(nombre="Sistema secreto"), date(2026, 10, 9))
    linea = avisos._linea(a, "vence")
    assert "Sistema secreto" not in linea and "de un sistema del inventario" in linea


def test_la_prueba_lo_dice_en_el_asunto_y_en_el_correo(bd):
    est = pendiente.estado(bd, espacio(bd), LUNES)
    m = avisos.mensaje(est, {"vencidos": [], "pronto": [], "recordatorios": [], "pregunta": [], "altas": []},
                       avisos.Toca(semana=LUNES), prueba=True)
    assert m.asunto.startswith("[Prueba] ") and "Aviso de prueba" in m.html


def test_destinatarios_con_comas_o_punto_y_coma():
    assert avisos.destinatarios(" a@x.com; b@y.com,, c@z.com ") == ["a@x.com", "b@y.com", "c@z.com"]


# --- Piezas: la tarea de Windows ---

def test_la_tarea_es_el_dia_1_y_los_lunes_a_las_9_y_al_encender_si_se_paso():
    x = avisos.xml_tarea(Path(r"C:\p & q\pythonw.exe"), Path(r"C:\p & q\scripts\avisos.py"), Path(r"C:\p & q"), LUNES)
    assert "<Day>1</Day>" in x and "<December/>" in x and "<Monday/>" in x
    assert x.count("<StartBoundary>2026-10-05T09:00:00</StartBoundary>") == 2
    assert "<StartWhenAvailable>true</StartWhenAvailable>" in x
    assert "<LogonType>InteractiveToken</LogonType>" in x and "<RunLevel>LeastPrivilege</RunLevel>" in x
    assert r"C:\p &amp; q\pythonw.exe" in x and " & " not in x  # las rutas, escapadas


# --- Lo que lanza Windows ---

def test_apagados_por_defecto_no_se_manda_nada(bd):
    envio = EnvioDeMentira()
    avisos.ejecutar(bd.parent.parent, LUNES, envio)
    assert envio.correos == [] and envio.notificaciones == [] and acciones(bd) == []


def test_el_lunes_manda_un_correo_lo_apunta_y_no_lo_repite(bd):
    activar(bd, para="carlos@empresa.com, directora@empresa.com")
    db.guardar_ajuste(bd, espacio(bd)["id"], avisos.CUENTA, "carlos@empresa.com")
    db.guardar_ajuste(bd, espacio(bd)["id"], avisos.MANDADO_MES, "2026-10-01")
    envio = EnvioDeMentira()
    avisos.ejecutar(bd.parent.parent, LUNES, envio)
    avisos.ejecutar(bd.parent.parent, LUNES, envio)  # al encender otra vez el mismo día
    assert len(envio.correos) == 1
    assert envio.correos[0]["para"] == ["carlos@empresa.com", "directora@empresa.com"]
    assert envio.correos[0]["cuenta"] == "carlos@empresa.com"
    assert envio.correos[0]["asunto"] == "[Portal ISO 42001 · General] Avisos: esta semana"
    assert envio.notificaciones == [("Portal ISO 42001 · General", "Esta semana no vence nada.")]
    assert db.ajuste(bd, espacio(bd)["id"], avisos.MANDADO_SEMANA, "") == "2026-10-05"
    assert [a for a, _ in acciones(bd)] == ["aviso"]


def test_si_el_dia_1_es_lunes_va_todo_en_un_solo_correo(bd):
    activar(bd)
    envio = EnvioDeMentira()
    avisos.ejecutar(bd.parent.parent, LUNES_DIA_1, envio)
    assert len(envio.correos) == 1 and "resumen del mes y esta semana" in envio.correos[0]["asunto"]
    e = espacio(bd)["id"]
    assert db.ajuste(bd, e, avisos.MANDADO_MES, "") == "2026-06-01"
    assert db.ajuste(bd, e, avisos.MANDADO_SEMANA, "") == "2026-06-01"


def test_si_el_correo_no_sale_queda_en_actividad_avisa_y_se_reintenta(bd):
    activar(bd)
    envio = EnvioDeMentira(falla="No hay Outlook clásico.")
    avisos.ejecutar(bd.parent.parent, LUNES, envio)
    assert acciones(bd) == [("aviso_fallido", "No hay Outlook clásico.")]
    assert envio.notificaciones[0][0] == "Portal ISO 42001 · General: el correo no ha salido"
    assert db.ajuste(bd, espacio(bd)["id"], avisos.MANDADO_SEMANA, "") == ""  # no cuenta como mandado
    bien = EnvioDeMentira()
    avisos.ejecutar(bd.parent.parent, date(2026, 10, 6), bien)  # al día siguiente, sí
    assert len(bien.correos) == 1


def test_sin_destinatarios_solo_sale_la_notificacion(bd):
    activar(bd, para="")
    envio = EnvioDeMentira()
    avisos.ejecutar(bd.parent.parent, LUNES, envio)
    # El 1 de octubre (jueves) aún no se había mandado: va con el lunes, en una sola notificación
    assert envio.correos == [] and envio.notificaciones == [
        ("Portal ISO 42001 · General", "Resumen del mes: todo al día; esta semana no vence nada.")]
    assert db.ajuste(bd, espacio(bd)["id"], avisos.MANDADO_SEMANA, "") == "2026-10-05"


# --- Recorridos: Ajustes ---

@pytest.fixture
def envio():
    return EnvioDeMentira(cuentas=["carlos@empresa.com", "otra@uni.edu"], programada=False)


@pytest.fixture
def cliente(bd, envio):
    with en_portal(bd, hoy=lambda: LUNES, envio=envio) as c:
        yield c


def test_en_ajustes_vienen_apagados_y_se_ve_la_seccion(cliente):
    html = cliente.get("/ajustes").text
    assert 'id="correo"' in html and 'name="activado" value="1" >' in html
    assert '<option value="carlos@empresa.com">' in html  # las cuentas del Outlook abierto
    assert "programar-avisos.bat" not in html  # solo se pide programar si están activados


def test_activarlos_guarda_desde_hoy_y_pide_programar_la_tarea(cliente, bd):
    r = cliente.post("/ajustes/correo", data={"activado": "1", "para": "a@x.com; b@y.com", "cuenta": " carlos@empresa.com "},
                     follow_redirects=False)
    assert r.headers["location"] == "/ajustes#correo"
    e = espacio(bd)["id"]
    assert db.ajuste(bd, e, avisos.ACTIVADOS, "") == "1" and db.ajuste(bd, e, avisos.DESDE, "") == "2026-10-05"
    assert db.ajuste(bd, e, avisos.PARA, "") == "a@x.com, b@y.com" and db.ajuste(bd, e, avisos.CUENTA, "") == "carlos@empresa.com"
    html = cliente.get("/ajustes").text
    assert "checked" in html.split('name="activado"')[1][:40] and "programar-avisos.bat" in html
    cliente.post("/ajustes/correo", data={"para": "a@x.com"})
    assert db.ajuste(bd, e, avisos.ACTIVADOS, "") == "0"


def test_volver_a_activarlos_no_cambia_desde_cuando(cliente, bd):
    e = espacio(bd)["id"]
    db.guardar_ajuste(bd, e, avisos.ACTIVADOS, "1")
    db.guardar_ajuste(bd, e, avisos.DESDE, "2026-01-01")
    cliente.post("/ajustes/correo", data={"activado": "1", "para": "a@x.com"})
    assert db.ajuste(bd, e, avisos.DESDE, "") == "2026-01-01"


def test_el_aviso_de_prueba_sale_y_queda_en_actividad_sin_contar_como_mandado(cliente, bd, envio):
    cliente.post("/ajustes/correo", data={"para": "carlos@empresa.com"})
    html = cliente.post("/ajustes/correo/prueba").text
    assert "Aviso mandado a carlos@empresa.com." in html
    assert len(envio.correos) == 1 and envio.correos[0]["asunto"].startswith("[Prueba] ")
    assert len(envio.notificaciones) == 1
    assert db.ajuste(bd, espacio(bd)["id"], avisos.MANDADO_SEMANA, "") == ""
    assert "aviso por correo mandado" in cliente.get("/actividad").text


def test_si_la_prueba_falla_se_ve_el_motivo(bd):
    with en_portal(bd, hoy=lambda: LUNES, envio=EnvioDeMentira(falla="Falta el Outlook clásico.")) as c:
        c.post("/ajustes/correo", data={"para": "carlos@empresa.com"})
        html = c.post("/ajustes/correo/prueba").text
    assert "Falta el Outlook clásico." in html and "mensaje-error" in html
