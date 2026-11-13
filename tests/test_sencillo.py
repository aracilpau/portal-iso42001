# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El portal más sencillo de usar."""
import re
from datetime import date

import pytest
from fastapi.testclient import TestClient

from portal import db, guia
from portal.main import crear_app
from conftest import en_portal, entrar

DIA = date(2026, 3, 15)


@pytest.fixture
def cliente(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    with en_portal(ruta, hoy=lambda: DIA) as c:
        yield c


def completar_4_3(cliente):
    for p in ("4.3.a", "4.3.b", "4.3.c"):
        cliente.post(f"/requisitos/4.3/puntos/{p}/marcar")


# --- Solo pendientes ---

def test_solo_pendientes_quita_los_completos_y_los_que_no_aplican(cliente):
    completar_4_3(cliente)
    cliente.post("/declaracion/A.10.3", data={"aplica": "no", "porque": "No usamos proveedores de IA."})
    todos = cliente.get("/requisitos").text
    assert 'href="/requisitos/4.3"' in todos and 'href="/requisitos/A.10.3"' in todos

    pendientes = cliente.get("/requisitos?ver=pendientes").text
    assert 'href="/requisitos/4.3"' not in pendientes      # completo
    assert 'href="/requisitos/A.10.3"' not in pendientes   # no aplica
    assert 'href="/requisitos/4.1"' in pendientes
    assert 'class="on" aria-current="page">Pendientes' in pendientes


def test_un_bloque_sin_pendientes_no_sale(cliente):
    cliente.post("/declaracion/A.10.2", data={"aplica": "no", "porque": "Sin terceros."})
    cliente.post("/declaracion/A.10.3", data={"aplica": "no", "porque": "Sin proveedores."})
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA."})
    assert "A.10 Terceros y clientes" not in cliente.get("/requisitos?ver=pendientes").text


# --- Ajustes: lo general a la vista y lo demás plegado ---

def test_ajustes_pliega_lo_que_casi_no_se_toca(cliente):
    html = cliente.get("/ajustes").text
    avanzadas = html.index('<details class="avanzadas"')
    for general in ('id="que-avisa"', 'id="preguntar"', 'id="revision"'):
        assert html.index(general) < avanzadas
    for avanzado in ('id="antelacion"', "Fechas de los puntos cumplidos", 'id="plazos"'):
        assert html.index(avanzado) > avanzadas


def test_ya_no_se_recoloca_a_mano_el_proximo_recordatorio(cliente):
    assert 'name="proximo"' not in cliente.get("/ajustes").text
    assert cliente.post("/ajustes/recordatorio/10.1/proximo", data={"proximo": "15/03/2026"}).status_code in (404, 405)


# --- La ficha ---

def test_el_historial_de_un_punto_se_ve_junto_a_sus_archivos(cliente):
    ficheros = [("archivos", ("politica.pdf", b"v1", "application/pdf"))]
    cliente.post("/requisitos/5.2/puntos/5.2.a/archivos", files=ficheros)
    assert "Versiones anteriores (" not in cliente.get("/requisitos/5.2").text
    cliente.post("/requisitos/5.2/puntos/5.2.a/archivos/politica.pdf/quitar")
    ficha = cliente.get("/requisitos/5.2").text
    assert 'href="#historial">Versiones anteriores (1)</a>' in ficha
    assert ficha.count('href="#historial">Versiones anteriores (') == 1  # solo en su punto, no en los demás


def test_el_reparto_explica_lo_que_va_por_sistema(cliente):
    ficha = cliente.get("/requisitos/8.4").text
    assert "una vez por cada sistema de IA del inventario" in ficha


def test_al_guardar_la_nota_se_ve_que_se_ha_guardado(cliente):
    assert "Nota guardada." not in cliente.get("/requisitos/5.2").text
    r = cliente.post("/requisitos/5.2/nota", data={"texto": "La lleva Ana, en la carpeta de Dirección."})
    assert "Nota guardada." in r.text and "La lleva Ana" in r.text
    assert "Nota guardada." not in cliente.get("/requisitos/5.2").text  # al volver a entrar, ya no



# --- La casilla y un solo «Renovar» ---

def test_el_punto_se_marca_y_desmarca_con_su_casilla(cliente):
    ficha = cliente.get("/requisitos/4.3").text
    assert 'aria-checked="false"' in ficha and 'aria-label="Marcar como cumplido 4.3.a"' in ficha
    assert ">Marcar como cumplido<" not in ficha and ">Desmarcar<" not in ficha  # ya no hay botones con texto

    ficha = cliente.post("/requisitos/4.3/puntos/4.3.a/marcar").text
    assert 'aria-label="Desmarcar 4.3.a"' in ficha and "casilla casilla-marcada" in ficha
    assert ">Renovar</button>" in ficha  # al estar marcado y vencer, un solo «Renovar»

    ficha = cliente.post("/requisitos/4.3/puntos/4.3.a/desmarcar").text
    assert 'aria-label="Marcar como cumplido 4.3.a"' in ficha and ">Renovar</button>" not in ficha


def test_las_lineas_de_cada_sistema_tambien_llevan_casilla(cliente):
    r = cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    x = r.url.path.rsplit("/", 1)[1]
    assert 'aria-label="Marcar como cumplido 8.4.a en ChatGPT"' in cliente.get("/requisitos/8.4").text
    ficha = cliente.post(f"/requisitos/8.4/puntos/8.4.a/sistemas/{x}/marcar").text
    assert 'aria-label="Desmarcar 8.4.a en ChatGPT"' in ficha


def test_ya_no_hay_otras_formas_de_renovar(cliente):
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    ficha = cliente.get("/requisitos/4.3").text
    assert "Ya está renovado" not in ficha and "Subir versión nueva y renovar" not in ficha


# --- Archivos arrastrando y «+ Archivo» ---

def test_cada_punto_y_cada_linea_es_una_zona_para_soltar_archivos(cliente):
    ficha = cliente.get("/requisitos/5.2").text
    assert 'data-soltar="/requisitos/5.2/puntos/5.2.a/archivos" data-soltar-que="5.2.a"' in ficha
    assert ">+ Archivo" in ficha and "Subir archivo" not in ficha
    assert "data-soltar=" not in cliente.get("/requisitos/7.3").text.split('id="7.3.a"')[1].split("</li>")[0]  # se cumple solo

    r = cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    x = r.url.path.rsplit("/", 1)[1]
    ficha = cliente.get("/requisitos/8.4").text
    assert f'data-soltar="/requisitos/8.4/puntos/8.4.a/sistemas/{x}/archivos" data-soltar-que="8.4.a · ChatGPT"' in ficha


def test_soltar_varios_archivos_a_la_vez_los_sube_todos(cliente):
    # Lo mismo que hace el navegador al soltar: un envío con varios archivos a la zona
    ficheros = [("archivos", ("acta.pdf", b"1", "application/pdf")), ("archivos", ("anexo.docx", b"2", "application/octet-stream"))]
    ficha = cliente.post("/requisitos/5.2/puntos/5.2.a/archivos", files=ficheros).text
    assert "/archivos/acta.pdf" in ficha and "/archivos/anexo.docx" in ficha and 'id="ficha"' in ficha


# --- Sin botones de «Guardar» ---

HX = {"HX-Request": "true"}


def test_la_nota_se_guarda_sola_y_solo_cambia_el_aviso(cliente):
    ficha = cliente.get("/requisitos/5.2").text
    assert 'hx-trigger="input changed delay:1s, change"' in ficha and "<noscript><button class=\"boton boton-mini\" type=\"submit\">Guardar nota" in ficha
    r = cliente.post("/requisitos/5.2/nota", data={"texto": "La lleva Ana."}, headers=HX)
    assert r.text.startswith('<span id="nota-estado"') and "Guardado a las" in r.text  # no se repinta lo escrito
    assert "La lleva Ana." in cliente.get("/requisitos/5.2").text


def test_la_ficha_de_un_sistema_se_guarda_sola(cliente):
    r = cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    x = r.url.path.rsplit("/", 1)[1]
    datos = {"nombre": "ChatGPT", "tipo": "herramienta", "datos": "Lo que escribe la plantilla.", "auto": "1"}
    r = cliente.post(f"/inventario/{x}", data=datos, headers=HX)
    assert r.status_code == 200 and "Guardado a las" in r.text  # se queda en la ficha
    assert 'id="estado-datos" hx-swap-oob="true" class="sello s-ok"' in r.text  # el estado se pone al día
    assert "1 de 5 campos" in r.text
    assert "<b>1/5</b>" in cliente.get("/inventario").text

    # Sin cambios no se apunta otra vez en «Actividad»
    cliente.post(f"/inventario/{x}", data=datos, headers=HX)
    assert cliente.get("/actividad").text.count("ficha del sistema guardada") == 1


def test_la_ficha_de_un_sistema_con_un_error_no_se_guarda(cliente):
    r = cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    x = r.url.path.rsplit("/", 1)[1]
    r = cliente.post(f"/inventario/{x}", data={"nombre": "", "tipo": "herramienta", "auto": "1"}, headers=HX)
    assert "Falta el nombre." in r.text and "guardado-falta" in r.text
    assert "ChatGPT" in cliente.get("/inventario").text


def test_la_declaracion_se_guarda_sola_cuando_esta_completa(cliente):
    # Solo con la opción elegida, falta el porqué: no se guarda y no se toca lo escrito
    r = cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "", "auto": "1"}, headers=HX)
    assert r.headers.get("HX-Reswap") == "none"
    assert "Para guardarlo falta el porqué" in r.text and 'class="guardado-estado guardado-falta"' in r.text
    assert "Decididos <strong>0 de 38</strong>" in cliente.get("/declaracion").text

    # Con el porqué, se guarda y se repinta ese control y el contador
    r = cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA.", "auto": "1"}, headers=HX)
    assert "HX-Reswap" not in r.headers and "Decididos <strong>1 de 38</strong>" in r.text
    assert re.search(r'id="guardado-A.10.4"[^>]*>Guardado</span>', r.text)
    assert cliente.get("/actividad").text.count("decidido: no aplica") == 1
    cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "Sin clientes con IA.", "auto": "1"}, headers=HX)
    assert cliente.get("/actividad").text.count("decidido: no aplica") == 1  # sin cambios, no se apunta otra vez


def test_ningun_selector_de_htmx_apunta_a_un_id_con_puntos(cliente):
    # «#control-A.10.4» no funciona en el navegador: el punto se lee como otra cosa
    cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    respuestas = [cliente.get(u).text for u in ("/", "/requisitos", "/requisitos/4.3", "/requisitos/8.4", "/declaracion",
                                                "/inventario", "/inventario/1", "/ajustes", "/eventos", "/actividad")]
    respuestas.append(cliente.post("/declaracion/A.10.4", data={"aplica": "no", "porque": "", "auto": "1"},
                                   headers={"HX-Request": "true"}).text)
    for html in respuestas:
        for atributo in re.findall(r'hx-(?:target|select|select-oob|swap-oob)="([^"]*)"', html):
            assert not re.search(r"#[\w-]*\.", atributo), atributo


# --- El menú solo con sitios ---

def menu(html):
    return html[html.index('<nav class="nav"'):html.index("</nav>")]


def test_el_menu_solo_tiene_sitios(cliente):
    m = menu(cliente.get("/").text)
    assert 'href="/eventos' not in m and "Avisos" not in m
    for sitio in ("Inicio", "Empresa", "Requisitos", "Declaración", "Actividad"):
        assert f">{sitio}</a>" in m


def test_ha_pasado_algo_esta_en_inicio(cliente):
    inicio = cliente.get("/").text
    for s in guia.situaciones():
        assert f'href="/eventos/{s.clave}"' in inicio  # cada situación, a un clic
    eventos = cliente.get("/eventos").text  # su página cuelga de Inicio
    assert 'class="activa" aria-current="page">Inicio</a>' in eventos


def test_los_avisos_estan_en_lo_siguiente_de_inicio(tmp_path):
    # No hay ventana de avisos ni tarjeta con cuántos hay: la lista está en Inicio
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    dia = [DIA]
    with en_portal(ruta, hoy=lambda: dia[0]) as cliente:
        assert "Nada pendiente por ahora" in cliente.get("/").text
        cliente.post("/ajustes/recordatorio/10.1", data={"meses": "1"})
        cliente.post("/ajustes/recordatorio/9.2", data={"meses": "1"})
        dia[0] = date(2026, 4, 20)
        inicio = cliente.get("/").text
    assert inicio.count('<span class="sello s-acento">Recordatorio</span>') == 2
    assert "Nada pendiente por ahora" not in inicio and 'id="avisos"' not in inicio


# --- «Reabrir» como enlace y el tema en Ajustes ---

def test_reabrir_es_un_enlace_que_pide_confirmacion(cliente):
    completar_4_3(cliente)
    cliente.post("/requisitos/5.2/puntos/5.2.a/marcar")
    ficha = cliente.get("/requisitos/5.2").text
    enlace = re.search(r'<button class="boton boton-mini"[^>]*>Reabrir 5.2</button>', ficha, re.S).group(0)
    assert 'data-confirmar="/requisitos/5.2/reabrir"' in enlace and 'data-accion="Reabrir"' in enlace
    assert "Sus puntos vuelven a pendiente hasta que los revises." in enlace
    assert "Ha cambiado algo: reabrir" not in ficha
    cliente.post("/requisitos/5.2/reabrir")  # lo que hace la confirmación
    assert 'data-confirmar="/requisitos/5.2/reabrir"' not in cliente.get("/requisitos/5.2").text


def test_el_tema_se_elige_en_ajustes_y_no_en_el_menu(cliente):
    assert "Cambiar tema" not in cliente.get("/").text
    ajustes = cliente.get("/ajustes").text
    aspecto = ajustes[ajustes.index('id="aspecto"'):ajustes.index('<details class="avanzadas"')]
    for valor, texto in (("", "Automático"), ("claro", "Claro"), ("oscuro", "Oscuro")):
        assert f'name="tema" value="{valor}"' in aspecto and texto in aspecto


def test_la_antelacion_se_guarda_sola(cliente):
    ajustes = cliente.get("/ajustes").text
    form = ajustes[ajustes.index('action="/ajustes/antelacion"'):]
    form = form[:form.index("</form>")]
    assert 'hx-trigger="change"' in form
    assert re.sub(r"<noscript>.*?</noscript>", "", form, flags=re.S).count("<button") == 0  # sin «Guardar»
    cliente.post("/ajustes/antelacion", data={"dias": "45"}, headers={"HX-Request": "true"})
    assert 'name="dias" type="number" min="0" max="365" value="45"' in cliente.get("/ajustes").text
