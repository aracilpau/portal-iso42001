# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Actualizar el portal (`actualizar.bat`): mira la versión publicada, pregunta, cambia el programa sin tocar los datos
ni las claves y, si algo falla a mitad, deja el de antes. Sin internet: la «versión publicada» es de mentira."""
import shutil
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from portal import main
from scripts import actualizar as act


def programa(carpeta: Path, version: str | None, texto: str) -> Path:
    """Una carpeta del programa de mentira, con su versión, un archivo que cambia y otro que solo está en ella."""
    (carpeta / "portal").mkdir(parents=True)
    if version:
        (carpeta / "VERSION").write_text(version + "\n", encoding="utf-8")
    (carpeta / "arrancar.bat").write_text("@echo off\necho hola\n", encoding="utf-8")
    (carpeta / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    (carpeta / "portal" / "main.py").write_text(texto, encoding="utf-8")
    (carpeta / "portal" / f"solo_{texto.strip()}.py").write_text("x = 1\n", encoding="utf-8")
    return carpeta


@pytest.fixture
def instalado(tmp_path):
    """El portal instalado: el programa viejo y, dentro de su carpeta, lo que no es del programa."""
    p = programa(tmp_path / "Portal", "2026-11-01 09:00", "viejo\n")
    (p / ".venv").mkdir()
    (p / ".venv" / "python.exe").write_text("entorno", encoding="utf-8")
    (p / "datos").mkdir()
    (p / "datos" / "cuentas.db").write_text("mis cuentas", encoding="utf-8")
    (p / "secretos.env").write_text("MYSQL_CLAVE=secreta", encoding="utf-8")
    return p


def nueva_version(origen: Path, version: str = "2026-11-17 10:32"):
    """Lo que haría GitHub: la versión publicada y la descarga."""
    def bajar(destino: Path) -> Path:
        return programa(destino / "portal-iso42001-main", version, "nuevo\n")
    return {"publicada": lambda: version, "bajar": bajar}


def lanzar(instalado, tmp_path, respuesta="s", **kw):
    dicho, apagados = [], []
    kw = {**nueva_version(tmp_path), **kw}
    cambiado = act.actualizar(programa=instalado, anterior=tmp_path / "ajustes" / "version-anterior",
                              preguntar=lambda _: respuesta, apagar=apagados.append, puerto="8000",
                              decir=dicho.append, **kw)
    return cambiado, "\n".join(dicho), apagados


def lo_de_fuera_sigue(p: Path):
    assert (p / ".venv" / "python.exe").read_text(encoding="utf-8") == "entorno"
    assert (p / "datos" / "cuentas.db").read_text(encoding="utf-8") == "mis cuentas"
    assert (p / "secretos.env").read_text(encoding="utf-8") == "MYSQL_CLAVE=secreta"


# --- Piezas ---

def test_la_version_se_lee_y_se_ensena_en_llano(tmp_path):
    assert act.leer_version(tmp_path) == ""  # las de antes no la traían
    (tmp_path / "VERSION").write_text("2026-11-17 10:32\n", encoding="utf-8")
    assert act.leer_version(tmp_path) == "2026-11-17 10:32"
    assert act.legible("2026-11-17 10:32") == "17/11/2026"
    assert "sin fecha" in act.legible("")


def test_una_descarga_incompleta_no_se_da_por_buena(tmp_path):
    (tmp_path / "VERSION").write_text("2026-11-17 10:32\n", encoding="utf-8")
    with pytest.raises(act.NoSeActualiza, match="no está completa.*arrancar.bat"):
        act.comprobar(tmp_path)


def test_los_bat_descargados_quedan_con_los_finales_de_linea_de_windows(tmp_path):
    p = programa(tmp_path, "2026-11-17 10:32", "nuevo\n")
    (p / "arrancar.bat").write_bytes(b"@echo off\nrem uno\r\necho dos\n")
    act.comprobar(p)
    assert (p / "arrancar.bat").read_bytes() == b"@echo off\r\nrem uno\r\necho dos\r\n"


def test_el_zip_de_github_se_descomprime_en_su_carpeta(tmp_path, monkeypatch):
    origen = programa(tmp_path / "origen", "2026-11-17 10:32", "nuevo\n")
    zip_ = tmp_path / "main.zip"
    with zipfile.ZipFile(zip_, "w") as z:
        for f in origen.rglob("*"):
            z.write(f, "portal-iso42001-main/" + f.relative_to(origen).as_posix())
    monkeypatch.setattr(act, "_bajar", lambda url, tope=60: zip_.read_bytes())
    carpeta = act.descargar(tmp_path / "temporal")
    assert carpeta.name == "portal-iso42001-main" and act.leer_version(carpeta) == "2026-11-17 10:32"


def test_una_descarga_rota_lo_dice(tmp_path, monkeypatch):
    monkeypatch.setattr(act, "_bajar", lambda url, tope=60: b"esto no es un zip")
    with pytest.raises(act.NoSeActualiza, match="incompleta"):
        act.descargar(tmp_path)


def test_apagar_cierra_solo_el_portal_de_su_puerto(monkeypatch):
    netstat = ("  TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       111\n"
               "  TCP    127.0.0.1:8001         0.0.0.0:0              ESCUCHANDO      222\n"
               "  TCP    127.0.0.1:50000        127.0.0.1:8000         ESTABLISHED     333\n")
    cerrados = []

    class Hecho:
        stdout = netstat

    def run(orden, **kw):
        if orden[0] == "taskkill":
            cerrados.append(orden[2])
        return Hecho()
    monkeypatch.setattr(act.subprocess, "run", run)
    act.apagar("8000")
    act.apagar("8001")
    assert cerrados == ["111", "222"]


# --- Recorridos ---

def test_con_la_misma_version_dice_que_esta_al_dia_y_no_toca_nada(instalado, tmp_path):
    cambiado, dicho, apagados = lanzar(instalado, tmp_path, **nueva_version(tmp_path, "2026-11-01 09:00"))
    assert cambiado is False and "Ya estás al día: tienes la versión del 01/11/2026" in dicho
    assert not apagados and (instalado / "portal" / "main.py").read_text(encoding="utf-8") == "viejo\n"


def test_con_una_nueva_cambia_el_programa_y_no_toca_datos_ni_claves(instalado, tmp_path):
    cambiado, dicho, apagados = lanzar(instalado, tmp_path)
    assert cambiado is True and apagados == ["8000"]
    assert "Hay una versión nueva: la del 17/11/2026. Tienes la del 01/11/2026." in dicho
    assert "Hecho: ya tienes la versión del 17/11/2026." in dicho
    assert (instalado / "portal" / "main.py").read_text(encoding="utf-8") == "nuevo\n"
    assert (instalado / "portal" / "solo_nuevo.py").exists()
    assert not (instalado / "portal" / "solo_viejo.py").exists()  # lo que ya no va, fuera
    lo_de_fuera_sigue(instalado)
    anterior = tmp_path / "ajustes" / "version-anterior"  # la de antes, guardada aparte
    assert (anterior / "portal" / "main.py").read_text(encoding="utf-8") == "viejo\n"
    assert not (anterior / "datos").exists() and not (anterior / "secretos.env").exists()


def test_sin_version_en_la_carpeta_ofrece_la_nueva(instalado, tmp_path):
    (instalado / "VERSION").unlink()  # instalado antes de que hubiera actualizaciones
    cambiado, dicho, _ = lanzar(instalado, tmp_path)
    assert cambiado is True and "Tienes la del sin fecha" in dicho


def test_si_se_dice_que_no_no_cambia_nada(instalado, tmp_path):
    cambiado, dicho, apagados = lanzar(instalado, tmp_path, respuesta="n")
    assert cambiado is False and "No se ha cambiado nada." in dicho and not apagados
    assert (instalado / "portal" / "main.py").read_text(encoding="utf-8") == "viejo\n"


def test_sin_internet_lo_dice_y_no_toca_nada(instalado, tmp_path):
    def sin_red():
        raise act.NoSeActualiza("No se ha podido conectar con GitHub")
    with pytest.raises(act.NoSeActualiza, match="GitHub"):
        lanzar(instalado, tmp_path, publicada=sin_red)
    assert (instalado / "portal" / "main.py").read_text(encoding="utf-8") == "viejo\n"


def test_si_falla_a_mitad_deja_la_version_de_antes_intacta(instalado, tmp_path, monkeypatch):
    copiar = shutil.copy2
    def falla_en_el_bat(origen, destino, *a, **kw):
        if Path(destino).name == "arrancar.bat":
            raise PermissionError("archivo en uso")
        return copiar(origen, destino, *a, **kw)
    monkeypatch.setattr(act.shutil, "copy2", falla_en_el_bat)
    with pytest.raises(act.NoSeActualiza, match="archivo en uso.*versión de antes"):
        lanzar(instalado, tmp_path)
    antes = sorted(f.relative_to(instalado).as_posix() for f in instalado.rglob("*") if f.is_file())
    assert antes == [".venv/python.exe", "VERSION", "arrancar.bat", "datos/cuentas.db", "portal/main.py",
                     "portal/solo_viejo.py", "requirements.txt", "secretos.env"]
    assert (instalado / "portal" / "main.py").read_text(encoding="utf-8") == "viejo\n"
    assert act.leer_version(instalado) == "2026-11-01 09:00"
    lo_de_fuera_sigue(instalado)


def test_el_pie_dice_la_version_si_la_hay(monkeypatch, tmp_path):
    monkeypatch.setitem(main.plantillas.env.globals, "version_portal", "Versión del 17/11/2026")
    with TestClient(main.crear_app(tmp_path / "datos")) as cliente:
        assert "Versión del 17/11/2026 · Desarrollado en Movired" in cliente.get("/licencia").text
    monkeypatch.setitem(main.plantillas.env.globals, "version_portal", "")
    with TestClient(main.crear_app(tmp_path / "datos2")) as cliente:
        assert "Versión del" not in cliente.get("/licencia").text
