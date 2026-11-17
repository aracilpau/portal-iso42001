# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""La Declaración de Aplicabilidad: decidir, cambios, efecto en las cuentas y documento."""
import io
from datetime import date

import pytest
from docx import Document
from fastapi.testclient import TestClient

from portal import db, documento, guia
from portal.db import Decision, Marca
from portal.main import crear_app
from conftest import en_portal, entrar
from portal.seguimiento import APOYADO, PROPIO, VENCE_PRONTO, Seguimiento

DIA = date(2026, 3, 15)


def punto(codigo):
    return guia.punto(codigo)


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


@pytest.fixture
def cliente(bd):
    with en_portal(bd, hoy=lambda: DIA) as c:
        yield c


def decidir(cliente, control, aplica, porque="Porque sí"):
    return cliente.post(f"/declaracion/{control}", data={"aplica": aplica, "porque": porque})


# --- Piezas: las cuentas ---

def test_sin_decidir_cuenta_y_no_aplica_lo_saca():
    assert Seguimiento(set()).controles.total == 38
    est = Seguimiento(set(), excluidos={"A.10.3", "A.10.4"})
    assert est.controles.total == 36
    assert not est.aplica("A.10.3") and est.aplica("A.2.2")


def test_un_punto_apoyado_en_un_control_excluido_pasa_a_propio():
    p = punto("8.1.d")  # se apoya en A.10.3
    assert Seguimiento(set()).clase(p) == APOYADO
    est = Seguimiento({"8.1.d"}, excluidos={"A.10.3"})
    assert est.clase(p) == PROPIO
    assert est.cumplido(p)  # marcado a mano


def test_la_4_4_no_espera_a_los_controles_excluidos():
    est = Seguimiento(set(), excluidos={"A.10.3"})
    assert est.avance("4.4").total == 63  # 64 con puntos, menos el excluido


def test_un_control_excluido_sale_de_vencimientos_y_recomendados():
    marcas = {"A.2.2.b": Marca(DIA, vence_manual=date(2026, 3, 20))}  # recomendado de A.2.2
    est = Seguimiento(marcas, hoy=DIA)
    assert est.recomendados.hechos == 1 and est.avisos(VENCE_PRONTO)
    est = Seguimiento(marcas, hoy=DIA, excluidos={"A.2.2"})
    assert est.recomendados.total == 1  # quedan los de 4.3
    assert est.avisos(VENCE_PRONTO) == []


# --- Piezas: la base de datos ---

def test_decidir_apunta_la_primera_decision_y_los_cambios(bd):
    e = db.espacio(bd, "general")["id"]
    db.decidir(bd, e, "A.10.3", True, "Usamos la API de un proveedor", "", DIA)
    db.decidir(bd, e, "A.10.3", True, "Usamos la API de OpenAI", "", DIA)  # solo cambia el porqué
    db.decidir(bd, e, "A.10.3", False, "Ya no usamos proveedores", "Dejamos la API", date(2026, 6, 1))
    assert db.decisiones(bd, e)["A.10.3"] == Decision(False, "Ya no usamos proveedores", date(2026, 6, 1))
    cambios = [(c["antes"], c["ahora"], c["motivo"]) for c in db.cambios(bd, e)]
    assert cambios == [("aplica", "no aplica", "Dejamos la API"),
                       ("sin decidir", "aplica", "Usamos la API de un proveedor")]


# --- Recorridos: desde el navegador ---

def test_decidir_desde_la_declaracion(cliente):
    r = decidir(cliente, "A.2.2", "si", "Tenemos política de IA (5.2)")
    assert "Decididos <strong>1 de 38</strong> · aplican 1 · no aplican 0" in r.text
    assert "Quedan 37 controles del Anexo A sin decidir" in cliente.get("/").text
    ficha = cliente.get("/requisitos/A.2.2").text
    assert "Decidido: <strong>aplica</strong>. Tenemos política de IA (5.2)" in ficha


def test_sin_porque_o_sin_eleccion_no_se_guarda(cliente):
    r = decidir(cliente, "A.2.2", "si", "   ")
    assert "Falta el porqué" in r.text and "Decididos <strong>0 de 38</strong>" in r.text
    r = decidir(cliente, "A.2.2", "", "algo")
    assert "Falta elegir si aplica o no aplica." in r.text


def test_cambiar_un_control_apunta_el_porque_nuevo_como_motivo(cliente):
    decidir(cliente, "A.10.3", "si", "Usamos proveedores")
    r = decidir(cliente, "A.10.3", "no", "Se cancela el contrato con el proveedor")
    assert 'role="alert"' not in r.text
    cambios = cliente.get("/declaracion/cambios").text
    assert "Se cancela el contrato con el proveedor" in cambios and "aplica → <strong>no aplica</strong>" in cambios
    assert 'name="motivo"' not in cliente.get("/declaracion").text  # ya no hay cuadro aparte


def test_un_control_que_no_aplica_se_ve_pero_no_se_marca(cliente):
    decidir(cliente, "A.10.3", "no", "No usamos IA de terceros")
    ficha = cliente.get("/requisitos/A.10.3").text
    assert "No aplica a vuestra empresa." in ficha and "No usamos IA de terceros" in ficha
    assert "Marcar como cumplido" not in ficha
    assert cliente.post("/requisitos/A.10.3/puntos/A.10.3.a/marcar").status_code == 400
    assert "No aplica</span>" in cliente.get("/requisitos").text
    assert "0 de 37 que aplican" in cliente.get("/").text  # el Anexo A, sin la A.10.3


def test_excluir_la_a_10_3_deja_marcar_a_mano_la_8_1_d(cliente):
    assert cliente.post("/requisitos/8.1/puntos/8.1.d/marcar").status_code == 400  # apoyado
    decidir(cliente, "A.10.3", "no", "No usamos IA de terceros")
    ficha = cliente.get("/requisitos/8.1").text
    assert "ahora es trabajo propio" in ficha
    assert cliente.post("/requisitos/8.1/puntos/8.1.d/marcar").status_code == 200
    assert "/requisitos/8.1/puntos/8.1.d/desmarcar" in cliente.get("/requisitos/8.1").text


def test_descargar_el_documento_en_word_y_pdf(cliente):
    decidir(cliente, "A.2.2", "si", "Tenemos política de IA")
    word = cliente.get("/declaracion/documento/descargar", params={"formato": "word"})
    assert word.status_code == 200 and "Declaracion%20de%20Aplicabilidad%202026-03-15.docx" in word.headers["content-disposition"]
    tabla = Document(io.BytesIO(word.content)).tables[0]
    assert len(tabla.rows) == 39  # cabecera + 38 controles
    assert [c.text for c in tabla.rows[1].cells][:3] == ["A.2.2", guia.requisito("A.2.2").titulo, "Aplica"]
    pdf = cliente.get("/declaracion/documento/descargar", params={"formato": "pdf"})
    assert pdf.content.startswith(b"%PDF")
    assert cliente.get("/declaracion/documento/descargar", params={"formato": "odt"}).status_code == 400
    assert "Aún no hay versiones anteriores." in cliente.get("/requisitos/6.1.3").text  # descargar no guarda


def test_guardar_como_prueba_y_la_anterior_al_historial(cliente):
    r = cliente.post("/declaracion/documento/guardar", data={"formato": "word"})
    assert "Guardado como «Declaracion de Aplicabilidad 2026-03-15.docx»" in r.text
    cliente.post("/declaracion/documento/guardar", data={"formato": "pdf"})
    ficha = cliente.get("/requisitos/6.1.3").text
    assert "/archivos/Declaracion%20de%20Aplicabilidad%202026-03-15.pdf" in ficha
    assert 'data-nombre="6.1.3.c - 2026-03-15 - Declaracion de Aplicabilidad 2026-03-15.docx"' in ficha


def test_guardar_la_declaracion_no_toca_otros_archivos_de_la_6_1_3_c(cliente):
    cliente.post("/requisitos/6.1.3/puntos/6.1.3.c/archivos",
                 files=[("archivos", ("acta comite.pdf", b"acta", "application/pdf"))])
    cliente.post("/declaracion/documento/guardar", data={"formato": "pdf"})
    cliente.post("/declaracion/documento/guardar", data={"formato": "pdf"})
    ficha = cliente.get("/requisitos/6.1.3").text
    assert "/archivos/acta%20comite.pdf" in ficha


def test_el_documento_avisa_de_lo_que_queda_sin_decidir():
    fs = documento.filas({})
    assert len(fs) == 38 and all(f.aplica == "Sin decidir" for f in fs)
    assert "Quedan 38 sin decidir" in documento._resumen(fs)


def test_al_cambiar_hay_que_escribir_un_porque_nuevo(cliente):
    # Pasaba: A.2.2 quedaba «no aplica» con el porqué de cuando aplicaba
    decidir(cliente, "A.2.2", "si", "porque si")
    r = decidir(cliente, "A.2.2", "no", "porque si")
    assert "Falta el porqué nuevo" in r.text
    r = decidir(cliente, "A.2.2", "no", "Usamos la política de grupo")
    assert "Último cambio, el 15/03/2026: aplica → no aplica · Usamos la política de grupo" in r.text
    assert cliente.get("/requisitos/A.2.2").text.count("Usamos la política de grupo") == 1


def test_cambiar_solo_el_porque_no_pide_motivo(cliente):
    decidir(cliente, "A.2.2", "si", "porque si")
    r = decidir(cliente, "A.2.2", "si", "Tenemos política aprobada")
    assert 'role="alert"' not in r.text  # sin mensaje de error
    assert "Tenemos política aprobada" in r.text


def test_si_falta_algo_no_se_pierde_lo_escrito(cliente):
    # Pasaba: al avisar, el control volvía a «aplica» con el porqué viejo y se perdía lo escrito
    decidir(cliente, "A.2.2", "si", "Tenemos política")
    r = decidir(cliente, "A.2.2", "no", "Tenemos política")  # el porqué de antes
    assert "Falta el porqué nuevo" in r.text
    assert 'value="no" checked' in r.text  # se queda la opción elegida
    r = decidir(cliente, "A.2.2", "no", "  ")
    assert "Falta el porqué" in r.text and 'value="no" checked' in r.text
    r = decidir(cliente, "A.2.2", "no", "Usamos la del grupo")
    assert 'role="alert"' not in r.text and "aplica → no aplica · Usamos la del grupo" in r.text


# --- El porqué se guarda al dejar de escribir, sin dejar motivos a medias ---

HX = {"HX-Request": "true"}


def solo(cliente, control, aplica, porque, origen):
    """Lo que manda la página al guardarse sola: al elegir la opción, al dejar de escribir o al salir del cuadro."""
    return cliente.post(f"/declaracion/{control}", headers=HX,
                        data={"aplica": aplica, "porque": porque, "auto": "1", "origen": origen})


def estado_de(html, control):
    import re
    return re.search(rf'<span id="guardado-{control}"[^>]*class="([^"]*)"[^>]*>(.*?)</span>', html, re.S).groups()


def test_al_cambiar_la_opcion_se_avisa_de_que_falta_el_porque(cliente):
    decidir(cliente, "A.10.4", "si", "Tenemos clientes que usan nuestra IA.")
    r = solo(cliente, "A.10.4", "no", "Tenemos clientes que usan nuestra IA.", "aplica")  # aún con el porqué de antes
    clase, texto = estado_de(r.text, "A.10.4")
    assert "guardado-pista" in clase and "guardado-falta" not in clase  # destacado, pero no es un error
    assert texto.strip() == "Escribe el porqué nuevo: se guarda solo."
    assert r.headers["HX-Reswap"] == "none"
    # Al salir del cuadro sin escribirlo, sí es que falta algo: en naranja
    r = solo(cliente, "A.10.4", "no", "", "")
    clase, texto = estado_de(r.text, "A.10.4")
    assert "guardado-falta" in clase and "Para guardarlo falta el porqué" in texto


def test_al_dejar_de_escribir_se_guarda_sin_volver_a_pintar_el_control(cliente, bd):
    decidir(cliente, "A.10.4", "si", "Tenemos clientes que usan nuestra IA.")
    r = solo(cliente, "A.10.4", "no", "Ya no", "porque")
    assert r.headers["HX-Reswap"] == "none"  # no se saca a nadie del cuadro
    clase, texto = estado_de(r.text, "A.10.4")
    assert "guardado-falta" not in clase and texto.strip().startswith("Guardado a las ")
    assert db.decisiones(bd, 1)["A.10.4"].aplica is False


def test_escribir_el_porque_en_varios_trozos_deja_una_sola_linea(cliente, bd):
    decidir(cliente, "A.10.4", "si", "Tenemos clientes que usan nuestra IA.")
    for trozo in ("Ya no", "Ya no tenemos clientes", "Ya no tenemos clientes que usen IA."):
        solo(cliente, "A.10.4", "no", trozo, "porque")
    solo(cliente, "A.10.4", "no", "Ya no tenemos clientes que usen IA.", "")  # y al salir del cuadro

    cambios = [c for c in db.cambios(bd, 1) if c["control"] == "A.10.4"]
    assert [(c["antes"], c["ahora"], c["motivo"]) for c in cambios[:1]] == [
        ("aplica", "no aplica", "Ya no tenemos clientes que usen IA.")]
    assert len(cambios) == 2  # el primero (sin decidir → aplica) y este
    lineas = [(a["accion"], a["detalle"]) for a in db.actividad(bd, 1, "A.10.4")]
    assert lineas == [("no_aplica", "Ya no tenemos clientes que usen IA."),
                      ("aplica", "Tenemos clientes que usan nuestra IA.")]


def test_pasado_un_rato_corregir_el_porque_es_una_linea_nueva(cliente, bd):
    import sqlite3
    decidir(cliente, "A.10.4", "no", "Sin clientes con IA.")
    con = sqlite3.connect(bd)
    with con:
        con.execute("UPDATE actividad SET cuando = '2026-03-14T08:00:00'")  # el día antes: más de 10 minutos
    con.close()
    solo(cliente, "A.10.4", "no", "Sin clientes con IA: lo revisamos cada año.", "porque")
    lineas = [a["detalle"] for a in db.actividad(bd, 1, "A.10.4")]
    assert lineas == ["Sin clientes con IA: lo revisamos cada año.", "Sin clientes con IA."]
    # El motivo del cambio de entonces no se toca
    assert [c["motivo"] for c in db.cambios(bd, 1) if c["control"] == "A.10.4"] == ["Sin clientes con IA."]


# --- Desmarcar: volver a pulsar la opción marcada deja el control sin decidir ---

def test_quitar_la_decision_la_apunta_en_los_cambios(bd):
    db.decidir(bd, 1, "A.10.3", False, "Sin proveedores.", "", DIA)
    assert db.quitar_decision(bd, 1, "A.10.3", DIA)
    assert "A.10.3" not in db.decisiones(bd, 1)
    ultimo = db.cambios(bd, 1)[0]
    assert (ultimo["antes"], ultimo["ahora"], ultimo["motivo"]) == ("no aplica", "sin decidir", "Se deja sin decidir")
    assert not db.quitar_decision(bd, 1, "A.10.3", DIA)          # ya sin decidir: no hace nada
    assert len(db.cambios(bd, 1)) == 2


def test_desmarcar_desde_la_declaracion(cliente, bd, tmp_path):
    base = tmp_path / "general" / "pruebas"
    decidir(cliente, "A.10.3", "no", "Sin proveedores de IA.")
    assert (base / "A.10.3 (no aplica)").is_dir()
    r = cliente.post("/declaracion/A.10.3", data={"aplica": "", "porque": "Sin proveedores de IA.", "auto": "1",
                                                  "origen": "aplica", "quitar": "1"},
                     headers={"HX-Request": "true"})
    assert "A.10.3" not in db.decisiones(bd, 1)
    i = r.text.index('id="control-A.10.3"')
    control = r.text[i:r.text.index("</li>", i)]
    assert "Sin decidir" in control and "Sin proveedores de IA.</textarea>" in control   # el porqué se queda
    assert "Falta" not in control
    assert (base / "A.10.3").is_dir() and not (base / "A.10.3 (no aplica)").exists()
    assert "no aplica → <strong>sin decidir</strong>" in cliente.get("/declaracion/cambios").text
    assert "vuelto a sin decidir" in cliente.get("/actividad").text


def test_sin_quitar_una_opcion_vacia_sigue_pidiendo_que_se_elija(cliente, bd):
    decidir(cliente, "A.10.3", "no", "Sin proveedores de IA.")
    r = cliente.post("/declaracion/A.10.3", data={"aplica": "", "porque": "x"})
    assert "elegir si aplica o no aplica" in r.text and "A.10.3" in db.decisiones(bd, 1)
