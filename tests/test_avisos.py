# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Los avisos al entrar y los recordatorios intermedios."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from portal import db, guia
from portal.db import Marca, Recordatorio
from portal.main import crear_app
from conftest import en_portal, entrar
from portal.seguimiento import Seguimiento

DIA = date(2026, 3, 15)
MEJORA = guia.requisito("10.1")


@pytest.fixture
def bd(tmp_path):
    ruta = tmp_path / "general" / "portal.db"
    db.iniciar(ruta)
    return ruta


class Reloj:
    def __init__(self, dia):
        self.dia = dia

    def __call__(self):
        return self.dia


@pytest.fixture
def reloj():
    return Reloj(DIA)


@pytest.fixture
def cliente(bd, reloj):
    with en_portal(bd, hoy=reloj) as c:
        yield c


def avisos(cliente):
    """La lista «Lo siguiente» de Inicio: los avisos solo viven ahí."""
    html = cliente.get("/").text
    return html[html.index('<ol class="tareas"'):html.index('</ol>', html.index('<ol class="tareas"'))]


def total(cliente):
    return avisos(cliente).count('<li class="tarea">')


def marcado_el(cliente, reloj, url, dia):
    """Marca un punto como si fuera otro día y vuelve al de la prueba: así llega a vencido o a vence pronto como de
    verdad (la fecha no se cambia a mano)."""
    reloj.dia = dia
    cliente.post(url)
    reloj.dia = DIA


# --- Piezas: los recordatorios ---

def test_un_recordatorio_toca_pasados_sus_meses_y_no_antes():
    recs = {"10.1": Recordatorio(3, DIA)}
    assert Seguimiento(set(), recordatorios=recs, hoy=date(2026, 6, 14)).recordatorios_hoy() == []
    hoy = Seguimiento(set(), recordatorios=recs, hoy=date(2026, 6, 15)).recordatorios_hoy()
    assert [(r.codigo, f) for r, f in hoy] == [("10.1", date(2026, 6, 15))]


def test_hecho_y_marcar_algo_del_requisito_vuelven_a_contar():
    est = Seguimiento(set(), recordatorios={"10.1": Recordatorio(3, DIA, hecho=date(2026, 5, 1))})
    assert est.proximo_recordatorio(MEJORA) == date(2026, 8, 1)
    punto = MEJORA.puntos[0].codigo
    est = Seguimiento({punto: Marca(date(2026, 7, 1))}, recordatorios={"10.1": Recordatorio(3, DIA)})
    assert est.proximo_recordatorio(MEJORA) == date(2026, 10, 1)


def test_un_control_que_no_aplica_no_recuerda():
    recs = {"A.10.3": Recordatorio(1, DIA)}
    est = Seguimiento(set(), recordatorios=recs, excluidos={"A.10.3"}, hoy=DIA + timedelta(days=60))
    assert est.recordatorios_hoy() == []


# --- Recorridos: la lista de Inicio ---

def test_sin_nada_pendiente_lo_dice(cliente):
    assert total(cliente) == 0 and "Nada pendiente por ahora" in avisos(cliente)


def test_lo_vencido_sale_hasta_que_se_renueva(cliente, reloj):
    marcado_el(cliente, reloj, "/requisitos/4.3/puntos/4.3.a/marcar", date(2025, 3, 10))  # venció el 10/03/2026
    v = avisos(cliente)
    assert total(cliente) == 1 and "Vencido" in v and "4.3.a" in v and "Venció el 10/03/2026" in v
    cliente.post("/requisitos/4.3/puntos/4.3.a/renovar")
    assert total(cliente) == 0 and "4.3.a" not in avisos(cliente)


def test_las_lineas_por_sistema_salen_con_su_sistema(cliente, reloj):
    r = cliente.post("/inventario", data={"nombre": "ChatGPT", "tipo": "herramienta"})
    chat = int(str(r.url).rsplit("/", 1)[1])
    cliente.post(f"/inventario/{chat}/no-reabrir")  # que no salga también como sistema nuevo
    marcado_el(cliente, reloj, f"/requisitos/8.4/puntos/8.4.a/sistemas/{chat}/marcar", date(2025, 3, 20))  # vence en 5 días
    v = avisos(cliente)
    assert "Vence 20 mar" in v and "· ChatGPT ·" in v and f"#8.4.a-{chat}" in v


# --- Recorridos: los recordatorios ---

def test_poner_un_recordatorio_y_marcarlo_hecho(cliente, reloj):
    cliente.post("/ajustes/recordatorio/10.1", data={"meses": "3"})
    ajustes = cliente.get("/ajustes").text
    assert 'value="3" selected' in ajustes and "Próximo aviso: 15/06/2026" in ajustes
    assert total(cliente) == 0  # aún no toca

    reloj.dia = date(2026, 6, 15)
    v = avisos(cliente)
    assert "Recordatorio" in v and "Tocaba el 15/06/2026" in v and total(cliente) == 1

    cliente.post("/avisos/recordatorio/10.1/hecho")
    assert total(cliente) == 0
    assert "Próximo aviso: 15/09/2026" in cliente.get("/ajustes").text  # el siguiente, dentro de 3 meses


def test_hecho_desde_inicio_vuelve_a_inicio(cliente, reloj):
    cliente.post("/ajustes/recordatorio/10.1", data={"meses": "1"})
    reloj.dia = date(2026, 4, 15)
    r = cliente.post("/avisos/recordatorio/10.1/hecho")
    assert str(r.url).endswith("/") and "Sistema de gestión de la IA" in r.text


def test_quitar_el_recordatorio(cliente, reloj):
    cliente.post("/ajustes/recordatorio/10.1", data={"meses": "1"})
    reloj.dia = date(2026, 4, 15)
    assert "10.1" in avisos(cliente)
    cliente.post("/ajustes/recordatorio/10.1", data={"meses": "no"})
    assert total(cliente) == 0
    assert cliente.post("/ajustes/recordatorio/10.1", data={"meses": "5"}).status_code == 400


# --- Recorridos: qué avisa ---

def test_lo_que_no_se_elige_no_avisa(cliente, reloj):
    marcado_el(cliente, reloj, "/requisitos/4.3/puntos/4.3.a/marcar", date(2025, 3, 10))
    cliente.post("/ajustes/avisos", data={"avisar_pronto": "1", "avisar_recordatorios": "1"})  # sin vencidos
    assert total(cliente) == 0
    ajustes = cliente.get("/ajustes").text
    assert 'name="avisar_vencidos" value="1" checked' not in ajustes
    assert 'name="avisar_pronto" value="1" checked' in ajustes
    cliente.post("/ajustes/avisos", data={"avisar_vencidos": "1"})
    assert total(cliente) == 1


# --- Los recordatorios por defecto ---

def test_los_recordatorios_por_defecto_solo_donde_hace_falta_continuidad():
    est = Seguimiento(set(), inicio=DIA)
    assert est.recordatorio(MEJORA).meses == 3
    assert est.recordatorio(guia.requisito("A.4.2")).meses == 6
    assert est.recordatorio(guia.requisito("5.2")) is None       # la política: basta con el vencimiento
    assert est.recordatorio(guia.requisito("9.3")) is None       # la revisión por la dirección: una vez al año
    assert est.proximo_recordatorio(MEJORA) == date(2026, 6, 15)  # cuentan desde que se creó el espacio


def test_sin_recordatorio_en_uno_que_lo_tiene_por_defecto_se_queda_sin(cliente):
    cliente.post("/ajustes/recordatorio/10.1", data={"meses": "no"})
    ajustes = cliente.get("/ajustes").text
    assert 'value="no" selected>Nunca</option>' in ajustes  # ya no es el recomendado
    assert "3 meses (recomendado)" in ajustes


def test_hecho_en_un_recordatorio_por_defecto(cliente, reloj, bd):
    # Los de por defecto cuentan desde que se creó el espacio: se crea el día que simulan las pruebas
    with db.conectar(bd) as con:
        con.execute("UPDATE espacio SET creado = ?", (DIA.isoformat(),))
    con.close()
    reloj.dia = date(2026, 6, 15)  # el de por defecto de la 10.1 (cada 3 meses) toca hoy
    assert "10.1" in avisos(cliente)
    cliente.post("/avisos/recordatorio/10.1/hecho")
    assert "/avisos/recordatorio/10.1/hecho" not in avisos(cliente)
    assert "Próximo aviso: 15/09/2026" in cliente.get("/ajustes").text


def test_volver_a_los_valores_recomendados_devuelve_los_recordatorios(cliente):
    cliente.post("/ajustes/recordatorio/10.1", data={"meses": "no"})
    cliente.post("/ajustes/recordatorio/5.2", data={"meses": "1"})
    assert "Hay 2 cambios respecto a lo recomendado" in cliente.get("/ajustes").text
    cliente.post("/ajustes/plazos/por-defecto")
    ajustes = cliente.get("/ajustes").text
    assert "Volver a los valores recomendados" not in ajustes
    assert 'value="3" selected>Cada 3 meses (recomendado)' in ajustes



def test_el_plazo_recomendado_tambien_se_ve_en_los_que_no_vencen(cliente):
    ajustes = cliente.get("/ajustes").text
    assert 'value="no" selected>No vence por fecha (recomendado)</option>' in ajustes  # p. ej. la 6.3, por evento
    assert 'value="si" selected>Cada año (recomendado)</option>' in ajustes            # p. ej. la 5.2



def test_las_fechas_se_ven_como_dd_mm_aaaa_y_no_se_cambian_a_mano(cliente):
    """La fecha de vencimiento se calcula; en Ajustes solo se consulta."""
    cliente.post("/requisitos/4.3/puntos/4.3.a/marcar")
    ajustes = cliente.get("/ajustes").text
    assert "Vence el 15/03/2027" in ajustes and 'action="/ajustes/fecha/' not in ajustes
    assert cliente.post("/ajustes/fecha/4.3.a", data={"vence": "1/4/2026"}).status_code in (404, 405)



def test_cada_fila_solo_elige_si_vence_con_la_revision_general(cliente):
    # Un plazo general para todos; en cada requisito, vence o no
    ajustes = cliente.get("/ajustes").text
    assert 'for="meses-5.2">Se revisa</label>' in ajustes and 'for="recordar-10.1">Recordar</label>' in ajustes
    assert 'value="12" selected>Cada año (recomendado)</option>' in ajustes  # la revisión general
    cliente.post("/ajustes/plazo-general", data={"meses": "24"})
    ajustes = cliente.get("/ajustes").text
    assert 'value="si" selected>Cada 2 años (recomendado)</option>' in ajustes
