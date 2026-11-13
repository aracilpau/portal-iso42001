# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Las pruebas: carpetas, subir, abrir, quitar, historial y renovar con archivo nuevo."""
import io
from datetime import date

import pytest
from fastapi.testclient import TestClient

from portal import db, guia
from portal.main import crear_app
from conftest import en_portal, entrar
from portal.pruebas import NoEncontrado, Pruebas, nombre_seguro

DIA = date(2026, 3, 15)


@pytest.fixture
def carpetas(tmp_path):
    c = Pruebas(tmp_path / "pruebas", "general")
    c.crear()
    return c


@pytest.fixture
def cliente(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    with en_portal(ruta, hoy=lambda: DIA) as c:
        yield c


def subir(cliente, punto, *archivos, ruta="archivos"):
    codigo = punto.rsplit(".", 1)[0]
    ficheros = [("archivos", (nombre, contenido, "application/octet-stream")) for nombre, contenido in archivos]
    return cliente.post(f"/requisitos/{codigo}/puntos/{punto}/{ruta}", files=ficheros)


# --- Piezas: las carpetas ---

def test_se_crean_las_carpetas_de_los_65_requisitos(carpetas):
    reqs = [d.name for d in carpetas.base.iterdir()]
    assert len(reqs) == 65
    assert (carpetas.base / "5.2" / "5.2.a").is_dir()
    assert not (carpetas.base / "7.3" / "7.3.a").exists()  # apoyado: sus archivos están en la 5.2
    assert (carpetas.base / "A.5.4" / "A.5.4.a").is_dir()  # por sistema: tiene carpeta
    assert (carpetas.base / "4.4").is_dir()                # sin puntos, pero con carpeta


def test_crear_otra_vez_no_toca_lo_que_hay(carpetas):
    carpetas.guardar("5.2.a", "politica.pdf", io.BytesIO(b"v1"))
    carpetas.crear()
    assert [a.nombre for a in carpetas.archivos("5.2.a")] == ["politica.pdf"]


def test_un_nombre_repetido_no_pisa_al_anterior(carpetas):
    assert carpetas.guardar("5.2.a", "politica.pdf", io.BytesIO(b"v1")) == "politica.pdf"
    assert carpetas.guardar("5.2.a", "politica.pdf", io.BytesIO(b"v2")) == "politica (2).pdf"
    assert (carpetas.carpeta("5.2.a") / "politica.pdf").read_bytes() == b"v1"


def test_los_nombres_trucados_no_salen_de_la_carpeta(carpetas):
    assert nombre_seguro("../../malo.pdf") == "malo.pdf"
    assert nombre_seguro("C:\\Users\\x\\informe.docx") == "informe.docx"
    assert nombre_seguro('a:b*c?.pdf') == "a_b_c_.pdf"
    assert nombre_seguro("..") == "archivo"
    carpetas.guardar("5.2.a", "../../malo.pdf", io.BytesIO(b"x"))
    assert (carpetas.carpeta("5.2.a") / "malo.pdf").exists()
    with pytest.raises(NoEncontrado):
        carpetas.ruta("5.2.a", "../../5.2/5.2.a/malo.pdf")


def test_los_temporales_de_office_no_se_ven(carpetas):
    (carpetas.carpeta("5.2.a") / "~$politica.docx").write_bytes(b"x")
    assert carpetas.archivos("5.2.a") == []


def test_quitar_lo_manda_al_historial_con_el_punto_y_el_dia(carpetas):
    carpetas.guardar("5.2.a", "politica.pdf", io.BytesIO(b"v1"))
    assert carpetas.quitar("5.2.a", "politica.pdf", DIA) == "5.2.a - 2026-03-15 - politica.pdf"
    assert carpetas.archivos("5.2.a") == []
    assert [a.nombre for a in carpetas.historial("5.2")] == ["5.2.a - 2026-03-15 - politica.pdf"]


def test_sustituir_manda_todos_al_historial(carpetas):
    carpetas.guardar("5.2.a", "a.pdf", io.BytesIO(b"1"))
    carpetas.guardar("5.2.a", "b.pdf", io.BytesIO(b"2"))
    assert len(carpetas.sustituir("5.2.a", DIA)) == 2
    assert carpetas.archivos("5.2.a") == [] and len(carpetas.historial("5.2")) == 2


def test_solo_se_borra_desde_el_historial(carpetas):
    carpetas.guardar("5.2.a", "politica.pdf", io.BytesIO(b"v1"))
    with pytest.raises(NoEncontrado):
        carpetas.borrar("5.2", "politica.pdf")  # no está en el historial
    nombre = carpetas.quitar("5.2.a", "politica.pdf", DIA)
    carpetas.borrar("5.2", nombre)
    assert carpetas.historial("5.2") == []


# --- Recorridos: desde el navegador ---

def test_subir_abrir_y_ver_en_la_ficha(cliente):
    r = subir(cliente, "5.2.a", ("política IA.pdf", b"%PDF-1.4 hola"), ("acta.docx", b"word"))
    assert r.status_code == 200
    ficha = cliente.get("/requisitos/5.2").text
    assert "política IA.pdf" in ficha and "acta.docx" in ficha
    assert "0 de 6 puntos" in ficha  # subir no marca

    pdf = cliente.get("/requisitos/5.2/puntos/5.2.a/archivos/política IA.pdf")
    assert pdf.status_code == 200 and pdf.content == b"%PDF-1.4 hola"
    assert pdf.headers["content-disposition"].startswith("inline")      # se ve en el navegador
    word = cliente.get("/requisitos/5.2/puntos/5.2.a/archivos/acta.docx")
    assert word.headers["content-disposition"].startswith("attachment")  # se descarga


def test_quitar_avisa_y_borrar_desde_el_historial(cliente):
    subir(cliente, "5.2.a", ("politica.pdf", b"v1"))
    r = cliente.post("/requisitos/5.2/puntos/5.2.a/archivos/politica.pdf/quitar")
    assert "Se ha movido a versiones anteriores como «5.2.a - 2026-03-15 - politica.pdf»" in r.text
    assert 'data-nombre="5.2.a - 2026-03-15 - politica.pdf"' in r.text  # está en el historial
    assert cliente.get("/requisitos/5.2/historial/5.2.a - 2026-03-15 - politica.pdf").content == b"v1"

    r = cliente.post("/requisitos/5.2/historial/5.2.a - 2026-03-15 - politica.pdf/borrar")
    assert "se ha borrado para siempre" in r.text
    assert "Aún no hay versiones anteriores." in r.text


def test_renovar_con_archivo_nuevo(cliente):
    cliente.post("/requisitos/5.2/puntos/5.2.a/marcar")
    subir(cliente, "5.2.a", ("politica-2026.pdf", b"v1"))
    # Un solo «Renovar»: subir versión nueva lo dice al pasar el ratón
    assert "y el punto se renueva desde hoy" in cliente.get("/requisitos/5.2").text
    subir(cliente, "5.2.a", ("politica-2027.pdf", b"v2"), ruta="renovar")
    ficha = cliente.get("/requisitos/5.2").text
    assert 'data-nombre="5.2.a - 2026-03-15 - politica-2026.pdf"' in ficha  # la vieja, al historial
    assert "/archivos/politica-2027.pdf" in ficha
    assert "Vence el 15/03/2027" in ficha


def test_renovar_sin_archivo_no_toca_los_archivos(cliente):
    cliente.post("/requisitos/5.2/puntos/5.2.a/marcar")
    subir(cliente, "5.2.a", ("politica.pdf", b"v1"))
    cliente.post("/requisitos/5.2/puntos/5.2.a/renovar")
    ficha = cliente.get("/requisitos/5.2").text
    assert "/archivos/politica.pdf" in ficha and "Aún no hay versiones anteriores." in ficha


def test_lo_que_no_existe_o_no_toca_da_error(cliente):
    assert cliente.get("/requisitos/5.2/puntos/5.2.a/archivos/nada.pdf").status_code == 404
    assert cliente.post("/requisitos/5.2/puntos/5.2.a/archivos/nada.pdf/quitar").status_code == 404
    assert cliente.post("/requisitos/5.2/historial/nada.pdf/borrar").status_code == 404
    assert subir(cliente, "7.3.a", ("x.pdf", b"x")).status_code == 400  # apoyado: sin archivos propios


def test_las_pruebas_de_un_portal_de_prueba_no_van_a_los_datos_reales(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    with en_portal(ruta):
        pass
    assert (tmp_path / "general" / "pruebas" / "5.2").is_dir()


def test_los_pdf_se_abren_sin_proteccion_y_los_svg_con_ella(cliente):
    # Con la protección «sandbox», el visor de PDF de Chrome se queda en gris
    subir(cliente, "5.2.a", ("politica.pdf", b"%PDF-1.4"), ("dibujo.svg", b"<svg/>"))
    pdf = cliente.get("/requisitos/5.2/puntos/5.2.a/archivos/politica.pdf")
    assert "content-security-policy" not in pdf.headers
    svg = cliente.get("/requisitos/5.2/puntos/5.2.a/archivos/dibujo.svg")
    assert svg.headers["content-security-policy"] == "sandbox"



def test_subir_version_nueva_en_lo_que_no_vence(cliente):
    # La 6.3 es «por evento», no vence; antes no había forma de cambiar el archivo de un paso
    cliente.post("/requisitos/6.3/puntos/6.3.c/marcar")
    subir(cliente, "6.3.c", ("plan-v1.pdf", b"v1"))
    ficha = cliente.get("/requisitos/6.3").text
    assert "Subir versión nueva" in ficha and "Subir versión nueva y renovar" not in ficha
    assert "No vence por fecha" in ficha and "revisado el 15/03/2026" in ficha
    subir(cliente, "6.3.c", ("plan-v2.pdf", b"v2"), ruta="version")
    ficha = cliente.get("/requisitos/6.3").text
    assert "/archivos/plan-v2.pdf" in ficha
    assert 'data-nombre="6.3.c - 2026-03-15 - plan-v1.pdf"' in ficha


def test_version_nueva_sin_marcar_no_marca(cliente):
    subir(cliente, "5.2.a", ("politica-v1.pdf", b"v1"))
    subir(cliente, "5.2.a", ("politica-v2.pdf", b"v2"), ruta="version")
    ficha = cliente.get("/requisitos/5.2").text
    assert "0 de 6 puntos" in ficha and "/archivos/politica-v2.pdf" in ficha


# --- Las carpetas de los controles que no aplican ---

def test_un_control_que_no_aplica_lleva_la_marca_con_todo_dentro(carpetas):
    carpetas.guardar("A.7.3.a", "origen-datos.pdf", io.BytesIO(b"pdf"))
    carpetas.quitar("A.7.3.a", "origen-datos.pdf", DIA)  # algo en el historial
    carpetas.guardar("A.7.3.a", "nuevo.pdf", io.BytesIO(b"pdf"))

    assert carpetas.poner_al_dia({"A.7.3"}) == []
    assert not (carpetas.base / "A.7.3").exists()
    assert (carpetas.base / "A.7.3 (no aplica)" / "A.7.3.a" / "nuevo.pdf").is_file()
    # El portal la sigue encontrando: archivos e historial
    assert [a.nombre for a in carpetas.archivos("A.7.3.a")] == ["nuevo.pdf"]
    assert len(carpetas.historial("A.7.3")) == 1

    assert carpetas.poner_al_dia(set()) == []  # vuelve a aplicar: recupera el nombre
    assert (carpetas.base / "A.7.3" / "A.7.3.a" / "nuevo.pdf").is_file()
    assert not (carpetas.base / "A.7.3 (no aplica)").exists()


def test_al_crear_no_se_duplica_la_carpeta_marcada(carpetas):
    carpetas.poner_al_dia({"A.7.3"})
    carpetas.crear()
    assert not (carpetas.base / "A.7.3").exists()
    assert len(list(carpetas.base.iterdir())) == 65


def test_un_portal_nuevo_crea_ya_marcados_los_que_no_aplican(tmp_path):
    c = Pruebas(tmp_path / "pruebas", "general")
    c.poner_al_dia({"A.7.3"})
    c.crear()
    assert (c.base / "A.7.3 (no aplica)" / "A.7.3.a").is_dir() and not (c.base / "A.7.3").exists()


def test_con_la_carpeta_ocupada_no_se_pierde_nada(carpetas, monkeypatch):
    carpetas.guardar("A.7.3.a", "abierto.docx", io.BytesIO(b"doc"))
    original = type(carpetas.base).rename

    def ocupada(self, destino):  # lo que hace Windows si hay un archivo de dentro abierto
        if self.name == "A.7.3":
            raise PermissionError("en uso")
        return original(self, destino)

    monkeypatch.setattr(type(carpetas.base), "rename", ocupada)
    assert carpetas.poner_al_dia({"A.7.3", "A.7.4"}) == ["A.7.3"]
    assert (carpetas.base / "A.7.4 (no aplica)").is_dir()  # las demás, sí
    assert [a.nombre for a in carpetas.archivos("A.7.3.a")] == ["abierto.docx"]  # se sigue viendo

    monkeypatch.undo()  # se cierra el archivo: a la próxima, sí
    assert carpetas.poner_al_dia({"A.7.3", "A.7.4"}) == []
    assert (carpetas.base / "A.7.3 (no aplica)" / "A.7.3.a" / "abierto.docx").is_file()


# --- Recorrido: desde la Declaración ---

def test_excluir_y_volver_a_incluir_desde_la_declaracion(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    base = tmp_path / "general" / "pruebas"
    with en_portal(ruta, hoy=lambda: DIA) as cliente:
        subir(cliente, "A.3.3.a", ("roles.pdf", b"pdf"))  # un punto propio
        cliente.post("/declaracion/A.3.3", data={"aplica": "no", "porque": "Somos pocos: no hay canal aparte."})
        assert (base / "A.3.3 (no aplica)" / "A.3.3.a" / "roles.pdf").is_file()
        cliente.post("/declaracion/A.3.3", data={"aplica": "si", "porque": "Ya somos más."})
        assert (base / "A.3.3" / "A.3.3.a" / "roles.pdf").is_file()
        assert "roles.pdf" in cliente.get("/requisitos/A.3.3").text  # y la ficha lo vuelve a enseñar

    # Al arrancar, se pone al día: p. ej. controles excluidos antes de existir la marca
    db.decidir(ruta, db.espacio(ruta, "general")["id"], "A.7.4", False, "Sin datos propios.", "", DIA)
    with en_portal(ruta, hoy=lambda: DIA) as cliente:
        assert (base / "A.7.4 (no aplica)").is_dir() and not (base / "A.7.4").exists()


def test_si_la_carpeta_esta_ocupada_la_decision_se_guarda_y_lo_dice(cliente, monkeypatch):
    from pathlib import Path
    original = Path.rename
    monkeypatch.setattr(Path, "rename", lambda self, d: (_ for _ in ()).throw(PermissionError("en uso"))
                        if self.name == "A.7.3" else original(self, d))
    r = cliente.post("/declaracion/A.7.3", data={"aplica": "no", "porque": "No entrenamos modelos.", "auto": "1"},
                     headers={"HX-Request": "true"})
    assert "Guardado, pero la carpeta no se ha podido renombrar: cierra los archivos de A.7.3." in r.text
    assert "Decididos <strong>1 de 38</strong>" in r.text
