# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Los manuales. Que el índice lleve a sitios que existen, que lo que nombran exista de verdad y que el de
instalar no lleve nada interno (se publicará tal cual)."""
import re
import subprocess
import sys
from pathlib import Path

from portal import chat

RAIZ = Path(__file__).resolve().parent.parent
INSTALAR = (RAIZ / "docs" / "instalar.md").read_text(encoding="utf-8")


def ancla(titulo: str) -> str:
    """Como hace GitHub: minúsculas, sin signos y con guiones en vez de espacios."""
    return re.sub(r"[^\w\- ]", "", titulo.strip().lower()).replace(" ", "-")


def test_el_indice_de_instalar_lleva_a_apartados_que_existen():
    titulos = {ancla(t) for t in re.findall(r"^## (.+)$", INSTALAR, re.M)}
    enlaces = set(re.findall(r"\]\(#([^)]+)\)", INSTALAR))
    assert enlaces and enlaces <= titulos, enlaces - titulos
    indice = INSTALAR.split("## Índice")[1].split("---")[0]
    assert set(re.findall(r"\]\(#([^)]+)\)", indice)) == titulos - {"índice"}  # todos, y ninguno de más


def test_lo_que_nombra_instalar_existe():
    for archivo in re.findall(r"`([\w\-]+\.bat)`", INSTALAR):
        assert (RAIZ / archivo).exists(), archivo
    assert (RAIZ / "docs" / "manual.md").exists()
    ayuda = subprocess.run([sys.executable, str(RAIZ / "scripts" / "cuentas.py"), "--help"],
                           capture_output=True, text=True, encoding="utf-8", cwd=RAIZ).stdout
    for orden in re.findall(r"scripts\\cuentas\.py (\w+) ", INSTALAR):
        assert orden in ayuda, orden


def test_el_chat_ve_lo_nuevo_del_manual():
    entrar = chat.secciones_manual()["entrar"]
    assert "Quitarse a uno mismo" in entrar and "instalar.md" in entrar
    assert "nadie se puede quitar a sí mismo" not in entrar  # la regla de antes (cambiada el 2026-11-11)


def test_la_base_de_datos_se_llama_igual_en_el_manual_y_en_la_pantalla():
    plantilla = (RAIZ / "portal" / "templates" / "instalar_mysql.html").read_text(encoding="utf-8")
    por_defecto = re.search(r"v\.base or '(\w+)'", plantilla).group(1)
    assert f"CREATE DATABASE {por_defecto} " in INSTALAR and f"`{por_defecto}`" in INSTALAR


def test_los_botones_que_nombra_instalar_existen():
    pantallas = "".join(p.read_text(encoding="utf-8") for p in (RAIZ / "portal" / "templates").glob("instalar*.html"))
    for boton in ("Usarlo solo en este ordenador", "Compartirlo con mi equipo", "Probar conexión", "Crear y entrar"):
        assert boton in INSTALAR and boton in pantallas, boton


def test_olvide_contrasena_cambia_la_clave_con_el_programa_de_cuentas():
    bat = (RAIZ / "olvide-contrasena.bat").read_text(encoding="utf-8")
    assert r'scripts\cuentas.py %* clave "%CORREO%"' in bat  # el portal instalado; con --prueba, el de prueba
    assert "olvide-contrasena.bat" in INSTALAR
    assert "scripts\cuentas.py clave" not in INSTALAR  # ya no hace falta escribir la orden


def test_cambiar_los_datos_del_mysql_se_llama_igual_en_el_manual_y_en_la_pantalla():
    pantalla = (RAIZ / "portal" / "templates" / "sin_conexion.html").read_text(encoding="utf-8")
    assert "Cambiar los datos del MySQL" in pantalla and "Cambiar los datos del MySQL" in INSTALAR
    assert "%APPDATA%" not in INSTALAR  # ya no hace falta borrar los ajustes a mano


# --- Los manuales en inglés (docs/en): los mismos apartados que en español ---

def test_los_manuales_en_ingles_tienen_los_mismos_apartados():
    en = RAIZ / "docs" / "en"
    install = (en / "install.md").read_text(encoding="utf-8")
    manual = (en / "manual.md").read_text(encoding="utf-8")
    # Instalar: tantos apartados como el español, y el índice lleva a todos
    assert len(re.findall(r"^## ", install, re.M)) == len(re.findall(r"^## ", INSTALAR, re.M))
    titulos = {ancla(t) for t in re.findall(r"^## (.+)$", install, re.M)}
    assert set(re.findall(r"\]\(#([^)]+)\)", install)) <= titulos
    # Uso: las mismas claves (las lee el chat), y los enlaces a install.md, a apartados que existen
    claves = lambda t: [c for c in re.findall(r"^## (\S+)\s*$", t, re.M) if c not in ("Índice", "Index")]
    assert claves(manual) == claves((RAIZ / "docs" / "manual.md").read_text(encoding="utf-8"))
    assert set(re.findall(r"install\.md#([^)]+)\)", manual)) <= titulos
    assert re.search(r"«Compartirlo con mi equipo»\*{0,2} \(Share", install)  # los botones, en español y con su traducción


# --- La skill de instalación: que lo que nombra exista y que no lleve nada interno ---

SKILL = RAIZ / ".claude" / "skills" / "instalar-portal"


def textos_skill() -> str:
    return "".join(p.read_text(encoding="utf-8") for p in SKILL.glob("*.md"))


def test_la_skill_se_puede_cargar():
    texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    cabeza = texto.split("---")[1]
    assert re.search(r"^name: instalar-portal$", cabeza, re.M)
    # Entre comillas: con «: » dentro (y lo tiene), sin ellas Claude Code no la lee y la skill no salta sola
    assert re.search(r"^description: '[^']*instalar el portal[^']*'$", cabeza, re.M)
    assert (SKILL / "mysql.md").exists()


def test_lo_que_nombra_la_skill_existe():
    texto = textos_skill()
    for archivo in re.findall(r"`([\w\-]+\.bat)`", texto):
        assert (RAIZ / archivo).exists(), archivo
    for ruta in re.findall(r"`(docs/[\w/]+\.md)`", texto):
        assert (RAIZ / ruta).exists(), ruta
    # Los apartados del manual que cita, con su nombre de verdad
    apartados = set(re.findall(r"^## (.+)$", INSTALAR, re.M))
    for citado in ("Elegir cómo lo vas a usar", "El MySQL: qué pedir", "La carpeta de los archivos", "Seguridad",
                   "Copias de seguridad", "Si algo no funciona", "Si el administrador olvida su contraseña"):
        assert citado in apartados and f"«{citado}»" in texto, citado
    # Los botones que nombra, en las pantallas
    pantallas = "".join(p.read_text(encoding="utf-8") for p in (RAIZ / "portal" / "templates").glob("*.html"))
    for boton in ("Usarlo solo en este ordenador", "Compartirlo con mi equipo", "Probar conexión", "Examinar…",
                  "Crear y entrar", "Cambiar los datos del MySQL", "Administrar"):
        assert boton in texto and boton in pantallas, boton


def test_la_skill_no_pide_contrasenas():
    texto = textos_skill()
    assert "Las contraseñas no se escriben en el chat" in texto and "No abras ni enseñes `secretos.env`" in texto


def test_los_manuales_dicen_como_pedir_ayuda_a_la_skill():
    assert "ayúdame a instalar el portal" in INSTALAR
    assert "help me install the portal" in (RAIZ / "docs" / "en" / "install.md").read_text(encoding="utf-8")
