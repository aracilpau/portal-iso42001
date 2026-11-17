# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El portal ISO/IEC 42001: la web que se abre en el navegador.

Se arranca desde la carpeta del proyecto con `uvicorn portal.main:app` (o con arrancar.bat).
"""
import io
import json
import re
import secrets
import threading
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from guia import datos as guia
from portal import avisos as correo, borradores, chat, config, cuentas, db, documento, ia, instalar, lectura, pendiente, propuestas, pruebas, revision93, revisor, seguimiento
from portal import servidor as srv
from portal import guia as guia_portal

AQUI = Path(__file__).resolve().parent

# Las columnas de la lista de requisitos, en llano (los valores de la guía no cambian: los usan las cuentas)
COMO_SE_DEMUESTRA = {
    "Documento": "un escrito aprobado (una política, un procedimiento).",
    "Registro": "la prueba de que se hizo (un acta, una lista de asistencia, unos resultados).",
    "Práctica": "el auditor lo comprueba mirando cómo trabajáis y preguntando a la gente.",
    "Inventario": "se cubre con las fichas de «Empresa → Sistemas de IA».",
    "Resumen": "no tiene trabajo propio: se completa al completar otros requisitos.",
}
CADA_CUANTO = {"Una vez y revisar": "Una vez y revisar cada año", "Periódico": "Varias veces al año",
               "Por evento": "Cuando pasa algo"}
CADA_CUANTO_AYUDA = {
    "Una vez y revisar": "se hace una vez y se repasa en la revisión de cada año.",
    "Periódico": "se repite a lo largo del año (el portal lo recuerda).",
    "Por evento": "se revisa cuando pasa algo que le afecta (ver «¿Ha pasado algo?»).",
}

# Un solo estilo, «Plano» (antes «Mesa de control»; el fichero sigue llamándose mesa.css)
plantillas = Jinja2Templates(directory=AQUI / "templates")
plantillas.env.globals.update(clase=seguimiento.clase, PROPIO=seguimiento.PROPIO,
                              APOYADO=seguimiento.APOYADO, SISTEMA=seguimiento.SISTEMA,
                              se_reabre=seguimiento.se_reabre, vence_por_defecto=seguimiento.vence_por_defecto,
                              VENCE_PRONTO=seguimiento.VENCE_PRONTO, VENCIDO=seguimiento.VENCIDO,
                              FICHA=seguimiento.FICHA, CAMPO_DE=seguimiento.CAMPO_DE, TIPOS=db.TIPOS,
                              RECORDAR_POR_DEFECTO=seguimiento.RECORDAR_POR_DEFECTO,
                              PREGUNTAR_POR_DEFECTO=seguimiento.PREGUNTAR_POR_DEFECTO,
                              NO_HACE_FALTA=seguimiento.NO_HACE_FALTA,
                              titulo_de={r.codigo: r.titulo for r in guia_portal.requisitos()},
                              COMO_SE_DEMUESTRA=COMO_SE_DEMUESTRA, CADA_CUANTO=CADA_CUANTO,
                              CADA_CUANTO_AYUDA=CADA_CUANTO_AYUDA)
# Se añade a la dirección del estilo (mesa.css) y de htmx: si cambian, el navegador ve una dirección nueva
# y no tira de la copia vieja que tenía guardada
plantillas.env.globals["version"] = str(int(max(f.stat().st_mtime for f in (AQUI / "static").iterdir())))
# La versión publicada (el fichero VERSION, que pone la copia pública): en el pie, para saber cuál se tiene
_VERSION = (config.RAIZ / "VERSION").read_text(encoding="utf-8").strip() if (config.RAIZ / "VERSION").is_file() else ""
plantillas.env.globals["version_portal"] = (f"Versión del {_VERSION[8:10]}/{_VERSION[5:7]}/{_VERSION[:4]}"
                                            if len(_VERSION) >= 10 else "")
plantillas.env.filters["seguro"] = pruebas.nombre_seguro  # el nombre de un sistema en carpetas e historial
# Si un archivo del historial es de un punto (o de la línea de un sistema): su nombre empieza por él
plantillas.env.tests["en_punto"] = lambda nombre, delante: nombre.startswith(delante + " - ")

plantillas.env.filters["fecha"] = lambda d: d.strftime("%d/%m/%Y") if d else ""
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")
plantillas.env.filters["fecha_larga"] = lambda d: f"{DIAS[d.weekday()].capitalize()} {d.day} de {MESES[d.month - 1]}"
plantillas.env.filters["dia_mes"] = lambda d: f"{d.day} {MESES[d.month - 1][:3]}" if d else ""

# Los campos de la ficha de cada sistema: qué piden, qué poner y un ejemplo
CAMPOS_FICHA = [
    ("para_que", "Para qué sirve y responsable", "A.4.2.a",
     "Qué hace el sistema y para qué lo usáis, y quién responde de él en la empresa. Indica si es vuestro "
     "o un servicio de terceros.",
     "Ej.: Asistente que responde dudas de los clientes en la web. Responsable: Ana (Producto). "
     "Propio, sobre un modelo de OpenAI."),
    ("datos", "Datos", "A.4.3.a",
     "Qué información entra y de dónde sale: de clientes, documentos internos, lo que escribe la plantilla… "
     "En una herramienta externa, qué datos le dais. Si hay datos personales, dilo.",
     "Ej.: Preguntas de los clientes y la base de conocimiento de la web. Sin datos personales sensibles. "
     "Se actualiza cada mes."),
    ("herramientas", "Herramientas y modelos", "A.4.4.a",
     "Qué modelo de IA hay detrás y de quién es (p. ej. GPT-4o de OpenAI), y con qué se desarrolla, prueba "
     "o vigila. En una IA que usa el equipo basta con el nombre del programa y de quién es.",
     "Ej.: ChatGPT Team, de OpenAI. (Si lo ha hecho vuestro equipo técnico, pídeles el modelo y las herramientas.)"),
    ("infraestructura", "Infraestructura", "A.4.5.a",
     "Dónde funciona: vuestros servidores, la nube (cuál y en qué región) o los del proveedor. En una "
     "herramienta externa, normalmente «en los servidores del proveedor».",
     "Ej.: En los servidores de OpenAI (es un servicio de internet)."),
    ("personas", "Personas", "A.4.6.a",
     "Quién interviene en cada fase (quién lo desarrolla o contrata, lo pone en marcha, lo mantiene y lo usa) "
     "y con qué formación. Si es un servicio que ofrecéis, incluye también quién lo usa del lado del cliente.",
     "Ej.: Lo contrató Marta (dirección). Lo usa el equipo comercial (5 personas), con una formación de una hora. "
     "Revisa las respuestas quien las usa."),
]

# El nombre del campo que cumple cada punto, para decirlo en la ficha del requisito
plantillas.env.globals["SOLO_SI_DESARROLLA"] = guia_portal.SOLO_SI_DESARROLLA  # el bloque de «Empresa» que puede no salir
plantillas.env.globals["quien_decide"] = propuestas.quien_decide  # Declaración mixta: quién ha propuesto
plantillas.env.globals["requisito_de"] = seguimiento.REQUISITO_DE  # para enlazar un punto con su ficha
plantillas.env.globals["CAMPO_TITULO"] = {punto: titulo for _, titulo, punto, _, _ in CAMPOS_FICHA}

# Si se sigue escribiendo el porqué de un control dentro de este rato, se corrige la línea ya apuntada
# en vez de añadir otra
SIGUE_ESCRIBIENDO = timedelta(minutes=10)
CARPETA_OCUPADA = ("No se han podido renombrar las carpetas del sistema: seguramente hay un archivo suyo abierto "
                   "(en Word, un visor de PDF…). Ciérralo y vuelve a intentarlo.")


# Qué puede avisar, y cada cuánto se puede recordar un requisito
AVISOS = {"avisar_vencidos": "Lo que ha vencido", "avisar_pronto": "Lo que vence pronto",
          "avisar_recordatorios": "Los recordatorios de cada requisito"}
RECORDAR = [1, 2, 3, 6]
# Cómo se lee cada acción en «Actividad»
ACCIONES = {
    "marcado": "marcado como cumplido",
    "desmarcado": "desmarcado",
    "renovado": "renovado",
    "reabierto": "reabierto",
    "evento": "ha pasado algo",
    "subido": "archivo subido",
    "version": "versión nueva subida",
    "quitado": "archivo quitado: pasa a versiones anteriores",
    "borrado": "borrado para siempre de versiones anteriores",
    "documento": "documento de la Declaración guardado como prueba",
    "aplica": "decidido: aplica",
    "no_aplica": "decidido: no aplica",
    "sin_decidir": "vuelto a sin decidir",
    "sistema_alta": "sistema dado de alta",
    "sistema_ficha": "ficha del sistema guardada",
    "sistema_retirado": "sistema retirado",
    "sistema_activado": "sistema vuelto a activar",
    "cuestionario": "cuestionario de la empresa",
    "revisado": "revisado por la IA",
    "borrador": "borrador del documento descargado (sin IA)",
    "borrador_ia": "borrador del documento hecho con IA",
    "revision93": "borrador de la revisión por la dirección preparado",
    "propuestas": "propuestas de la IA para la Declaración",
    "aviso": "aviso por correo mandado",
    "aviso_fallido": "aviso por correo: no ha salido",
}
PREGUNTAR = [0, 1, 2, 3, 4, 6]  # «¿ha pasado algo?»: 0 es nunca

def texto_cada(meses: int) -> str:
    """«Cada año», «Cada 2 años», «Cada 6 meses»."""
    if meses % 12 == 0:
        return "Cada año" if meses == 12 else f"Cada {meses // 12} años"
    return f"Cada {meses} meses"


plantillas.env.filters["cada"] = texto_cada

# La revisión general que se puede elegir en ajustes, en meses
PLAZOS = [6, 12, 18, 24]

# Los filtros de la lista: qué estados de requisito entran en cada uno
FILTROS = {
    "": ("Todos", None),
    "pendientes": ("Pendientes", ("pendiente", "curso", "vencido")),
    "vencen": ("Vencen o vencidos", ("vencido", "pronto")),
    "completos": ("Completos", ("hecho", "pronto")),
    "noaplica": ("No aplican o no hacen falta", ("noaplica", "nohacefalta")),
}


def licencia_html(texto: str) -> Markup:
    """El texto de LICENSE (Markdown sencillo) en HTML, para que no se vean «##» ni «**» en la página."""
    bloques = []
    for bloque in re.split(r"\n\s*\n", texto.strip()):
        b = str(escape(bloque.strip()))
        b = re.sub(r"&lt;(https?://[^&]+)&gt;", r'<a href="\1">\1</a>', b)
        b = re.sub(r"\[([^\]]+)\]\(#[^)]+\)", r"\1", b)  # los enlaces internos, como texto
        b = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", b, flags=re.S)
        b = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", b, flags=re.S)
        if b.startswith("## "):
            bloques.append(f"<h3>{b[3:]}</h3>")
        elif b.startswith("# "):
            bloques.append(f"<h2>{b[2:]}</h2>")
        else:
            bloques.append(f"<p>{b}</p>")
    return Markup("\n".join(bloques))


def _y(partes: list[str]) -> str:
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]


def puntos_llano(codigos: list[str], actual: str, delante: str = "en ") -> Markup:
    """Los puntos por su letra y su ficha: «en los puntos a, b y c de esta ficha y en el punto b de la ficha A.2.2
    (Política de IA)», con enlaces. Para decir dónde se sube un borrador sin una lista de códigos."""
    fichas: dict[str, list[str]] = {}
    for c in codigos:
        fichas.setdefault(seguimiento.REQUISITO_DE[c].codigo, []).append(c)
    partes = []
    for r, suyos in fichas.items():
        letras = _y([f'<a href="/requisitos/{r}#{escape(c)}">{escape(c.rsplit(".", 1)[1])}</a>' for c in suyos])
        donde = "de esta ficha" if r == actual else (
            f'de la ficha <a href="/requisitos/{r}">{r}</a> ({escape(guia_portal.requisito(r).titulo)})')
        partes.append(f"{delante}{'los puntos' if len(suyos) > 1 else 'el punto'} {letras} {donde}")
    return Markup(_y(partes))


plantillas.env.globals["puntos_llano"] = puntos_llano


# El nombre que se ve de cada empresa es el de cuentas.db (o el MySQL), no el de su espacio
@dataclass
class Sesion:
    """Quién está mirando y en qué empresa. Se guardan en memoria: al arrancar el portal, hay que volver a
    entrar."""
    usuario: cuentas.Usuario | None
    empresa: cuentas.Empresa | None = None
    administrador: bool = False  # se mira en cada petición


# La sesión de la petición que se está atendiendo: la pone `acceso` y la leen `bd()`, `carpetas()` y las páginas
ACTUAL: ContextVar[Sesion] = ContextVar("sesion")
# Lo que se lee una sola vez en cada petición (el espacio de la empresa); lo vacía `acceso` al empezar cada una
POR_PETICION: ContextVar[dict] = ContextVar("por_peticion")
COOKIE = "portal_sesion"
LIBRES = ("/entrar", "/static", "/sin-conexion", "/licencia")  # se ven sin haber entrado


SIN_EMPRESA = ("/empresas", "/salir", "/carpeta", "/administrar", "/contrasena")  # se ven sin haber elegido empresa
plantillas.env.globals["sesion_actual"] = lambda: ACTUAL.get(None)


def cifras_guia() -> dict:
    """Lo que hay cargado de la guía, para enseñarlo en el inicio."""
    return {
        "requisitos": len(guia.filas),
        "obligatorios": len(guia.C),
        "controles": len(guia.A),
        "puntos": len(guia.P),
    }


# Se ven en el navegador; el resto se descarga
SE_VEN = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".txt"}


def crear_app(datos: Path = config.DATOS, hoy: Callable[[], date] = date.today, prueba: bool = config.PRUEBA,
              envio: correo.Envio | None = None,
              servidor: srv.Servidor | None = srv.leer(config.SECRETOS) if config.SERVIDOR else None,
              ajustes_pc: Path | None = config.AJUSTES if config.SERVIDOR else None,
              examinar: Callable[[Path | None], str | None] = config.examinar,
              instalador: instalar.Instalador | None = None) -> FastAPI:
    """`datos`: la carpeta con `cuentas.db` y una carpeta por empresa. `hoy` se puede cambiar en las pruebas para
    simular que pasa el tiempo. `prueba`: el portal de arrancar-prueba.bat, que lo dice en la cabecera. `envio`: cómo
    salen los avisos por correo; las pruebas ponen uno de mentira. `servidor`: el MySQL del portal de verdad;
    sin él, todo en local. `ajustes_pc`: en el portal compartido, el archivo de ajustes de este ordenador, que dice en qué
    carpeta van las pruebas; sin él, en `datos`. `examinar`: la ventana de Windows para elegir carpeta (las
    pruebas ponen una de mentira). `instalador`: el portal instalado de arrancar.bat: el modo sale de los
    ajustes de este ordenador y, si aún no hay, se ve la instalación; entonces `datos`, `servidor` y `ajustes_pc` no
    cuentan."""
    envio = envio or correo.Envio()
    db.usar_servidor(servidor)
    plantillas.env.globals["prueba"] = prueba
    # La marca «LOCAL» es la de arrancar-local.bat; el portal instalado no la lleva, aunque esté solo en este ordenador
    plantillas.env.globals["local"] = servidor is None and not prueba and instalador is None
    sesiones: dict[str, Sesion] = {}
    cajones: dict[str, pruebas.Pruebas] = {}  # las carpetas de pruebas de cada empresa
    preparando = threading.Lock()
    iniciado = []  # las cuentas preparadas; con el MySQL, puede que al arrancar no hubiera conexión
    problema = [srv.SinConexion(srv.SIN_CONEXION)]  # el último «sin conexión», para la página que lo explica
    instalando = [False]  # hasta acabar la instalación, solo se ven sus páginas
    elegido: dict = {}    # lo elegido en la instalación, hasta el final (el portal es de una sola persona a la vez)

    def ponerse_en(modo: str) -> None:
        """El portal en el modo de este ordenador: al arrancar, o al acabar la instalación sin tener que
        reiniciarlo. Todo lo de dentro lee `datos` y `ajustes_pc` de aquí, así que basta con cambiarlos."""
        nonlocal datos, ajustes_pc
        if modo == config.LOCAL:
            db.usar_servidor(None)
            datos, ajustes_pc = config.datos_local(instalador.ajustes), None
        else:
            db.usar_servidor(instalador.servidor())
            datos, ajustes_pc = instalador.datos_compartido, instalador.ajustes
        plantillas.env.globals["local"] = False  # la marca «LOCAL» es la de arrancar-local.bat, para no confundirlos
        with preparando:
            cajones.clear()
        iniciado.clear()
        instalando[0] = False

    if instalador is not None:
        ya = instalador.modo()
        if ya is None:
            instalando[0] = True
        else:
            ponerse_en(ya)

    def raiz_pruebas() -> Path | None:
        """Dónde van las carpetas de pruebas: en local, en `datos`; en el compartido, en la carpeta elegida en este
        ordenador, o None si no hay ninguna o ya no está (el portal la pide)."""
        return datos if ajustes_pc is None else config.carpeta_pruebas(ajustes_pc)

    def falta_carpeta() -> bool:
        return raiz_pruebas() is None

    def bd() -> Path:
        """La base de datos de la empresa en la que se está."""
        return cuentas.bd_de(datos, ACTUAL.get().empresa.slug)

    def carpetas() -> pruebas.Pruebas:
        return cajones[ACTUAL.get().empresa.slug]

    def preparar(slug: str) -> None:
        """La primera vez que se entra en una empresa desde que arrancó el portal: su base de datos al día y sus
        carpetas de pruebas, como hacía el arranque cuando solo había una."""
        with preparando:
            if slug in cajones:
                return
            db.iniciar(cuentas.bd_de(datos, slug))
            cajones[slug] = pruebas.Pruebas(raiz_pruebas() / slug, "pruebas")  # quien llama ya ha mirado que esté
            carpetas_no_aplica()  # antes de crear, para no crear una «A.7.3» al lado de «A.7.3 (no aplica)»
            carpetas().crear(db.sistemas(bd(), espacio()["id"]))

    def iniciar_cuentas() -> None:
        if not iniciado and not instalando[0]:
            # Un portal instalado empezó sin el General: si faltara cuentas.db, tampoco se crea
            cuentas.iniciar(datos, prueba, general=instalador is None)
            iniciado.append(True)

    @asynccontextmanager
    async def arranque(app: FastAPI):
        try:
            iniciar_cuentas()
        except srv.SinConexion:
            pass  # sin conexión con el MySQL: se dice en la primera página y se vuelve a intentar entonces
        yield
        for c in list(conversaciones.values()):  # el chat: al cerrar el portal, sus Claude se cierran
            await c.cerrar()
        conversaciones.clear()

    app = FastAPI(title="Portal ISO/IEC 42001", lifespan=arranque)
    app.mount("/static", StaticFiles(directory=AQUI / "static"), name="static")

    def ir_a(url: str, request: Request) -> Response:
        # Un botón de htmx que pide un trozo de página: que cambie la página entera, no que meta la entrada en el trozo
        if request.headers.get("HX-Request"):
            return Response(status_code=204, headers={"HX-Redirect": url})
        return RedirectResponse(url, status_code=303)

    @app.middleware("http")
    async def acceso(request: Request, call_next):
        """Sin haber entrado solo se ve la entrada; sin empresa elegida, la lista de empresas. Se comprueba en
        cada petición: si quitan a alguien o borran su empresa, deja de verla aunque tuviera la página abierta."""
        ruta = request.url.path
        if instalando[0]:  # la primera vez, la instalación
            if ruta.startswith(("/instalar", "/static", "/licencia")):
                return await call_next(request)
            return ir_a("/instalar", request)
        if ruta.startswith(LIBRES):
            return await call_next(request)
        token = request.cookies.get(COOKIE, "")
        sesion = sesiones.get(token)
        if sesion is None:
            return ir_a("/entrar", request)
        # Las comprobaciones, a la vez: con el MySQL, un viaje en vez de cuatro en cada petición
        uid, slug = sesion.usuario.id, sesion.empresa.slug if sesion.empresa else None
        u, e, dentro, admin = db.a_la_vez(lambda: cuentas.usuario_por_id(datos, uid),
                                          lambda: cuentas.empresa(datos, slug) if slug else None,
                                          lambda: cuentas.puede_entrar(datos, uid, slug) if slug else False,
                                          lambda: cuentas.es_administrador(datos, uid))
        if u is None or not u.activo:
            sesiones.pop(token, None)
            return ir_a("/entrar", request)
        sesion.usuario, sesion.administrador = u, admin
        if sesion.empresa is not None:
            sesion.empresa = e if e and dentro else None
        ACTUAL.set(sesion)
        POR_PETICION.set({})
        if falta_carpeta():
            # Sin la carpeta de las pruebas no se puede enseñar nada: se pide nada más entrar, antes de elegir empresa,
            # porque vale para todas
            if not ruta.startswith(("/carpeta", "/salir")):
                return ir_a("/carpeta", request)
        elif sesion.empresa is None:
            if not ruta.startswith(SIN_EMPRESA):
                return ir_a("/empresas", request)
        else:
            preparar(sesion.empresa.slug)
        return await call_next(request)

    @app.middleware("http")
    async def sin_copias(request: Request, call_next):
        # Que el navegador no guarde copia de las páginas: con Atrás y Adelante enseñaba
        # porcentajes viejos. El estilo y htmx sí se pueden guardar.
        respuesta = await call_next(request)
        if respuesta.headers.get("content-type", "").startswith("text/html"):
            respuesta.headers["Cache-Control"] = "no-store"
        return respuesta

    def pagina_sin_conexion(request: Request, error: srv.SinConexion):
        return plantillas.TemplateResponse(request, "sin_conexion.html", {
            "texto": str(error), "cambiar_mysql": puede_cambiar_mysql()}, status_code=503)

    @app.middleware("http")
    async def sin_conexion(request: Request, call_next):
        """Sin el MySQL (sin internet, o sin secretos.env) no hay nada que enseñar: se dice en llano. Si se corta
        a mitad de guardar algo, no se guarda nada a medias."""
        try:
            if not request.url.path.startswith(("/static", "/sin-conexion", "/licencia")):
                iniciar_cuentas()
            return await call_next(request)
        except srv.SinConexion as error:
            problema[0] = error
            if request.headers.get("HX-Request"):  # un botón: que cambie la página entera
                return Response(status_code=204, headers={"HX-Redirect": "/sin-conexion"})
            return pagina_sin_conexion(request, error)

    @app.get("/sin-conexion")
    def pagina_problema(request: Request):
        return pagina_sin_conexion(request, problema[0])

    @app.get("/licencia")
    def licencia(request: Request):
        """La licencia en llano y su texto, que vale legalmente. Se ve sin entrar y sin el MySQL."""
        texto = (config.RAIZ / "LICENSE").read_text(encoding="utf-8")
        return plantillas.TemplateResponse(request, "licencia.html", {"texto": licencia_html(texto)})

    # --- Entrar, elegir empresa y salir ---

    def pagina_entrar(request: Request, error: str = "", correo_: str = "", instalado: str = ""):
        return plantillas.TemplateResponse(request, "entrar.html", {
            "error": error, "correo": correo_, "hay_cuentas": bool(cuentas.usuarios(datos)),
            "usuario_prueba": cuentas.PRUEBA if prueba else None, "equipo": instalado == "equipo",
        })

    @app.get("/entrar")
    def entrar(request: Request, instalado: str = ""):
        return pagina_entrar(request, instalado=instalado)

    @app.post("/entrar")
    def entrar_con(request: Request, correo_: str = Form("", alias="correo"), clave: str = Form("")):
        u = cuentas.entrar(datos, correo_, clave)
        if u is None:
            return pagina_entrar(request, "El correo o la contraseña no son correctos.", correo_)
        token = secrets.token_urlsafe(32)
        sesiones[token] = Sesion(u)
        r = RedirectResponse("/empresas", status_code=303)
        r.set_cookie(COOKIE, token, httponly=True, samesite="lax")  # sin fecha: se olvida al cerrar el navegador
        return r

    @app.get("/empresas")
    def elegir_empresa(request: Request):
        s = ACTUAL.get()
        return plantillas.TemplateResponse(request, "empresas.html", {
            "empresas": cuentas.empresas_de(datos, s.usuario.id),
        })

    @app.post("/empresas/{slug}")
    def entrar_en_empresa(slug: str):
        s = ACTUAL.get()
        if not cuentas.puede_entrar(datos, s.usuario.id, slug):
            raise HTTPException(404)
        s.empresa = cuentas.empresa(datos, slug)
        if falta_carpeta():
            return RedirectResponse("/carpeta", status_code=303)
        preparar(slug)
        return RedirectResponse("/empresa/paso/1" if paso_a_paso_pendiente() else "/", status_code=303)

    # --- La carpeta de las pruebas en este ordenador ---

    def pagina_carpeta(request: Request, ruta: str | None = None, error: str = ""):
        if ajustes_pc is None:  # en local, las pruebas van con los datos: no hay nada que elegir
            raise HTTPException(404)
        elegida = config.carpeta_elegida(ajustes_pc)
        return plantillas.TemplateResponse(request, "carpeta.html", {
            "ruta": ruta if ruta is not None else str(elegida or ""), "error": error,
            "perdida": elegida if elegida and config.carpeta_pruebas(ajustes_pc) is None else None,
            "suyas": [e.slug for e in cuentas.empresas_de(datos, ACTUAL.get().usuario.id)],
        })

    @app.get("/carpeta")
    def carpeta(request: Request):
        return pagina_carpeta(request)

    @app.post("/carpeta/examinar")
    def carpeta_examinar(request: Request, ruta: str = Form("")):
        """La ventana de Windows para elegir carpeta; la elegida queda escrita para confirmarla con «Usar esta carpeta».
        El portal está en el mismo ordenador que el navegador, así que la ventana sale delante de quien lo usa."""
        if ajustes_pc is None:
            raise HTTPException(404)
        inicial = Path(ruta.strip().strip('"')) if ruta.strip() else None
        elegida = examinar(inicial if inicial and inicial.is_absolute() and inicial.is_dir() else None)
        return plantillas.TemplateResponse(request, "_carpeta.html", {"ruta": elegida or ruta, "error": ""})

    @app.post("/carpeta")
    def carpeta_guardar(request: Request, ruta: str = Form("")):
        if ajustes_pc is None:
            raise HTTPException(404)
        try:
            config.guardar_carpeta(str(comprobar_compartida(ruta, datos)), ajustes_pc)
        except config.CarpetaNoVale as error:
            return pagina_carpeta(request, ruta, str(error))
        with preparando:
            cajones.clear()  # las carpetas de cada empresa, otra vez, en la carpeta nueva
        if ACTUAL.get().empresa is None:
            return RedirectResponse("/empresas", status_code=303)
        preparar(ACTUAL.get().empresa.slug)
        return RedirectResponse("/empresa/paso/1" if paso_a_paso_pendiente() else "/", status_code=303)

    def comprobar_compartida(ruta: str, de_datos: Path) -> Path:
        """La carpeta compartida, si vale. La de una empresa no: se elige la de arriba, que tiene dentro una carpeta
        para cada una."""
        elegida = config.comprobar_carpeta(ruta)
        de = next((e for e in cuentas.empresas(de_datos) if e.slug.lower() == elegida.name.lower()), None)
        if de is not None:
            raise config.CarpetaNoVale(
                f"«{elegida.name}» es la carpeta de la empresa «{de.nombre}». Elige la de arriba, la que tiene "
                f"dentro una carpeta para cada empresa: «{elegida.parent}».")
        return elegida

    # --- La instalación: la primera vez que se arranca el portal ---

    def pagina_instalar(request: Request, plantilla: str, **contexto):
        if not instalando[0]:  # ya está instalado: estas páginas ya no tienen nada que hacer
            return RedirectResponse("/", status_code=303)
        local = elegido.get("modo") == config.LOCAL
        return plantillas.TemplateResponse(request, plantilla, {
            "local_elegido": local, "pasos": 3 if local else 4, "error": "", **contexto})

    def sin_modo() -> RedirectResponse | None:
        """Si se llega a un paso sin haber elegido el modo (un enlace guardado, el portal reiniciado a medias), al
        principio."""
        return None if elegido.get("modo") in (config.LOCAL, config.COMPARTIDO) else RedirectResponse("/instalar", 303)

    @app.get("/instalar")
    def instalar_inicio(request: Request):
        return pagina_instalar(request, "instalar.html")

    @app.post("/instalar/modo")
    def instalar_modo(modo: str = Form("")):
        if not instalando[0] or modo not in (config.LOCAL, config.COMPARTIDO):
            return RedirectResponse("/instalar", status_code=303)
        elegido.clear()
        elegido["modo"] = modo
        return RedirectResponse("/instalar/datos" if modo == config.LOCAL else "/instalar/mysql", status_code=303)

    @app.post("/instalar/examinar")
    def instalar_examinar(request: Request, ruta: str = Form(""), accion: str = Form("")):
        """«Examinar» en los pasos de carpetas de la instalación: como el de «/carpeta»."""
        if not instalando[0] or accion not in ("/instalar/datos", "/instalar/carpeta"):
            raise HTTPException(404)
        inicial = Path(ruta.strip().strip('"')) if ruta.strip() else None
        elegida = examinar(inicial if inicial and inicial.is_absolute() and inicial.is_dir() else None)
        return plantillas.TemplateResponse(request, "_carpeta.html", {
            "ruta": elegida or ruta, "error": "", "accion": accion, "examinar_url": "/instalar/examinar",
            "boton": "Siguiente"})

    # Solo en este ordenador: la carpeta de los datos
    @app.get("/instalar/datos")
    def instalar_datos(request: Request):
        return sin_modo() or pagina_instalar(request, "instalar_datos.html",
                                             ruta=elegido.get("datos") or str(config.datos_local(instalador.ajustes)))

    @app.post("/instalar/datos")
    def instalar_datos_guardar(request: Request, ruta: str = Form("")):
        if sin_modo():
            return sin_modo()
        try:
            elegido["datos"] = str(config.comprobar_datos(ruta))
        except config.CarpetaNoVale as error:
            return pagina_instalar(request, "instalar_datos.html", ruta=ruta, error=str(error))
        return RedirectResponse("/instalar/cuenta", status_code=303)

    # Compartido: el MySQL
    @app.get("/instalar/mysql")
    def instalar_mysql(request: Request):
        if elegido.get("cambio"):  # los datos de ahora, salvo la contraseña, para cambiar solo lo que haga falta
            s = srv.leer(instalador.secretos)
            v = {"host": s.host or "", "puerto": str(s.puerto or 3306), "usuario": s.usuario or "", "base": s.base or ""}
            return pagina_instalar(request, "instalar_mysql.html", v=v, cambio=True)
        return sin_modo() or pagina_instalar(request, "instalar_mysql.html", v={"puerto": "3306", "base": "iso42001"})

    def leer_mysql(host, puerto, usuario, clave, base) -> tuple[srv.Servidor | None, str]:
        try:
            s = instalar.servidor_de(host, puerto, usuario, clave, base)
        except instalar.ErrorInstalar as error:
            return None, str(error)
        return s, instalador.probar(s) or ""

    @app.post("/instalar/mysql/probar")
    def instalar_mysql_probar(request: Request, host: str = Form(""), puerto: str = Form(""), usuario: str = Form(""),
                              clave: str = Form(""), base: str = Form("")):
        """«Probar conexión»: solo dice si funciona, sin guardar nada."""
        if not instalando[0]:
            raise HTTPException(404)
        _, error = leer_mysql(host, puerto, usuario, clave, base)
        return plantillas.TemplateResponse(request, "_instalar_prueba.html", {"error": error})

    @app.post("/instalar/mysql")
    def instalar_mysql_guardar(request: Request, host: str = Form(""), puerto: str = Form(""), usuario: str = Form(""),
                               clave: str = Form(""), base: str = Form("")):
        if sin_modo():
            return sin_modo()
        s, error = leer_mysql(host, puerto, usuario, clave, base)
        escrito = {"host": host, "puerto": puerto, "usuario": usuario, "base": base}
        if error:  # lo escrito se queda, salvo la contraseña, que no se vuelve a enseñar
            return pagina_instalar(request, "instalar_mysql.html", error=error, v=escrito, cambio=elegido.get("cambio"))
        try:  # si el MySQL ya tiene cuentas, es un equipo que ya existe: la carpeta es el último paso
            db.usar_servidor(instalador.usar(s))
            equipo = instalar.hay_cuentas(instalador.datos_compartido)
        except srv.SinConexion:
            equipo = False
        if elegido.get("cambio"):
            # Datos nuevos en un portal que ya funcionaba: tiene que ser el MySQL del equipo, no uno vacío
            if not equipo:
                db.usar_servidor(instalador.servidor())
                return pagina_instalar(request, "instalar_mysql.html", v=escrito, cambio=True, error=(
                    "Conecta, pero esa base de datos no tiene las cuentas de tu equipo. Revisa el nombre de la base "
                    "de datos."))
            config.escribir_secretos(instalador.secretos, s.host, s.puerto, s.usuario, s.clave, s.base)
            ponerse_en(config.COMPARTIDO)
            elegido.clear()
            return RedirectResponse("/", status_code=303)
        config.escribir_secretos(instalador.secretos, s.host, s.puerto, s.usuario, s.clave, s.base)
        elegido["mysql"] = True
        elegido["equipo"] = equipo
        return RedirectResponse("/instalar/carpeta", status_code=303)

    # Cambiar los datos del MySQL de un portal que ya funcionaba: desde «Sin conexión», por ejemplo
    # cuando el equipo cambia la contraseña del MySQL. Se vuelve al paso del MySQL; nada más se toca
    def puede_cambiar_mysql() -> bool:
        return instalador is not None and not instalando[0] and instalador.modo() == config.COMPARTIDO

    @app.post("/sin-conexion/mysql")
    def cambiar_mysql():
        if not puede_cambiar_mysql():
            raise HTTPException(404)
        elegido.clear()
        elegido.update(modo=config.COMPARTIDO, cambio=True)
        instalando[0] = True
        return RedirectResponse("/instalar/mysql", status_code=303)

    @app.post("/instalar/cancelar")
    def cancelar_cambio_mysql():
        """«Dejarlo como estaba»: el portal sigue con los datos de antes."""
        if instalando[0] and elegido.get("cambio"):
            elegido.clear()
            ponerse_en(config.COMPARTIDO)
        return RedirectResponse("/", status_code=303)

    # Compartido: la carpeta de los archivos, la misma página que «/carpeta»
    def pagina_carpeta_instalar(request: Request, ruta: str, error: str = ""):
        """Si el MySQL ya tiene cuentas (un compañero que se une), es el último paso, y se dice antes."""
        equipo = bool(elegido.get("equipo"))
        return pagina_instalar(request, "carpeta.html", ruta=ruta, error=error, perdida=None, suyas=[],
                               instalacion=True, equipo=equipo, **({"pasos": 3} if equipo else {}))

    @app.get("/instalar/carpeta")
    def instalar_carpeta(request: Request):
        if sin_modo() or not elegido.get("mysql"):
            return RedirectResponse("/instalar", status_code=303)
        return pagina_carpeta_instalar(request, str(config.carpeta_elegida(instalador.ajustes) or ""))

    @app.post("/instalar/carpeta")
    def instalar_carpeta_guardar(request: Request, ruta: str = Form("")):
        if sin_modo() or not elegido.get("mysql"):
            return RedirectResponse("/instalar", status_code=303)
        try:
            db.usar_servidor(instalador.servidor())
            compartidos = instalador.datos_compartido
            ya_hay = instalar.hay_cuentas(compartidos)
            config.guardar_carpeta(str(comprobar_compartida(ruta, compartidos)), instalador.ajustes)
        except config.CarpetaNoVale as error:
            return pagina_carpeta_instalar(request, ruta, str(error))
        except srv.SinConexion:
            return pagina_carpeta_instalar(
                request, ruta, "No se llega al MySQL. Vuelve al paso anterior y pulsa «Probar conexión».")
        if ya_hay:  # un compañero que se une a un equipo que ya existe: no se crea nada, entra con su cuenta
            config.guardar_ajustes(instalador.ajustes, modo=config.COMPARTIDO)
            ponerse_en(config.COMPARTIDO)
            return RedirectResponse("/entrar?instalado=equipo", status_code=303)
        return RedirectResponse("/instalar/cuenta", status_code=303)

    # Los dos modos: la primera cuenta y la primera empresa
    @app.get("/instalar/cuenta")
    def instalar_cuenta(request: Request):
        if sin_modo() or not (elegido.get("datos") or elegido.get("mysql")):
            return RedirectResponse("/instalar", status_code=303)
        return pagina_instalar(request, "instalar_cuenta.html", v={})

    @app.post("/instalar/cuenta")
    def instalar_cuenta_guardar(request: Request, nombre: str = Form(""), correo_: str = Form("", alias="correo"),
                                clave: str = Form(""), repetida: str = Form(""), empresa: str = Form("")):
        if sin_modo() or not (elegido.get("datos") or elegido.get("mysql")):
            return RedirectResponse("/instalar", status_code=303)
        local = elegido["modo"] == config.LOCAL
        destino = Path(elegido["datos"]) if local else instalador.datos_compartido
        try:
            db.usar_servidor(None if local else instalador.servidor())
            u, e = instalar.crear_primera(destino, nombre, correo_, clave, repetida, empresa)
        except (instalar.ErrorInstalar, srv.SinConexion) as error:
            return pagina_instalar(request, "instalar_cuenta.html", error=str(error),
                                   v={"nombre": nombre, "correo": correo_, "empresa": empresa})
        if local:
            config.guardar_ajustes(instalador.ajustes, modo=config.LOCAL, datos=destino)
        else:
            config.guardar_ajustes(instalador.ajustes, modo=config.COMPARTIDO)
        ponerse_en(elegido["modo"])
        elegido.clear()
        # Ya dentro, en su empresa, en el paso a paso del cuestionario: como la primera vez que se entra en una
        token = secrets.token_urlsafe(32)
        sesiones[token] = Sesion(u, e)
        r = RedirectResponse("/empresa/paso/1", status_code=303)
        r.set_cookie(COOKIE, token, httponly=True, samesite="lax")
        return r

    # --- Administrar: cuentas y empresas desde el portal ---

    HECHO = {  # lo que dice la página al volver de cada cambio; {n} es el nombre de la cuenta o la empresa
        "cuenta": "Cuenta creada: {n}. Pásale su correo y la contraseña que has escrito.",
        "empresas": "Guardado en qué empresas entra {n}.",
        "clave": "Contraseña de {n} cambiada. Pásale la nueva.",
        "quitada": "{n} ya no puede entrar. Lo que hizo se queda en «Actividad».",
        "activada": "{n} ya puede entrar otra vez.",
        "admin": "{n} ya es administrador.",
        "no-admin": "{n} ya no es administrador.",
        "empresa": "Empresa creada: {n}. Marca quién entra en ella.",
        "nombre": "Nombre cambiado: ahora la empresa se llama {n}.",
    }

    def solo_administrador() -> cuentas.Usuario:
        s = ACTUAL.get()
        if not s.administrador:  # a los demás, como si no existiera
            raise HTTPException(404)
        return s.usuario

    def pagina_administrar(request: Request, error: str = "", nueva: dict | None = None, hecho: str = "",
                           de: str = "", ancla: str = ""):
        """`de`: de quién es lo hecho, «c<número>» si es una cuenta o «e<carpeta>» si es una empresa (en la dirección
        va eso, no su nombre)."""
        solo_administrador()
        donde = ""  # el mensaje de lo hecho sale junto a lo cambiado: la página salta allí
        if de.startswith("c") and de[1:].isdigit():
            donde = f"cuenta-{de[1:]}"
            de = getattr(cuentas.usuario_por_id(datos, int(de[1:])), "nombre", "")
        elif de.startswith("e"):
            donde = "empresas"
            de = getattr(cuentas.empresa(datos, de[1:]), "nombre", "")
        todas = cuentas.empresas(datos)
        admins = cuentas.administradores(datos)
        filas = [{"u": u, "admin": u.id in admins,  # las suyas, sin las de todos (el General): esas no se marcan
                  "suyas": {e.slug for e in cuentas.empresas_de(datos, u.id) if not e.todos}}
                 for u in sorted(cuentas.usuarios(datos), key=lambda u: not u.activo)]  # las quitadas, al final
        return plantillas.TemplateResponse(request, "administrar.html", {
            "filas": filas, "empresas": [e for e in todas if not e.todos], "de_todos": [e for e in todas if e.todos],
            "error": error, "ancla": ancla, "nueva": nueva or {}, "donde": donde,
            "hecho": HECHO[hecho].format(n=de) if hecho in HECHO else "", "yo": ACTUAL.get().usuario.id})

    def volver_a_administrar(hecho: str, de: str, ancla: str = "") -> RedirectResponse:
        """`de`: «c<número>» o «e<carpeta>» (ver pagina_administrar)."""
        return RedirectResponse(f"/administrar?hecho={hecho}&de={quote(de)}" + (f"#{ancla}" if ancla else ""),
                                status_code=303)

    def cuenta_o_404(uid: int) -> cuentas.Usuario:
        u = cuentas.usuario_por_id(datos, uid)
        if u is None:
            raise HTTPException(404)
        return u

    @app.get("/administrar")
    def administrar(request: Request, hecho: str = "", de: str = ""):
        return pagina_administrar(request, hecho=hecho, de=de)

    @app.post("/administrar/cuenta")
    async def administrar_nueva_cuenta(request: Request):
        solo_administrador()
        f = await request.form()
        nueva = {"nombre": f.get("nombre", ""), "correo": f.get("correo", ""), "empresas": set(f.getlist("empresas"))}
        try:
            cuentas.comprobar_clave(f.get("clave", ""))
            u = cuentas.crear_usuario(datos, nueva["correo"], nueva["nombre"], f.get("clave", ""))
        except cuentas.ErrorCuentas as error:
            return pagina_administrar(request, error=str(error), nueva=nueva, ancla="nueva-cuenta")
        cuentas.poner_empresas(datos, u.correo, nueva["empresas"])
        return volver_a_administrar("cuenta", f"c{u.id}", f"cuenta-{u.id}")

    @app.post("/administrar/cuenta/{uid}/empresas")
    async def administrar_empresas_de(request: Request, uid: int):
        solo_administrador()
        u = cuenta_o_404(uid)
        cuentas.poner_empresas(datos, u.correo, set((await request.form()).getlist("empresas")))
        return volver_a_administrar("empresas", f"c{u.id}", f"cuenta-{u.id}")

    @app.post("/administrar/cuenta/{uid}/clave")
    def administrar_clave(request: Request, uid: int, clave: str = Form("")):
        solo_administrador()
        u = cuenta_o_404(uid)
        try:
            cuentas.comprobar_clave(clave)
        except cuentas.ErrorCuentas as error:
            return pagina_administrar(request, error=f"{u.nombre}: {error}", ancla=f"cuenta-{u.id}")
        cuentas.cambiar_clave(datos, u.correo, clave)
        return volver_a_administrar("clave", f"c{u.id}", f"cuenta-{u.id}")

    # Uno mismo también puede quitarse (con confirmación en la página), siempre que quede otro administrador: lo
    # comprueba cuentas. Al quitarse, ya no ve «Administrar» (o ya no entra), así que no se vuelve allí.

    @app.post("/administrar/cuenta/{uid}/entra")
    def administrar_entra(request: Request, uid: int, si: int = Form(0)):
        solo_administrador()
        u = cuenta_o_404(uid)
        try:
            cuentas.activar(datos, u.correo, bool(si))
        except cuentas.ErrorCuentas as error:
            return pagina_administrar(request, error=f"{u.nombre}: {error}", ancla=f"cuenta-{u.id}")
        if not si and u.id == ACTUAL.get().usuario.id:
            return RedirectResponse("/entrar", status_code=303)
        return volver_a_administrar("activada" if si else "quitada", f"c{u.id}", f"cuenta-{u.id}")

    @app.post("/administrar/cuenta/{uid}/administrador")
    def administrar_administrador(request: Request, uid: int, si: int = Form(0)):
        solo_administrador()
        u = cuenta_o_404(uid)
        try:
            cuentas.administrar(datos, u.correo, bool(si))
        except cuentas.ErrorCuentas as error:
            return pagina_administrar(request, error=f"{u.nombre}: {error}", ancla=f"cuenta-{u.id}")
        if not si and u.id == ACTUAL.get().usuario.id:
            return RedirectResponse("/empresas", status_code=303)
        return volver_a_administrar("admin" if si else "no-admin", f"c{u.id}", f"cuenta-{u.id}")

    @app.post("/administrar/empresa")
    def administrar_nueva_empresa(request: Request, nombre: str = Form("")):
        solo_administrador()
        try:
            e = cuentas.crear_empresa(datos, nombre)
        except cuentas.ErrorCuentas as error:
            return pagina_administrar(request, error=str(error), ancla="empresas")
        return volver_a_administrar("empresa", f"e{e.slug}", "empresas")

    @app.post("/administrar/empresa/{slug}/nombre")
    def administrar_nombre_empresa(request: Request, slug: str, nombre: str = Form("")):
        """Cambiar el nombre que se ve (con confirmación en la página); la carpeta se queda como está. Queda en la
        «Actividad» de esa empresa."""
        solo_administrador()
        antes = cuentas.empresa(datos, slug)
        if antes is None or antes.slug != slug:
            raise HTTPException(404)
        try:
            e = cuentas.renombrar_empresa(datos, slug, nombre)
        except cuentas.ErrorCuentas as error:
            return pagina_administrar(request, error=str(error), ancla="empresas")
        if e.nombre != antes.nombre:
            ruta = cuentas.bd_de(datos, slug)
            db.iniciar(ruta)
            db.apuntar(ruta, db.el_espacio(ruta)["id"], datetime.combine(hoy(), datetime.now().time()),
                       "Cambia el nombre de la empresa", detalle=f"«{antes.nombre}» → «{e.nombre}»", quien=quien())
        return volver_a_administrar("nombre", f"e{e.slug}", "empresas")

    # --- Cambiar la contraseña propia ---

    @app.get("/contrasena")
    def contrasena(request: Request):
        return plantillas.TemplateResponse(request, "contrasena.html", {"error": "", "hecho": False})

    @app.post("/contrasena")
    def contrasena_cambiar(request: Request, actual: str = Form(""), nueva: str = Form(""), repetida: str = Form("")):
        try:
            cuentas.cambiar_la_propia(datos, ACTUAL.get().usuario.id, actual, nueva, repetida)
        except cuentas.ErrorCuentas as error:
            return plantillas.TemplateResponse(request, "contrasena.html", {"error": str(error), "hecho": False})
        return plantillas.TemplateResponse(request, "contrasena.html", {"error": "", "hecho": True})

    @app.post("/salir")
    def salir(request: Request):
        sesiones.pop(request.cookies.get(COOKIE, ""), None)
        r = RedirectResponse("/entrar", status_code=303)
        r.delete_cookie(COOKIE)
        return r

    def espacio() -> dict:
        """Lo de la empresa en su base de datos, con el nombre que tiene en cuentas.db."""
        guardado = POR_PETICION.get(None)
        if guardado is None:
            guardado = {}
        slug = ACTUAL.get().empresa.slug
        if slug not in guardado:  # se lee una vez por petición: con el MySQL, cada lectura son 50 ms
            guardado[slug] = dict(db.el_espacio(bd()))
        return {**guardado[slug], "nombre": ACTUAL.get().empresa.nombre}

    def quien() -> str:
        """El nombre de quien está dentro: queda en «Actividad», en las marcas y en los cambios."""
        return ACTUAL.get().usuario.nombre

    def apunta(accion: str, requisito: str | None = None, punto: str | None = None,
               sistema: db.Sistema | None = None, detalle: str = "") -> None:
        """Deja constancia en «Actividad», con quién lo ha hecho. La hora es la de ahora; el día, el del
        portal (en las pruebas se simula)."""
        db.apuntar(bd(), espacio()["id"], datetime.combine(hoy(), datetime.now().time()), accion,
                   requisito=requisito, punto=punto, sistema=sistema.nombre if sistema else None, detalle=detalle,
                   quien=quien())

    # Las cuentas de lo pendiente están en pendiente.py: las comparte con los avisos por correo
    def antelacion() -> int:
        return pendiente.antelacion(bd(), espacio()["id"])

    def plazo_general() -> int:
        return pendiente.plazo_general(bd(), espacio()["id"])

    def estado():
        return pendiente.estado(bd(), espacio(), hoy())

    def sin_decidir() -> int:
        return len(guia.A) - len(db.decisiones(bd(), espacio()["id"]))

    def requisito_o_404(codigo: str) -> guia_portal.Requisito:
        req = guia_portal.requisito(codigo)
        if req is None:
            raise HTTPException(404)
        return req

    def volver_a_la_ficha(codigo: str, ancla: str = "", **mensaje: str) -> RedirectResponse:
        # 303: tras un POST, el navegador vuelve a pedir la ficha con GET.
        # El mensaje (p. ej. movido=…) va en la dirección para que la ficha lo enseñe.
        consulta = "&".join(f"{k}={quote(v)}" for k, v in mensaje.items())
        return RedirectResponse(f"/requisitos/{codigo}" + (f"?{consulta}" if consulta else "")
                                + (f"#{ancla}" if ancla else ""), status_code=303)

    def ficha_al_momento(request: Request, codigo: str, ancla: str) -> Response:
        """Tras marcar o desmarcar con la casilla (htmx), la ficha nueva va en la misma respuesta, sin que el
        navegador la vuelva a pedir: con el MySQL, una petición menos. Sin htmx, como siempre."""
        if request.headers.get("HX-Request"):
            return pagina_ficha(request, codigo)
        return volver_a_la_ficha(codigo, ancla)

    def abrir(ruta: Path) -> FileResponse:
        se_ve = ruta.suffix.lower() in SE_VEN
        r = FileResponse(ruta, filename=ruta.name, content_disposition_type="inline" if se_ve else "attachment")
        # Un .svg puede llevar código dentro: se ve, pero sin poder ejecutar nada. No se pone en
        # todos porque el visor de PDF de Chrome no abre con esta protección.
        if ruta.suffix.lower() == ".svg":
            r.headers["Content-Security-Policy"] = "sandbox"
        return r

    def subidos(archivos: list[UploadFile] | None) -> list[UploadFile]:
        # Sin elegir archivo, el navegador manda uno vacío y sin nombre
        return [a for a in archivos or [] if a.filename]

    @app.exception_handler(404)
    async def no_encontrado(request: Request, exc):
        return plantillas.TemplateResponse(request, "no_encontrado.html", {
            "seccion": "requisitos",
            "codigo": request.path_params.get("codigo"),
        }, status_code=404)

    # --- El chat: lo que puede consultar, todo de solo lectura ---

    conversaciones: dict[str, chat.Conversacion] = {}

    def texto_estado_requisito(codigo: str) -> str:
        r = guia_portal.requisito(codigo)
        if r is None:
            return f"No hay ningún requisito «{codigo}»."
        est = estado()
        e = espacio()["id"]
        if not est.aplica(codigo):
            d = db.decisiones(bd(), e).get(codigo)
            return f"{codigo}: NO APLICA en este espacio. Porqué: {d.porque if d else ''}"
        av = est.avance(codigo)
        completo = " · completo" if est.completo(codigo) else ""
        lineas = [f"{codigo} {r.titulo}: {av.hechos} de {av.total} {'puntos' if r.puntos else 'requisitos'}{completo}"]
        nombres = {seguimiento.VENCIDO: "VENCIDO", seguimiento.VENCE_PRONTO: "vence pronto",
                   seguimiento.CUMPLIDO: "cumplido", seguimiento.PENDIENTE: "pendiente",
                   seguimiento.NO_HACE_FALTA: "no hace falta por ahora (solo IA del producto, y no hay)"}
        for p in r.puntos:
            c, estado_p = est.clase(p), est.estado(p)
            linea = f"- {p.codigo}: {nombres.get(estado_p, estado_p)}"
            vence = est.vence(p) if c == seguimiento.PROPIO else None
            if vence:
                linea += f" (vence el {vence:%d/%m/%Y})"
            if c == seguimiento.APOYADO:
                linea += " · se cumple solo con " + ", ".join(p.apoyos)
            if c in (seguimiento.SISTEMA, seguimiento.FICHA):
                partes = [f"{x.nombre}: {nombres.get(est.estado_en(p, x), est.estado_en(p, x))}" for x in est.sistemas_de(p)]
                linea += " · por sistema: " + ("; ".join(partes) if partes else "sin sistemas en el inventario")
            if c == seguimiento.PROPIO:
                archivos = [a.nombre for a in carpetas().archivos(p.codigo)]
                linea += " · archivos: " + (", ".join(archivos) if archivos else "ninguno")
            lineas.append(linea)
        nota = (db.nota(bd(), e, codigo) or "").strip()
        lineas.append("Nota «Cómo lo hacemos aquí»: " + (nota or "(vacía)"))
        return "\n".join(lineas)

    def texto_lo_siguiente() -> str:
        est = estado()
        hay = pendientes(est)
        ob, an = est.obligatorios, est.controles
        lineas = [f"Avance: obligatorios {ob.porcentaje} % ({ob.hechos} de {ob.total}); Anexo A {an.porcentaje} % "
                  f"({an.hechos} de {an.total}). Controles sin decidir: {sin_decidir()}. Hoy es {hoy():%d/%m/%Y}."]
        for titulo, lista in (("Vencido", hay["vencidos"]), ("Vence pronto", hay["pronto"])):
            for a in lista:
                sistema = f" ({a.sistema.nombre})" if a.sistema else ""
                lineas.append(f"- {titulo}: {a.punto.codigo}{sistema} {a.requisito.titulo}, {a.vence:%d/%m/%Y}")
        for r, cuando in hay["recordatorios"]:
            lineas.append(f"- Recordatorio: {r.codigo} {r.titulo}, tocaba el {cuando:%d/%m/%Y}")
        if hay["pregunta"]:
            lineas.append("- Toca preguntar «¿Ha pasado algo?»")
        for x, _ in hay["altas"]:
            lineas.append(f"- Sistema nuevo sin contestar si se reabren riesgos y proveedores: {x.nombre}")
        if len(lineas) == 1:
            lineas.append("Nada vencido, nada que venza pronto ni recordatorios.")
        return "\n".join(lineas)

    def texto_inventario() -> str:
        sistemas = db.sistemas(bd(), espacio()["id"])
        if not sistemas:
            return "El inventario está vacío."
        lineas = []
        for x in sistemas:
            retirado = " · retirado" if x.retirado else ""
            lineas.append(f"- {x.nombre} ({db.TIPOS[x.tipo]}){retirado}")
            for campo, titulo, punto, _, _ in CAMPOS_FICHA:
                lineas.append(f"  - {titulo} ({punto}): {x.campo(campo).strip() or '(vacío)'}")
        return "\n".join(lineas)

    def texto_declaracion() -> str:
        decs = db.decisiones(bd(), espacio()["id"])
        lineas = [f"Decididos {len(decs)} de {len(guia.A)}."]
        for r in guia_portal.requisitos():
            if not r.obligatorio:
                d = decs.get(r.codigo)
                que = (("aplica" if d.aplica else "no aplica") + f" · {d.porque}") if d else "sin decidir"
                lineas.append(f"- {r.codigo} {r.titulo}: {que}")
        return "\n".join(lineas)

    def texto_cuestionario() -> str:
        p = perfil()
        lineas = [f"- {t}: {p['datos'][c] or '(sin contestar)'}" for c, t, _ in guia_portal.DATOS_EMPRESA]
        lineas += [f"- {q.texto} → {guia_portal.RESPUESTAS.get(p['respuestas'][q.clave], 'sin contestar')}"
                   for q in guia_portal.PREGUNTAS]
        lineas += [f"- {q.texto} → {p['abiertas'][q.clave] or '(sin contestar)'}" for q in p["visibles"]]
        lineas += [f"- {f['texto']} → {f['respuesta'] or '(sin contestar)'}" for f in p["de_la_ia"]]
        return "\n".join(lineas)

    def consultas_de(sesion: Sesion) -> chat.Consultas:
        """Lo que puede consultar el chat, siempre de la empresa en la que empezó la conversación: Claude consulta
        desde fuera de la petición, cuando ya no se sabe en qué empresa se está."""
        def de_la_empresa(f):
            def consulta(*args):
                marca = ACTUAL.set(sesion)
                try:
                    preparar(sesion.empresa.slug)
                    return f(*args)
                finally:
                    ACTUAL.reset(marca)
            return consulta
        return chat.Consultas(*(de_la_empresa(f) for f in (texto_estado_requisito, texto_lo_siguiente,
                                                           texto_inventario, texto_declaracion, texto_cuestionario)))

    # Para las pruebas: las consultas del chat en una empresa
    app.state.consultas_de = lambda slug: consultas_de(Sesion(None, cuentas.empresa(datos, slug)))
    empresa_de_conversacion: dict[str, str] = {}

    def trozo_chat(datos: dict) -> str:
        return "data: " + json.dumps(datos, ensure_ascii=False) + "\n\n"

    @app.post("/chat")
    async def chat_preguntar(id: str = Form(""), pregunta: str = Form(""), pagina: str = Form("")):
        """Una pregunta al chat. Responde a trozos (eventos del servidor): el id de la conversación, lo que consulta
        y el texto según sale. Sin id (o uno que ya no existe, o de otra empresa), empieza una conversación nueva."""
        sesion = ACTUAL.get()
        conversacion = conversaciones.get(id)
        if conversacion is None or empresa_de_conversacion.get(id) != sesion.empresa.slug:
            conversacion = chat.Conversacion(consultas_de(Sesion(sesion.usuario, sesion.empresa)))
            conversaciones[conversacion.id] = conversacion
            empresa_de_conversacion[conversacion.id] = sesion.empresa.slug

        async def eventos():
            yield trozo_chat({"id": conversacion.id})
            if not pregunta.strip():
                yield trozo_chat({"error": "Escribe la pregunta."})
            else:
                async for trozo in conversacion.preguntar(pregunta.strip(), pagina.strip() or "Inicio"):
                    yield trozo_chat(trozo)
            yield trozo_chat({"fin": True})

        return StreamingResponse(eventos(), media_type="text/event-stream")

    @app.post("/chat/{id}/parar")
    async def chat_parar(id: str):
        if id in conversaciones:
            await conversaciones[id].parar()
        return Response(status_code=204)

    @app.post("/chat/{id}/cerrar")
    async def chat_cerrar(id: str):
        """Conversación nueva: la de antes se cierra y se olvida."""
        conversacion = conversaciones.pop(id, None)
        if conversacion is not None:
            await conversacion.cerrar()
        return Response(status_code=204)

    @app.get("/buscar")
    def buscar(request: Request, q: str = ""):
        """El buscador (Ctrl K): solo la lista de resultados, que la página pinta."""
        return plantillas.TemplateResponse(request, "_buscar.html", {
            "q": q.strip(), "encontrados": guia_portal.buscar(q)})

    def estados_requisitos(est) -> dict[str, tuple[str, int]]:
        """Para el mapa de Inicio y la lista: el estado de cada requisito y su porcentaje.
        Manda lo peor: vencido, vence pronto; luego completo, en curso o sin empezar. Los que no aplican o no hacen
        falta por ahora, aparte."""
        vencidos = {a.requisito.codigo for a in est.avisos(seguimiento.VENCIDO)}
        pronto = {a.requisito.codigo for a in est.avisos(seguimiento.VENCE_PRONTO)}
        res = {}
        for r in guia_portal.requisitos():
            pct = est.avance(r.codigo).porcentaje
            if not est.aplica(r.codigo):
                res[r.codigo] = ("noaplica", 0)
            elif est.no_hace_falta(r.codigo):
                res[r.codigo] = ("nohacefalta", 0)
            elif r.codigo in vencidos:
                res[r.codigo] = ("vencido", pct)
            elif r.codigo in pronto:
                res[r.codigo] = ("pronto", pct)
            elif est.completo(r.codigo):
                res[r.codigo] = ("hecho", 100)
            else:
                res[r.codigo] = ("curso" if pct else "pendiente", pct)
        return res

    @app.get("/")
    def inicio(request: Request):
        est = estado()
        hay = pendientes(est)
        return plantillas.TemplateResponse(request, "inicio.html", {
            "seccion": "inicio",
            "guia": cifras_guia(),
            "espacio": espacio(),
            "est": est,
            "sin_decidir": sin_decidir(),
            "faltan_empresa": faltan_empresa(),
            # Los avisos son la lista «Lo siguiente» y el mapa de requisitos
            "hay": hay,
            "hoy": hoy(),
            "situaciones": guia_portal.situaciones(),
            "estados": estados_requisitos(est),
            "bloques": guia_portal.por_bloques(),
            "periodo_revision": periodo_revision(),
            "ia_disponible": ia.disponible(),
        })

    # --- La revisión por la dirección: Claude redacta el borrador del acta del periodo ---

    def periodo_revision():
        return revision93.periodo(db.actividad(bd(), espacio()["id"]), hoy())

    @app.post("/revision-direccion")
    async def revision_direccion():
        """El borrador del acta de la revisión por la dirección, en Word. Si no se puede, un texto con el motivo."""
        e = espacio()["id"]
        desde, hasta, anterior = periodo_revision()
        est = estado()
        texto_datos = revision93.mensaje(
            perfil=perfil(), desde=desde, hasta=hasta, anterior=anterior, est=est, actividad=db.actividad(bd(), e),
            cambios=db.cambios(bd(), e), sistemas=db.sistemas(bd(), e), pendientes=pendientes(est),
            nombres_acciones=ACCIONES, requisitos=guia_portal.requisitos())
        try:
            texto = await ia.tarea("revision93", revision93.INSTRUCCIONES, texto_datos, revision93.ESFUERZO)
        except ia.ClaudeNoDisponible as error:
            return Response(str(error), status_code=503, media_type="text/plain; charset=utf-8")
        if not revision93.valida(texto):
            return Response("Claude ha respondido, pero no con la forma esperada. Vuelve a probar.", status_code=502,
                            media_type="text/plain; charset=utf-8")
        apunta("revision93", "9.3", detalle=f"del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}")
        nombre = revision93.nombre_archivo(desde, hasta)
        return Response(revision93.word(texto),
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nombre)}"})

    @app.get("/requisitos")
    def lista_requisitos(request: Request, ver: str = ""):
        """Todos los requisitos, con filtros que se aplican en la página con el estado de cada uno."""
        est = estado()
        return plantillas.TemplateResponse(request, "requisitos.html", {
            "seccion": "requisitos",
            "est": est,
            "ver": ver if ver in FILTROS else "",
            "filtros": FILTROS,
            "estados": estados_requisitos(est),
            "bloques": guia_portal.por_bloques(),
        })

    @app.get("/requisitos/{codigo}")
    def ficha(request: Request, codigo: str, movido: str = "", borrado: str = "", nota: str = ""):
        return pagina_ficha(request, codigo, movido=movido, borrado=borrado, nota=nota)

    def pagina_ficha(request: Request, codigo: str, movido: str = "", borrado: str = "", nota: str = "", **extra):
        req = requisito_o_404(codigo)
        e = espacio()["id"]
        # Con el MySQL, lo que pide la ficha, a la vez: un viaje en vez de once
        est, revisiones, nota_, decisiones, actividad, faltan, guardados = db.a_la_vez(
            estado, lambda: db.revisiones(bd(), e, [p.codigo for p in req.puntos]), lambda: db.nota(bd(), e, codigo),
            lambda: db.decisiones(bd(), e), lambda: db.actividad(bd(), e, codigo), faltan_empresa, lambda: db.ajustes(bd(), e))
        # El revisor: la última revisión de cada punto o línea y si sigue valiendo (misma huella de archivos)
        huellas = {}
        for (punto, sid) in revisiones:
            x = next((x for x in est.sistemas if x.id == sid), None) if sid else None
            if x or not sid:
                rutas = rutas_de(punto, x)
                # Si sigue valiendo, la guardada (también las antiguas, con la fecha); si no, la de ahora
                guardada = revisiones[(punto, sid)]["huella"]
                huellas[(punto, sid)] = guardada if revisor.vigente(rutas, guardada) else revisor.huella(rutas)
            else:
                huellas[(punto, sid)] = ""
        return plantillas.TemplateResponse(request, "ficha.html", {
            "seccion": "requisitos",
            "req": req,
            "est": est,
            "reparto": est.reparto(req),
            "nota": nota_,
            "decision": decisiones.get(codigo),
            "archivos": {p.codigo: carpetas().archivos(p.codigo) for p in req.puntos
                         if est.clase(p) != seguimiento.APOYADO},
            # En los puntos por sistema, los archivos de cada línea que se marca a mano
            "archivos_linea": {(p.codigo, x.id): carpetas().archivos(p.codigo, x) for p in req.puntos
                               if est.clase(p) == seguimiento.SISTEMA and est.clase_linea(p) == seguimiento.PROPIO
                               for x in est.sistemas_de(p)},
            "historial": carpetas().historial(codigo),
            "movido": movido,
            "borrado": borrado,
            "nota_guardada": nota == "guardada",
            # Lo último que se ha hecho en este requisito, al lado de la ficha
            "ultimo": actividad[:5],
            "subido_por": subido_por(actividad),
            "acciones": ACCIONES,
            "revisiones": revisiones,
            "huellas": huellas,
            # Las firmas que había al revisar: se guardan entonces para no abrir los PDF cada vez que se ve la ficha
            "firmas_revision": guardados,
            "ia_disponible": ia.disponible(),
            "con_borrador": borradores.con_borrador(codigo),
            "borrador_generico": codigo not in borradores.PLANTILLAS,  # la base para empezar
            "destino": borradores.donde(codigo) if borradores.con_borrador(codigo) else None,
            "faltan_empresa": faltan,  # el borrador sale mejor con «Sobre la empresa» completo
            **extra,
        })

    def subido_por(actividad: list) -> dict[tuple[str, str, str], str]:
        """Quién subió cada archivo de un requisito: (punto, sistema, archivo) → nombre, según «Actividad».
        Lo que no está ahí se metió desde el Explorador; lo subido antes de los usuarios va sin nombre."""
        quien_ = {}
        for f in reversed(actividad):  # la del requisito, del más antiguo al último: gana el último
            if f["accion"] in ("subido", "version", "documento") and f["punto"]:
                for nombre in f["detalle"].split(", "):
                    quien_[(f["punto"], f["sistema"] or "", nombre)] = f["quien"]
        return quien_

    def punto_propio(codigo: str, punto: str) -> guia_portal.Punto:
        """Solo se marcan a mano los puntos propios: los apoyados se calculan y los de
        sistema esperan al inventario."""
        req = requisito_o_404(codigo)
        p = next((p for p in req.puntos if p.codigo == punto), None)
        if p is None:
            raise HTTPException(404)
        est = estado()
        if not est.aplica(codigo):
            raise HTTPException(400, "Este control no aplica: no se marca")
        if est.clase(p) != seguimiento.PROPIO:
            raise HTTPException(400, "Este punto no se marca a mano")
        return p

    # --- El revisor de archivos: «Revisar con IA» ---

    def rutas_de(punto: str, sistema: db.Sistema | None = None) -> list[Path]:
        return [carpetas().ruta(punto, a.nombre, sistema) for a in carpetas().archivos(punto, sistema)]

    async def revisar(request: Request, codigo: str, punto: str, sistema: db.Sistema | None):
        """Claude lee los archivos del punto (o de la línea del sistema), juntos, y dice si se cumple. Se guarda la
        revisión con la huella de los archivos. No marca nada."""
        ancla = f"{punto}-{sistema.id}" if sistema else punto
        rutas = rutas_de(punto, sistema)

        def con_error(texto: str):
            if request.headers.get("HX-Request"):
                return pagina_ficha(request, codigo, revision_error=texto, revision_ancla=ancla)
            return volver_a_la_ficha(codigo, ancla)

        if not rutas:
            return con_error("Sube antes algún archivo para revisarlo.")
        leidos, demasiado = lectura.leer_todos(rutas)
        if demasiado:
            return con_error(demasiado)
        imagenes = [l.imagen for l in leidos if l.imagen]
        try:
            texto = await ia.tarea("revisor", revisor.INSTRUCCIONES,
                                   revisor.mensaje(punto, perfil(), leidos, sistema.nombre if sistema else ""),
                                   revisor.ESFUERZO, imagenes)
        except ia.ClaudeNoDisponible as e:
            return con_error(str(e))
        rev = revisor.leer(texto)
        if rev is None:
            return con_error("No se pudo comprobar: Claude ha respondido, pero no con la forma esperada. Vuelve a probar.")
        db.guardar_revision(bd(), espacio()["id"], punto, sistema.id if sistema else 0, rev.veredicto, rev.porque,
                            rev.apoyo, rev.falta, revisor.huella(rutas), datetime.combine(hoy(), datetime.now().time()))
        db.guardar_ajuste(bd(), espacio()["id"], f"firmas.{punto}.{sistema.id if sistema else 0}",
                          " · ".join(f for l in leidos for f in l.firmas))
        apunta("revisado", codigo, punto, sistema, detalle={revisor.SI: "SÍ", revisor.NO: "NO"}.get(rev.veredicto, "NO SE PUEDE SABER"))
        if request.headers.get("HX-Request"):
            return pagina_ficha(request, codigo)
        return volver_a_la_ficha(codigo, ancla)

    @app.post("/requisitos/{codigo}/puntos/{punto}/revisar")
    async def revisar_punto(request: Request, codigo: str, punto: str):
        punto_propio(codigo, punto)
        return await revisar(request, codigo, punto, None)

    @app.post("/requisitos/{codigo}/puntos/{punto}/sistemas/{sistema_id}/revisar")
    async def revisar_linea(request: Request, codigo: str, punto: str, sistema_id: int):
        _, x, _ = linea_a_mano(codigo, punto, sistema_id)
        return await revisar(request, codigo, punto, x)

    # --- Los borradores de documentos: plantilla de la guía + cuestionario + inventario. Los redacta
    # Claude sobre esa estructura; sin Claude, sale la plantilla rellena ---

    def preguntas_ia_contestadas() -> list[tuple[str, str]]:
        return [(f["texto"], f["respuesta"]) for f in db.preguntas_ia(bd(), espacio()["id"]) if f["respuesta"]]

    @app.post("/requisitos/{codigo}/borrador")
    async def hacer_borrador(codigo: str):
        requisito_o_404(codigo)
        if not borradores.con_borrador(codigo):
            raise HTTPException(404, "Este requisito no tiene borrador: no se demuestra con un documento")
        e, sistemas, p = espacio()["id"], db.sistemas(bd(), espacio()["id"]), perfil()
        b = borradores.base(codigo, p, sistemas, hoy())
        texto, motivo = None, ""
        if not ia.disponible():
            motivo = "Claude no está disponible en este ordenador."
        else:
            mensaje = borradores.mensaje(b, p, sistemas, [(c, t) for c, t, _, _, _ in CAMPOS_FICHA],
                                         {r.codigo: db.nota(bd(), e, r.codigo) for r in b.requisitos},
                                         preguntas_ia_contestadas(),
                                         # Las pendientes de los otros borradores: las de este se sustituyen al
                                         # rehacerlo, y si contaran, pulsar dos veces daría otro borrador
                                         [f["texto"] for f in db.preguntas_ia(bd(), e)
                                          if not f["respuesta"] and f["documento"] != b.documento])
            huella = borradores.huella(mensaje)
            anterior = db.borrador_ia(bd(), e, b.documento)
            if anterior is not None and anterior["huella"] == huella:
                texto = anterior["texto"]  # no ha cambiado nada de lo que se le da: el mismo de antes
            else:
                try:
                    texto, preguntas = borradores.leer(
                        await ia.tarea("borrador", borradores.INSTRUCCIONES, mensaje, borradores.ESFUERZO), b)
                    db.guardar_borrador_ia(bd(), e, b.documento, huella, texto, hoy())
                    db.poner_preguntas_ia(bd(), e, b.documento, preguntas, hoy())
                except ia.ClaudeNoDisponible as error:
                    motivo = str(error)
                except borradores.EstructuraRota:
                    motivo = "la IA no ha respetado la estructura del documento."
        from portal import word
        if texto is not None:
            datos_word = word.documento(texto, aviso=borradores.AVISO_IA)
            apunta("borrador_ia", codigo, detalle=b.archivo)
        else:
            datos_word = word.documento(b.texto, aviso=borradores.AVISO_SIN_IA.format(motivo=motivo) + (
                "" if b.aviso == borradores.AVISO else " " + b.aviso), unir_lineas=True)
            apunta("borrador", codigo, detalle=b.archivo)
        return Response(datos_word, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(b.archivo)}"})

    @app.post("/empresa/pregunta-ia/{pregunta_id}")
    def contestar_pregunta_ia(request: Request, pregunta_id: int, valor: str = Form("")):
        """Una pregunta de la IA contestada en «Empresa»: la usan todos los borradores siguientes."""
        fila = db.contestar_pregunta_ia(bd(), espacio()["id"], pregunta_id, valor)
        if fila is None:
            raise HTTPException(404)
        if fila["respuesta"] != valor.strip():
            apunta("cuestionario", detalle=fila["texto"])
        if request.headers.get("HX-Request"):
            return plantillas.TemplateResponse(request, "_respuesta.html", {
                "clave": f"ia-{pregunta_id}", "perfil": perfil(), "hora": datetime.now(), "est": estado(),
                "reabrir": [], "bloques": guia_portal.BLOQUES, "abiertas": guia_portal.ABIERTAS,
            })
        return RedirectResponse(f"/empresa#pregunta-ia-{pregunta_id}", status_code=303)

    @app.post("/requisitos/{codigo}/puntos/{punto}/marcar")
    def marcar(request: Request, codigo: str, punto: str):
        punto_propio(codigo, punto)
        db.marcar(bd(), espacio()["id"], punto, hoy(), quien())
        apunta("marcado", codigo, punto)
        return ficha_al_momento(request, codigo, punto)

    @app.post("/requisitos/{codigo}/puntos/{punto}/renovar")
    def renovar(codigo: str, punto: str, archivos: list[UploadFile] | None = File(None)):
        """Con archivo nuevo, los que había pasan al historial."""
        p = punto_propio(codigo, punto)
        if not estado().marcado(p):
            raise HTTPException(400, "Solo se renueva lo que está marcado")
        nuevos = subidos(archivos)
        if nuevos:
            carpetas().sustituir(punto, hoy())
            nombres = [carpetas().guardar(punto, a.filename, a.file) for a in nuevos]
            apunta("version", codigo, punto, detalle=", ".join(nombres))
        db.renovar(bd(), espacio()["id"], punto, hoy(), quien())
        apunta("renovado", codigo, punto)
        return volver_a_la_ficha(codigo, punto)

    # --- Líneas de los puntos por sistema ---

    def linea_a_mano(codigo: str, punto: str, sistema_id: int):
        """Solo se marcan a mano las líneas de los puntos por sistema que no se cumplen solas, de
        sistemas activos a los que les toca el punto."""
        req = requisito_o_404(codigo)
        p = next((p for p in req.puntos if p.codigo == punto), None)
        x = db.sistema(bd(), espacio()["id"], sistema_id)
        if p is None or x is None:
            raise HTTPException(404)
        est = estado()
        if not est.aplica(codigo):
            raise HTTPException(400, "Este control no aplica: no se marca")
        if est.clase(p) != seguimiento.SISTEMA or est.clase_linea(p) != seguimiento.PROPIO:
            raise HTTPException(400, "Esta línea no se marca a mano")
        if x.retirado or not seguimiento.toca(p, x):
            raise HTTPException(400, "Este punto no le toca a este sistema")
        return p, x, est

    def volver_a_la_linea(codigo: str, punto: str, sistema_id: int, **mensaje: str) -> RedirectResponse:
        return volver_a_la_ficha(codigo, f"{punto}-{sistema_id}", **mensaje)

    @app.post("/requisitos/{codigo}/puntos/{punto}/sistemas/{sistema_id}/marcar")
    def marcar_linea(request: Request, codigo: str, punto: str, sistema_id: int):
        _, x, _ = linea_a_mano(codigo, punto, sistema_id)
        db.marcar_linea(bd(), espacio()["id"], punto, sistema_id, hoy(), quien())
        apunta("marcado", codigo, punto, x)
        return ficha_al_momento(request, codigo, f"{punto}-{sistema_id}")

    @app.post("/requisitos/{codigo}/puntos/{punto}/sistemas/{sistema_id}/desmarcar")
    def desmarcar_linea(request: Request, codigo: str, punto: str, sistema_id: int):
        _, x, _ = linea_a_mano(codigo, punto, sistema_id)
        db.desmarcar_linea(bd(), espacio()["id"], punto, sistema_id)
        apunta("desmarcado", codigo, punto, x)
        return ficha_al_momento(request, codigo, f"{punto}-{sistema_id}")

    @app.post("/requisitos/{codigo}/puntos/{punto}/sistemas/{sistema_id}/renovar")
    def renovar_linea(codigo: str, punto: str, sistema_id: int, archivos: list[UploadFile] | None = File(None)):
        p, x, est = linea_a_mano(codigo, punto, sistema_id)
        if not est.marcado_en(p, x):
            raise HTTPException(400, "Solo se renueva lo que está marcado")
        nuevos = subidos(archivos)
        if nuevos:
            carpetas().sustituir(punto, hoy(), x)
            nombres = [carpetas().guardar(punto, a.filename, a.file, x) for a in nuevos]
            apunta("version", codigo, punto, x, ", ".join(nombres))
        db.renovar_linea(bd(), espacio()["id"], punto, sistema_id, hoy(), quien())
        apunta("renovado", codigo, punto, x)
        return volver_a_la_linea(codigo, punto, sistema_id)

    @app.post("/requisitos/{codigo}/puntos/{punto}/sistemas/{sistema_id}/version")
    def version_nueva_linea(codigo: str, punto: str, sistema_id: int, archivos: list[UploadFile] | None = File(None)):
        """Como en los puntos: lo de antes al historial y, si está marcada, se renueva."""
        p, x, est = linea_a_mano(codigo, punto, sistema_id)
        nuevos = subidos(archivos)
        if nuevos:
            carpetas().sustituir(punto, hoy(), x)
            nombres = [carpetas().guardar(punto, a.filename, a.file, x) for a in nuevos]
            apunta("version", codigo, punto, x, ", ".join(nombres))
            if est.marcado_en(p, x):
                db.renovar_linea(bd(), espacio()["id"], punto, sistema_id, hoy(), quien())
                apunta("renovado", codigo, punto, x)
        return volver_a_la_linea(codigo, punto, sistema_id)

    @app.post("/requisitos/{codigo}/puntos/{punto}/sistemas/{sistema_id}/archivos")
    def subir_linea(codigo: str, punto: str, sistema_id: int, archivos: list[UploadFile] | None = File(None)):
        """Subir no marca la línea."""
        _, x, _ = linea_a_mano(codigo, punto, sistema_id)
        for a in subidos(archivos):
            apunta("subido", codigo, punto, x, carpetas().guardar(punto, a.filename, a.file, x))
        return volver_a_la_linea(codigo, punto, sistema_id)

    @app.get("/requisitos/{codigo}/puntos/{punto}/sistemas/{sistema_id}/archivos/{nombre}")
    def abrir_archivo_linea(codigo: str, punto: str, sistema_id: int, nombre: str):
        _, x, _ = linea_a_mano(codigo, punto, sistema_id)
        try:
            return abrir(carpetas().ruta(punto, nombre, x))
        except pruebas.NoEncontrado:
            raise HTTPException(404)

    @app.post("/requisitos/{codigo}/puntos/{punto}/sistemas/{sistema_id}/archivos/{nombre}/quitar")
    def quitar_linea(codigo: str, punto: str, sistema_id: int, nombre: str):
        _, x, _ = linea_a_mano(codigo, punto, sistema_id)
        try:
            en_historial = carpetas().quitar(punto, nombre, hoy(), x)
        except pruebas.NoEncontrado:
            raise HTTPException(404)
        apunta("quitado", codigo, punto, x, nombre)
        return volver_a_la_linea(codigo, punto, sistema_id, movido=en_historial)

    # --- Archivos de cada punto ---

    @app.post("/requisitos/{codigo}/puntos/{punto}/version")
    def version_nueva(codigo: str, punto: str, archivos: list[UploadFile] | None = File(None)):
        """Los archivos que había pasan al historial y queda el nuevo; si está marcado, se renueva
        (o, si no vence, se apunta el día como «revisado»)."""
        p = punto_propio(codigo, punto)
        nuevos = subidos(archivos)
        if nuevos:
            carpetas().sustituir(punto, hoy())
            nombres = [carpetas().guardar(punto, a.filename, a.file) for a in nuevos]
            apunta("version", codigo, punto, detalle=", ".join(nombres))
            if estado().marcado(p):
                db.renovar(bd(), espacio()["id"], punto, hoy(), quien())
                apunta("renovado", codigo, punto)
        return volver_a_la_ficha(codigo, punto)

    @app.post("/requisitos/{codigo}/puntos/{punto}/archivos")
    def subir(codigo: str, punto: str, archivos: list[UploadFile] | None = File(None)):
        """Subir no marca el punto."""
        punto_propio(codigo, punto)
        for a in subidos(archivos):
            apunta("subido", codigo, punto, detalle=carpetas().guardar(punto, a.filename, a.file))
        return volver_a_la_ficha(codigo, punto)

    @app.get("/requisitos/{codigo}/puntos/{punto}/archivos/{nombre}")
    def abrir_archivo(codigo: str, punto: str, nombre: str):
        punto_propio(codigo, punto)
        try:
            return abrir(carpetas().ruta(punto, nombre))
        except pruebas.NoEncontrado:
            raise HTTPException(404)

    @app.post("/requisitos/{codigo}/puntos/{punto}/archivos/{nombre}/quitar")
    def quitar(codigo: str, punto: str, nombre: str):
        punto_propio(codigo, punto)
        try:
            en_historial = carpetas().quitar(punto, nombre, hoy())
        except pruebas.NoEncontrado:
            raise HTTPException(404)
        apunta("quitado", codigo, punto, detalle=nombre)
        return volver_a_la_ficha(codigo, punto, movido=en_historial)

    @app.get("/requisitos/{codigo}/historial/{nombre}")
    def abrir_historial(codigo: str, nombre: str):
        requisito_o_404(codigo)
        try:
            return abrir(carpetas().ruta_historial(codigo, nombre))
        except pruebas.NoEncontrado:
            raise HTTPException(404)

    @app.post("/requisitos/{codigo}/historial/{nombre}/borrar")
    def borrar(codigo: str, nombre: str):
        """Para siempre; la ficha pide confirmación antes."""
        requisito_o_404(codigo)
        try:
            carpetas().borrar(codigo, nombre)
        except pruebas.NoEncontrado:
            raise HTTPException(404)
        apunta("borrado", codigo, detalle=nombre)
        return volver_a_la_ficha(codigo, "historial", borrado=nombre)

    @app.post("/requisitos/{codigo}/reabrir")
    def reabrir(codigo: str):
        """Ha pasado algo que afecta al requisito: sus puntos propios vuelven a Pendiente."""
        req = requisito_o_404(codigo)
        if not seguimiento.se_reabre(req):
            raise HTTPException(400, "Este requisito no se reabre por evento")
        reabrir_requisito(req, estado().a_reabrir(req), "desde su ficha")
        return volver_a_la_ficha(codigo)

    def reabrir_requisito(req, lista, motivo: str) -> None:
        """Lo marcado vuelve a pendiente y queda apuntado con el motivo."""
        for p, x in lista:
            if x is None:
                db.desmarcar(bd(), espacio()["id"], p.codigo)
            else:
                db.desmarcar_linea(bd(), espacio()["id"], p.codigo, x.id)
        if lista:
            apunta("reabierto", req.codigo, detalle=motivo)

    @app.post("/requisitos/{codigo}/puntos/{punto}/desmarcar")
    def desmarcar(request: Request, codigo: str, punto: str):
        punto_propio(codigo, punto)
        db.desmarcar(bd(), espacio()["id"], punto)
        apunta("desmarcado", codigo, punto)
        return ficha_al_momento(request, codigo, punto)

    def guardado_a_las(id_: str, texto: str = "") -> Response:
        """El «Guardado» discreto que sustituye al botón."""
        texto = texto or f"Guardado a las {datetime.now():%H:%M}"
        return Response(f'<span id="{id_}" class="guardado-estado" role="status">{texto}</span>', media_type="text/html")

    @app.post("/requisitos/{codigo}/nota")
    def guardar_nota(request: Request, codigo: str, texto: str = Form("")):
        requisito_o_404(codigo)
        db.guardar_nota(bd(), espacio()["id"], codigo, texto)
        if request.headers.get("HX-Request"):
            return guardado_a_las("nota-estado")  # se guarda sola: solo cambia el aviso
        return volver_a_la_ficha(codigo, "nota", nota="guardada")  # sin JavaScript, con el botón

    # --- Declaración de Aplicabilidad ---

    def controles_por_bloque():
        bloques: dict[str, list] = {}
        for r in guia_portal.requisitos():
            if not r.obligatorio:
                bloques.setdefault(r.bloque, []).append(r)
        return list(bloques.items())

    def pagina_declaracion(request: Request, pestaña: str, **extra):
        decs = db.decisiones(bd(), espacio()["id"])
        return plantillas.TemplateResponse(request, "declaracion.html", {
            "seccion": "declaracion",
            "pestaña": pestaña,
            "decisiones": decs,
            "aplican": sum(d.aplica for d in decs.values()),
            "no_aplican": sum(not d.aplica for d in decs.values()),
            "total": len(guia.A),
            "perfil": perfil(),
            "preguntas": guia_portal.PREGUNTAS,
            "datos_empresa": guia_portal.DATOS_EMPRESA,
            "respuestas_posibles": guia_portal.RESPUESTAS,
            "propuestas": db.propuestas(bd(), espacio()["id"]),
            "ia_disponible": ia.disponible(),
            **extra,
        })

    def pagina_controles(request: Request, **extra):
        # El último cambio de cada control, para enseñarlo debajo (los cambios vienen del más reciente)
        ultimo = {}
        for c in db.cambios(bd(), espacio()["id"]):
            if c["antes"] != "sin decidir":
                ultimo.setdefault(c["control"], c)
        return pagina_declaracion(request, "controles", bloques=controles_por_bloque(), ultimo=ultimo, **extra)

    def carpetas_no_aplica() -> list[str]:
        """La marca «(no aplica)» en las carpetas, según la Declaración. Devuelve las que no se han
        podido renombrar por tener un archivo abierto."""
        e = espacio()["id"]
        return carpetas().poner_al_dia({c for c, d in db.decisiones(bd(), e).items() if not d.aplica})

    # --- Cuestionario de la empresa ---

    def sugerencias() -> dict[str, tuple[str, str]]:
        """Lo que el inventario ya dice de dos preguntas: si hay IA del producto y si hay herramientas de terceros."""
        activos = [x for x in db.sistemas(bd(), espacio()["id"]) if x.retirado is None]
        res = {}
        for clave, tipo in (("desarrolla", "producto"), ("proveedores", "herramienta")):
            suyos = [x.nombre for x in activos if x.tipo == tipo]
            if suyos:
                que = "una IA que ofrecéis a clientes" if tipo == "producto" else "una IA que usa el equipo"
                res[clave] = ("si", f"Según tu inventario: {', '.join(suyos)} {'es' if len(suyos) == 1 else 'son'} {que}.")
        return res

    def perfil() -> dict:
        """El perfil de la empresa: los datos generales y las respuestas del cuestionario. Si una pregunta no se ha
        contestado y el inventario la responde, vale su sugerencia. Lo usan la Declaración, el chat y los borradores."""
        e = espacio()["id"]
        todo = db.ajustes(bd(), e)  # de una vez: con el MySQL, cada lectura son 50 ms
        datos_ = {c: todo.get(f"empresa.{c}", "") for c, _, _ in guia_portal.DATOS_EMPRESA}
        guardadas = {q.clave: todo.get(f"cuestionario.{q.clave}", "") for q in guia_portal.PREGUNTAS}
        sug = sugerencias()
        respuestas = {c: v or (sug[c][0] if c in sug else "") for c, v in guardadas.items()}
        # «No lo sé» queda por aclarar, como una en blanco: el borrador saca ese apartado con su [POR COMPLETAR]
        hechas = sum(bool(v) for v in datos_.values()) + sum(v in ("si", "no") for v in respuestas.values())
        total = len(datos_) + len(respuestas)
        # Las abiertas: las del bloque 5 solo si desarrolla IA. No cuentan para «completo», que es lo
        # que necesita la Declaración, pero sí para lo que queda por aclarar
        visibles = guia_portal.abiertas(respuestas["desarrolla"])
        abiertas = {q.clave: todo.get(f"abierta.{q.clave}", "") for q in guia_portal.ABIERTAS}
        abiertas_hechas = sum(bool(abiertas[q.clave]) for q in visibles)
        de_la_ia = db.preguntas_ia(bd(), e)  # las que dejan los borradores, también por aclarar
        return {"datos": datos_, "respuestas": respuestas, "guardadas": guardadas,
                "sugerencias": {c: s for c, s in sug.items() if not guardadas[c]},
                "hechas": hechas, "total": total, "completo": hechas == total,
                "abiertas": abiertas, "visibles": visibles, "de_la_ia": de_la_ia,
                "todas_hechas": hechas + abiertas_hechas + sum(bool(f["respuesta"]) for f in de_la_ia),
                "todas_total": total + len(visibles) + len(de_la_ia),
                "sin_empezar": not (any(datos_.values()) or any(guardadas.values()) or any(abiertas.values()))}

    def faltan_empresa() -> int:
        """Cuántas preguntas de «Empresa» quedan por aclarar (sin contestar o en «No lo sé»), también las abiertas.
        Lo avisan Inicio y los borradores."""
        p = perfil()
        return p["todas_total"] - p["todas_hechas"]

    def guardar_respuesta(clave: str, valor: str) -> tuple[str, str] | None:
        """Guarda una respuesta del cuestionario, un dato general o una pregunta abierta y lo apunta en
        «Actividad». Devuelve lo que había antes y lo que hay ahora si ha cambiado; None si no."""
        valor = valor.strip()
        preguntas = {q.clave: q for q in guia_portal.PREGUNTAS}
        datos_ = {c: titulo for c, titulo, _ in guia_portal.DATOS_EMPRESA}
        abiertas = {q.clave: q for q in guia_portal.ABIERTAS}
        if clave in preguntas:
            if valor not in guia_portal.RESPUESTAS:
                raise HTTPException(400, "Respuesta no válida")
            ajuste, que = f"cuestionario.{clave}", f"{preguntas[clave].texto} {guia_portal.RESPUESTAS[valor]}"
        elif clave in datos_:
            ajuste, que = f"empresa.{clave}", f"{datos_[clave]}: {valor or '(vacío)'}"
        elif clave in abiertas:
            ajuste, que = f"abierta.{clave}", abiertas[clave].texto
        else:
            raise HTTPException(404)
        e = espacio()["id"]
        antes = db.ajuste(bd(), e, ajuste, "")
        if antes == valor:
            return None
        db.guardar_ajuste(bd(), e, ajuste, valor)
        apunta("cuestionario", detalle=que)
        return antes, valor

    def situacion_de(clave: str) -> guia_portal.Situacion | None:
        """Los requisitos que dependen de una respuesta: los controles que decide una de Sí/No, o los de la
        columna «Para qué» de una abierta. Los datos generales no reabren nada."""
        for q in guia_portal.PREGUNTAS:
            if q.clave == clave:
                return guia_portal.Situacion(clave, q.texto, "", [guia_portal.REQUISITOS[c] for c in q.controles])
        for q in guia_portal.ABIERTAS:
            if q.clave == clave:
                return guia_portal.Situacion(clave, q.texto, "", q.requisitos)
        return None

    def para_reabrir(clave: str, cambio: tuple[str, str] | None) -> list:
        """Si se ha cambiado una respuesta que ya tenía algo, los requisitos que dependen de ella y tienen algo que
        reabrir. Al contestar por primera vez, nada: no hay nada hecho con la respuesta anterior."""
        sit = situacion_de(clave)
        if not cambio or not cambio[0] or sit is None:
            return []
        lista = afectados(sit, estado())
        return lista if any(cosas for _, cosas in lista) else []

    @app.post("/empresa/respuesta/{clave}")
    @app.post("/declaracion/cuestionario/{clave}")
    def contestar(request: Request, clave: str, valor: str = Form("")):
        """Una respuesta del cuestionario, un dato general o una pregunta abierta. Se guarda sola al cambiarla; si
        cambia una que ya tenía algo, propone reabrir lo que depende de ella."""
        cambio = guardar_respuesta(clave, valor)
        if request.headers.get("HX-Request"):
            p = perfil()
            return plantillas.TemplateResponse(request, "_respuesta.html", {
                "clave": clave, "perfil": p, "hora": datetime.now(), "est": estado(),
                "reabrir": para_reabrir(clave, cambio), "bloques": guia_portal.BLOQUES, "abiertas": guia_portal.ABIERTAS,
            })
        return RedirectResponse(f"/empresa#pregunta-{clave}", status_code=303)

    # --- La página «Empresa» y el paso a paso ---

    def pagina_empresa(request: Request, **extra):
        return plantillas.TemplateResponse(request, "empresa.html", {
            "seccion": "empresa",
            "perfil": perfil(),
            "preguntas": guia_portal.PREGUNTAS,
            "datos_empresa": guia_portal.DATOS_EMPRESA,
            "respuestas_posibles": guia_portal.RESPUESTAS,
            "abiertas": guia_portal.ABIERTAS,
            "bloques": guia_portal.BLOQUES,
            **extra,
        })

    @app.get("/empresa")
    def empresa(request: Request, reabiertos: str = ""):
        return pagina_empresa(request, reabiertos=reabiertos)

    @app.post("/empresa/reabrir/{clave}")
    async def reabrir_por_respuesta(request: Request, clave: str):
        sit = situacion_de(clave)
        if sit is None:
            raise HTTPException(404)
        form = await request.form()
        hechos = reabrir_elegidos(sit, set(form.getlist("requisitos")), f"por cambiar «{sit.titulo}»")
        return RedirectResponse(f"/empresa?reabiertos={quote(', '.join(hechos) or 'nada')}#pregunta-{clave}",
                                status_code=303)

    VISTO = "cuestionario_visto"  # el paso a paso ya salió en esta empresa

    def pasos() -> list[tuple[str, str]]:
        """Los pasos: datos generales, las de Sí/No y un bloque de abiertas en cada uno (el 5, si desarrolla IA)."""
        visibles = perfil()["visibles"]
        return ([("datos", "Datos generales"), ("sino", "Cómo es vuestra IA")]
                + [(f"bloque{b}", titulo) for b, titulo in guia_portal.BLOQUES.items()
                   if any(q.bloque == b for q in visibles)])

    def paso_a_paso_pendiente() -> bool:
        """Sale la primera vez que se entra en una empresa con el cuestionario sin empezar, una sola vez."""
        return db.ajuste(bd(), espacio()["id"], VISTO, "") != "1" and perfil()["sin_empezar"]

    @app.get("/empresa/paso/{n}")
    def paso(request: Request, n: int):
        lista = pasos()
        if not 1 <= n <= len(lista):
            raise HTTPException(404)
        clave, titulo = lista[n - 1]
        return plantillas.TemplateResponse(request, "empresa_paso.html", {
            "seccion": "empresa", "n": n, "pasos": lista, "clave": clave, "titulo": titulo, "perfil": perfil(),
            "preguntas": guia_portal.PREGUNTAS, "datos_empresa": guia_portal.DATOS_EMPRESA,
            "respuestas_posibles": guia_portal.RESPUESTAS,
            "abiertas": [q for q in perfil()["visibles"] if clave == f"bloque{q.bloque}"],
        })

    @app.post("/empresa/paso/{n}")
    async def paso_siguiente(request: Request, n: int):
        """«Siguiente» guarda lo escrito en el paso; «Saltar», no. Al terminar, a Inicio y no vuelve a salir."""
        form = await request.form()
        if form.get("ir") == "siguiente":
            for nombre, valor in form.multi_items():
                if nombre.startswith("r.") and valor.strip():
                    guardar_respuesta(nombre[2:], valor)
        if form.get("ir") == "terminar" or n >= len(pasos()):
            db.guardar_ajuste(bd(), espacio()["id"], VISTO, "1")
            return RedirectResponse("/", status_code=303)
        return RedirectResponse(f"/empresa/paso/{n + 1}", status_code=303)

    # --- Ayuda con la Declaración: Claude propone, la persona decide ---

    def guardar_propuestas(nuevas: dict, aclaraciones: dict | None = None) -> None:
        e = espacio()["id"]
        for c, p in nuevas.items():
            db.guardar_propuesta(bd(), e, c, p.decision, p.porque, p.apoyo,
                                 (aclaraciones or {}).get(c, ("", ""))[1], p.quien, p.aviso)

    def volver_a_la_declaracion(request: Request, control: str = "", **extra):
        if request.headers.get("HX-Request"):
            return pagina_controles(request, **extra)
        return RedirectResponse("/declaracion" + (f"#control-{control}" if control else "#propuestas"), status_code=303)

    @app.post("/declaracion/proponer")
    async def proponer(request: Request):
        """Propone si aplica cada uno de los 38 controles: los claros los decide el portal con el
        cuestionario; Claude, los dudosos, y redacta el porqué de todos. Sustituye las propuestas que hubiera. Si Claude
        no está o no responde con la forma pedida, se guardan igual las del portal y las demás se quedan como estaban."""
        e = espacio()["id"]
        todos, sistemas = propuestas.controles(), db.sistemas(bd(), e)
        fijas = propuestas.fijas(perfil(), sistemas)
        error = ""
        try:
            if not ia.disponible():
                raise ia.ClaudeNoDisponible("Claude no está disponible: no se encuentra Claude Code en este ordenador.")
            texto = await ia.tarea("declaracion", propuestas.INSTRUCCIONES,
                                   propuestas.mensaje(perfil(), sistemas, todos, fijas_=fijas), propuestas.ESFUERZO)
            leidas = propuestas.leer(texto, todos)
            if not leidas:
                error = "Claude ha respondido, pero no con la forma esperada. Vuelve a probar."
        except ia.ClaudeNoDisponible as fallo:
            error, leidas = str(fallo), {}
        if error:
            if not fijas:
                return volver_a_la_declaracion(request, error_ia=error)
            for c in fijas:
                db.quitar_propuesta(bd(), e, c)
            guardar_propuestas(propuestas.combinar(fijas, {}, todos))
            apunta("propuestas", detalle=f"{len(fijas)} controles por tus respuestas; sin la IA")
            return volver_a_la_declaracion(request, error_ia=f"{error} Se han propuesto los {len(fijas)} controles "
                                                             "que se deciden con tus respuestas; los demás, cuando "
                                                             "Claude esté.")
        nuevas = propuestas.combinar(fijas, leidas, todos)
        for c in db.propuestas(bd(), e):
            db.quitar_propuesta(bd(), e, c)
        guardar_propuestas(nuevas)
        faltan = len(todos) - len(nuevas)
        apunta("propuestas", detalle=f"{len(nuevas)} controles ({len(fijas)} por tus respuestas)"
                                     + (f"; {faltan} sin propuesta" if faltan else ""))
        return volver_a_la_declaracion(request, sin_propuesta=faltan)

    def aceptar_una(control: str, p) -> None:
        """Como decidirlo a mano: la decisión, su porqué en «Cambios» y «Actividad», y la carpeta."""
        e = espacio()["id"]
        aplica = p["decision"] == propuestas.APLICA
        db.decidir(bd(), e, control, aplica, p["porque"], "", hoy(), quien())
        apunta("aplica" if aplica else "no_aplica", control,
               detalle=f"{p['porque']} ({propuestas.quien_decide(p['quien'], p['apoyo'])})")
        db.quitar_propuesta(bd(), e, control)

    def propuesta_o_400(control: str, decidible: bool = True):
        p = db.propuestas(bd(), espacio()["id"]).get(control)
        if p is None:
            raise HTTPException(404, "Este control no tiene propuesta")
        if decidible and p["decision"] == propuestas.FALTA:
            raise HTTPException(400, "Falta saber algo: contesta la pregunta antes")
        return p

    @app.post("/declaracion/propuesta/{control}/aceptar")
    def aceptar_propuesta(request: Request, control: str):
        aceptar_una(control, propuesta_o_400(control))
        carpetas_no_aplica()
        return volver_a_la_declaracion(request, control, guardado_control=control)

    @app.post("/declaracion/propuestas/aceptar-todas")
    def aceptar_todas(request: Request):
        """Solo las de controles sin decidir y que no sean FALTA SABER: cambiar un control ya decidido va uno a uno."""
        e = espacio()["id"]
        decididos = db.decisiones(bd(), e)
        for c, p in db.propuestas(bd(), e).items():
            if c not in decididos and p["decision"] != propuestas.FALTA:
                aceptar_una(c, p)
        carpetas_no_aplica()
        return volver_a_la_declaracion(request)

    @app.post("/declaracion/propuesta/{control}/descartar")
    def descartar_propuesta(request: Request, control: str):
        propuesta_o_400(control, decidible=False)
        db.quitar_propuesta(bd(), espacio()["id"], control)
        return volver_a_la_declaracion(request, control)

    @app.post("/declaracion/propuesta/{control}/contestar")
    async def contestar_propuesta(request: Request, control: str, texto: str = Form("")):
        """Se contesta la pregunta de un FALTA SABER y Claude vuelve a proponer solo ese control."""
        p = propuesta_o_400(control, decidible=False)
        texto = texto.strip()
        if not texto:
            return volver_a_la_declaracion(request, control, error_ia="Escribe la respuesta antes de enviarla.",
                                           error_control=control)
        e = espacio()["id"]
        aclaraciones = {control: (p["porque"], texto)}
        try:
            respuesta = await ia.tarea("declaracion", propuestas.INSTRUCCIONES,
                                       propuestas.mensaje(perfil(), db.sistemas(bd(), e), [control], aclaraciones),
                                       propuestas.ESFUERZO)
        except ia.ClaudeNoDisponible as error:
            return volver_a_la_declaracion(request, control, error_ia=str(error), error_control=control)
        nueva = propuestas.leer(respuesta, [control])
        if not nueva:
            return volver_a_la_declaracion(request, control, error_control=control,
                                           error_ia="Claude ha respondido, pero no con la forma esperada. Vuelve a probar.")
        guardar_propuestas(nueva, aclaraciones)
        return volver_a_la_declaracion(request, control)

    @app.get("/declaracion")
    def declaracion(request: Request):
        return pagina_controles(request)

    @app.post("/declaracion/{control}")
    async def decidir(request: Request, control: str, aplica: str = Form(""), porque: str = Form("")):
        req = requisito_o_404(control)
        if req.obligatorio:
            raise HTTPException(404)
        antes = db.decisiones(bd(), espacio()["id"]).get(control)
        form = await request.form()
        if form.get("quitar") == "1" and aplica not in ("si", "no"):
            # Se ha vuelto a pulsar la opción marcada: se desmarca y el control vuelve a «sin decidir». El porqué
            # escrito se queda en el cuadro, por si se vuelve a decidir
            if db.quitar_decision(bd(), espacio()["id"], control, hoy(), quien()):
                apunta("sin_decidir", control, detalle=f"Antes: {'aplica' if antes.aplica else 'no aplica'}")
            carpetas_no_aplica()
            if request.headers.get("HX-Request"):
                return pagina_controles(request, guardado_control=control, control_error=control,
                                        borrador={"aplica": "", "porque": porque})
            return RedirectResponse(f"/declaracion#control-{control}", status_code=303)
        cambia = antes is not None and aplica in ("si", "no") and antes.aplica != (aplica == "si")
        falta = []
        if aplica not in ("si", "no"):
            falta.append("elegir si aplica o no aplica")
        if not porque.strip():
            falta.append("el porqué (la norma lo pide en los dos casos, 6.1.3.c)")
        elif cambia and porque.strip() == antes.porque:
            falta.append("el porqué nuevo (el que hay explicaba la decisión de antes)")
        auto = request.headers.get("HX-Request") and form.get("auto") == "1"
        # Desde dónde se guarda solo: al elegir la opción o al dejar de escribir el porqué. Se está a
        # medio camino: lo que falta se dice en gris y lo guardado no vuelve a pintar el control, para no
        # sacar a nadie del cuadro mientras escribe
        a_medias = auto and form.get("origen") in ("aplica", "porque")
        escribiendo = auto and form.get("origen") == "porque"
        if falta and auto:
            # Guardado solo: aún no está completo; no se toca lo escrito, solo se dice qué falta
            if a_medias:
                r = pagina_controles(request, aviso_control=control, aviso_tipo="pista",
                                     aviso="Escribe el porqué" + (" nuevo" if cambia else "") + ": se guarda solo.")
            else:
                r = pagina_controles(request, aviso_control=control,
                                     aviso="Para guardarlo falta " + "; ".join(falta) + ".")
            r.headers["HX-Reswap"] = "none"
            return r
        if falta:
            # Se vuelve a pintar con lo que se había escrito, para no perderlo
            return pagina_controles(request, control_error=control,
                                    error="Falta " + "; ".join(falta) + ".",
                                    borrador={"aplica": aplica, "porque": porque})
        porque = porque.strip()
        # El porqué nuevo es también el motivo del cambio
        db.decidir(bd(), espacio()["id"], control, aplica == "si", porque, "", hoy(), quien())
        if antes is None or antes.aplica != (aplica == "si") or antes.porque != porque:
            accion = "aplica" if aplica == "si" else "no_aplica"
            ultima = next(iter(db.actividad(bd(), espacio()["id"], control)), None)
            ahora = datetime.combine(hoy(), datetime.now().time())
            if (antes is not None and antes.aplica == (aplica == "si") and ultima is not None
                    and ultima["accion"] == accion and ultima["detalle"] == antes.porque
                    and ahora - datetime.fromisoformat(ultima["cuando"]) < SIGUE_ESCRIBIENDO):
                # Solo cambia el porqué y hace poco que se guardó: se sigue escribiendo el mismo. Se corrige
                # la línea de «Actividad» y, si venía de un cambio, el motivo en «Cambios»
                db.corregir_actividad(bd(), ultima["id"], ahora, porque)
                db.corregir_motivo(bd(), espacio()["id"], control, antes.porque, porque, hoy())
            else:
                apunta(accion, control, detalle=porque)
        db.quitar_propuesta(bd(), espacio()["id"], control)  # decidido a mano: su propuesta queda resuelta
        # La decisión se guarda aunque la carpeta esté ocupada: se vuelve a intentar al siguiente cambio
        # o al arrancar
        ocupada = control in carpetas_no_aplica()
        aviso_carpeta = (f"Guardado, pero la carpeta no se ha podido renombrar: cierra los archivos de {control}."
                         if ocupada else "")
        if escribiendo:
            # Sin volver a pintar el control: solo el aviso y el resumen de arriba
            r = pagina_controles(request, aviso_control=control, aviso_tipo="falta" if ocupada else "hecho",
                                 aviso=aviso_carpeta or f"Guardado a las {datetime.now():%H:%M}")
            r.headers["HX-Reswap"] = "none"
            return r
        if auto or ocupada:
            return pagina_controles(request, guardado_control=control, aviso_carpeta=aviso_carpeta)
        return RedirectResponse(f"/declaracion#control-{control}", status_code=303)

    @app.get("/declaracion/cambios")
    def declaracion_cambios(request: Request):
        return pagina_declaracion(request, "cambios", cambios=db.cambios(bd(), espacio()["id"]))

    @app.get("/declaracion/documento")
    def declaracion_documento(request: Request, guardado: str = ""):
        return pagina_declaracion(request, "documento", filas=documento.filas(db.decisiones(bd(), espacio()["id"])),
                                  guardado=guardado, hoy=hoy(), espacio=espacio())

    def generar(formato: str) -> tuple[bytes, str]:
        if formato not in documento.FORMATOS:
            raise HTTPException(400, "Formato no válido")
        fs = documento.filas(db.decisiones(bd(), espacio()["id"]))
        return documento.generar(formato, fs, espacio()["nombre"], hoy()), documento.nombre_archivo(formato, hoy())

    @app.get("/declaracion/documento/descargar")
    def descargar(formato: str):
        datos, nombre = generar(formato)
        tipo = ("application/vnd.openxmlformats-officedocument.wordprocessingml.document" if formato == "word"
                else "application/pdf")
        return Response(datos, media_type=tipo,
                        headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(nombre)})

    @app.post("/declaracion/documento/guardar")
    def guardar_documento(formato: str = Form(...)):
        """Se guarda en las pruebas de la 6.1.3.c; la versión anterior pasa al historial."""
        datos, nombre = generar(formato)
        punto = "6.1.3.c"
        for a in carpetas().archivos(punto):
            if a.nombre.startswith(documento.NOMBRE):
                carpetas().quitar(punto, a.nombre, hoy())
        guardado = carpetas().guardar(punto, nombre, io.BytesIO(datos))
        apunta("documento", "6.1.3", punto, detalle=guardado)
        return RedirectResponse(f"/declaracion/documento?guardado={quote(guardado)}", status_code=303)

    # --- Inventario de IA ---

    def pagina_inventario(request: Request, **extra):
        todos = db.sistemas(bd(), espacio()["id"])
        return plantillas.TemplateResponse(request, "inventario.html", {
            "seccion": "inventario",
            "activos": [x for x in todos if x.retirado is None],
            "retirados": [x for x in todos if x.retirado is not None],
            "total_campos": len(db.CAMPOS),
            **extra,
        })

    def sistema_o_404(sistema_id: int) -> db.Sistema:
        x = db.sistema(bd(), espacio()["id"], sistema_id)
        if x is None:
            raise HTTPException(404)
        return x

    def pagina_sistema(request: Request, x: db.Sistema, **extra):
        return plantillas.TemplateResponse(request, "sistema.html", {
            "seccion": "inventario",
            "x": x,
            "campos": CAMPOS_FICHA,
            **extra,
        })

    @app.get("/inventario")
    def inventario(request: Request, guardado: str = "", retirado: str = "", activado: str = "", error: str = ""):
        mensaje = (f"Ficha de «{guardado}» guardada." if guardado else
                   f"«{retirado}» retirado: ya no cuenta. Su ficha se guarda y sus archivos han pasado a las versiones anteriores de cada requisito." if retirado else
                   f"«{activado}» vuelve a estar activo." if activado else "")
        return pagina_inventario(request, mensaje=mensaje, error=error)

    def volver_al_inventario(**mensaje: str) -> RedirectResponse:
        # Tras guardar, retirar o activar se vuelve a la lista, con un mensaje de qué ha pasado
        (clave, valor), = mensaje.items()
        return RedirectResponse(f"/inventario?{clave}={quote(valor)}", status_code=303)

    # Sistemas dados de alta o vueltos a activar con la pregunta de reabrir sin contestar:
    # «id:como» separados por comas, en los ajustes del espacio
    def altas_pendientes() -> dict[int, str]:
        return pendiente.altas_pendientes(bd(), espacio()["id"])

    def guardar_altas(pendientes: dict[int, str]) -> None:
        db.guardar_ajuste(bd(), espacio()["id"], "altas_pendientes",
                          ",".join(f"{i}:{como}" for i, como in pendientes.items()))

    def alta_contestada(sistema_id: int) -> None:
        pendientes = altas_pendientes()
        pendientes.pop(sistema_id, None)
        guardar_altas(pendientes)

    def preguntas_alta(est) -> list[tuple[db.Sistema, str]]:
        return pendiente.preguntas_alta(bd(), espacio()["id"], est)

    def a_la_ficha_nueva(sistema_id: int, como: str) -> RedirectResponse:
        """Tras dar de alta o volver a activar un sistema: si hay algo de toda la empresa que reabrir, la
        pregunta queda pendiente y se va a su ficha, que la hace; si no, a la ficha (alta) o a la lista."""
        if any(lista for _, lista in afectados(guia_portal.ALTA, estado())):
            guardar_altas(altas_pendientes() | {sistema_id: como})
            return RedirectResponse(f"/inventario/{sistema_id}", status_code=303)
        if como == "nuevo":
            return RedirectResponse(f"/inventario/{sistema_id}", status_code=303)
        return volver_al_inventario(activado=db.sistema(bd(), espacio()["id"], sistema_id).nombre)

    @app.post("/inventario")
    def añadir_sistema(request: Request, nombre: str = Form(""), tipo: str = Form("")):
        nombre = nombre.strip()
        error = ("Falta el nombre." if not nombre else
                 "Elige qué tipo de IA es: si la ofrecéis a clientes o la usa el equipo." if tipo not in db.TIPOS else "")
        if not error:
            try:
                nuevo = db.crear_sistema(bd(), espacio()["id"], nombre, tipo, hoy())
                carpetas().crear_sistema(db.sistema(bd(), espacio()["id"], nuevo))
                apunta("sistema_alta", sistema=db.sistema(bd(), espacio()["id"], nuevo))
                return a_la_ficha_nueva(nuevo, "nuevo")
            except db.NombreRepetido:
                error = f"Ya hay un sistema que se llama «{nombre}»."
        return pagina_inventario(request, error=error, borrador={"nombre": nombre, "tipo": tipo})

    @app.get("/inventario/{sistema_id}")
    def ficha_sistema(request: Request, sistema_id: int, reabiertos: str = ""):
        x = sistema_o_404(sistema_id)
        est = estado()
        como = next((c for y, c in preguntas_alta(est) if y.id == x.id), None)
        return pagina_sistema(request, x, est=est, reabiertos=reabiertos, como=como,
                              alta=afectados(guia_portal.ALTA, est) if como else [])

    @app.post("/inventario/{sistema_id}/no-reabrir")
    def no_reabrir_alta(request: Request, sistema_id: int):
        """«No hace falta»: se contesta la pregunta sin reabrir nada."""
        sistema_o_404(sistema_id)
        alta_contestada(sistema_id)
        return RedirectResponse(f"/inventario/{sistema_id}?reabiertos=nada", status_code=303)

    @app.post("/inventario/{sistema_id}/reabrir")
    async def reabrir_alta(request: Request, sistema_id: int):
        """Tras dar de alta un sistema: reabre lo elegido de toda la empresa."""
        x = sistema_o_404(sistema_id)
        form = await request.form()
        hechos = reabrir_elegidos(guia_portal.ALTA, set(form.getlist("requisitos")), f"por el sistema «{x.nombre}»")
        alta_contestada(sistema_id)
        return RedirectResponse(f"/inventario/{sistema_id}?reabiertos={quote(', '.join(hechos) or 'nada')}",
                                status_code=303)

    @app.post("/inventario/{sistema_id}")
    async def guardar_sistema(request: Request, sistema_id: int):
        x = sistema_o_404(sistema_id)
        form = await request.form()
        nombre = str(form.get("nombre", "")).strip()
        tipo = str(form.get("tipo", ""))
        campos = {c: str(form.get(c, "")).strip() for c in db.CAMPOS}
        error = ("Falta el nombre." if not nombre else
                 "Elige qué tipo de IA es: si la ofrecéis a clientes o la usa el equipo." if tipo not in db.TIPOS else "")
        if not error and nombre.lower() != x.nombre.lower() and any(
                y.nombre.lower() == nombre.lower() for y in db.sistemas(bd(), espacio()["id"])):
            error = f"Ya hay otro sistema que se llama «{nombre}»."
        if not error:
            try:
                carpetas().renombrar(x.nombre, nombre)  # sus carpetas, con el nombre nuevo
            except pruebas.CarpetaOcupada:
                error = CARPETA_OCUPADA
        auto = request.headers.get("HX-Request") and form.get("auto") == "1"
        cambia = (nombre, tipo, campos) != (x.nombre, x.tipo, {c: x.campo(c) for c in db.CAMPOS})
        if not error and cambia:
            db.guardar_sistema(bd(), espacio()["id"], sistema_id, nombre, tipo, campos, hoy())
            apunta("sistema_ficha", sistema=db.sistema(bd(), espacio()["id"], sistema_id),
                   detalle=f"antes se llamaba «{x.nombre}»" if nombre != x.nombre else "")
            if x.retirado is None:
                carpetas().crear_sistema(db.sistema(bd(), espacio()["id"], sistema_id))  # por si cambia el tipo
        if auto:
            # Guardado solo: se actualizan el aviso, la cabecera y los estados, no lo que se escribe
            y = db.sistema(bd(), espacio()["id"], sistema_id)
            if error:
                y = db.Sistema(x.id, nombre, tipo, **campos, actualizado=x.actualizado, retirado=x.retirado)
            return pagina_sistema(request, y, auto=True, aviso=error or f"Guardado a las {datetime.now():%H:%M}",
                                  aviso_error=bool(error))
        if not error:
            return volver_al_inventario(guardado=nombre)
        # Se vuelve a pintar con lo escrito, para no perderlo
        borrador = db.Sistema(x.id, nombre, tipo, **campos, actualizado=x.actualizado, retirado=x.retirado)
        return pagina_sistema(request, borrador, error=error)

    @app.post("/inventario/{sistema_id}/retirar")
    def retirar_sistema(sistema_id: int):
        x = sistema_o_404(sistema_id)
        try:
            carpetas().retirar(x, hoy())
        except pruebas.CarpetaOcupada:
            return volver_al_inventario(error=CARPETA_OCUPADA)
        db.retirar_sistema(bd(), espacio()["id"], sistema_id, hoy())
        apunta("sistema_retirado", sistema=x)
        return volver_al_inventario(retirado=x.nombre)

    @app.post("/inventario/{sistema_id}/activar")
    def activar_sistema(sistema_id: int):
        x = sistema_o_404(sistema_id)
        try:
            carpetas().activar(x)
        except pruebas.CarpetaOcupada:
            return volver_al_inventario(error=CARPETA_OCUPADA)
        db.retirar_sistema(bd(), espacio()["id"], sistema_id, None)
        apunta("sistema_activado", sistema=x)
        carpetas().crear_sistema(db.sistema(bd(), espacio()["id"], sistema_id))
        return a_la_ficha_nueva(sistema_id, "activado")

    # --- Ha pasado algo ---

    def preguntar_cada() -> int:
        return pendiente.preguntar_cada(bd(), espacio()["id"])

    def proxima_pregunta(est) -> date | None:
        return pendiente.proxima_pregunta(bd(), espacio()["id"], est)

    def contestada() -> None:
        db.guardar_ajuste(bd(), espacio()["id"], "eventos_contestado", hoy().isoformat())

    def situacion_o_404(clave: str) -> guia_portal.Situacion:
        sit = guia_portal.situacion(clave)
        if sit is None:
            raise HTTPException(404)
        return sit

    afectados = pendiente.afectados

    def reabrir_elegidos(sit: guia_portal.Situacion, elegidos: set[str], motivo: str) -> list[str]:
        """Reabre los requisitos elegidos de la situación (solo los suyos y con algo que reabrir)."""
        hechos = []
        for r, lista in afectados(sit, estado()):
            if r.codigo in elegidos and lista:
                reabrir_requisito(r, lista, motivo)
                hechos.append(r.codigo)
        return hechos

    @app.get("/eventos")
    def eventos(request: Request, reabiertos: str = "", situacion: str = ""):
        est = estado()
        return plantillas.TemplateResponse(request, "eventos.html", {
            "seccion": "inicio",  # se llega desde Inicio
            "situaciones": guia_portal.situaciones(),
            "proxima": proxima_pregunta(est),
            "cada": preguntar_cada(),
            "reabiertos": reabiertos,
            "hecha": guia_portal.situacion(situacion),
        })

    @app.get("/eventos/{clave}")
    def evento(request: Request, clave: str):
        sit = situacion_o_404(clave)
        est = estado()
        return plantillas.TemplateResponse(request, "evento.html", {
            "seccion": "inicio",  # se llega desde Inicio
            "sit": sit,
            "est": est,
            "afectados": afectados(sit, est),
        })

    @app.post("/eventos/{clave}")
    async def reabrir_evento(request: Request, clave: str):
        """Reabre los requisitos elegidos y cuenta como respuesta a «¿ha pasado algo?»."""
        sit = situacion_o_404(clave)
        form = await request.form()
        hechos = reabrir_elegidos(sit, set(form.getlist("requisitos")), f"ha pasado algo: {sit.titulo.lower()}")
        # La situación queda apuntada siempre, aunque no se reabra nada (sirve para la revisión anual, 9.3)
        apunta("evento", detalle=f"{sit.titulo} · " + (f"reabiertos {', '.join(hechos)}" if hechos else "nada que reabrir"))
        contestada()
        return RedirectResponse(f"/eventos?situacion={clave}&reabiertos={quote(', '.join(hechos))}", status_code=303)

    # --- Actividad ---

    @app.get("/actividad")
    def actividad(request: Request, requisito: str = "", persona: str = ""):
        todas = db.actividad(bd(), espacio()["id"])
        con_actividad = sorted({f["requisito"] for f in todas if f["requisito"]},
                               key=lambda c: list(guia_portal.REQUISITOS).index(c))
        return plantillas.TemplateResponse(request, "actividad.html", {
            "seccion": "actividad",
            "filas": [f for f in todas if (not requisito or f["requisito"] == requisito)
                      and (not persona or f["quien"] == persona)],
            "requisitos": [guia_portal.requisito(c) for c in con_actividad],
            "elegido": requisito,
            # Quién ha hecho algo en esta empresa: también quien ya no está
            "personas": sorted({f["quien"] for f in todas if f["quien"]}, key=str.casefold),
            "persona": persona,
            "acciones": ACCIONES,
        })

    # --- Avisos ---

    def avisa(clave: str) -> bool:
        return pendiente.avisa(bd(), espacio()["id"], clave)

    def pendientes(est) -> dict:
        return pendiente.pendientes(bd(), espacio()["id"], est)

    @app.post("/avisos/nada")
    def no_ha_pasado_nada(request: Request):
        contestada()
        return RedirectResponse("/", status_code=303)

    @app.post("/avisos/recordatorio/{codigo}/hecho")
    def recordatorio_hecho(request: Request, codigo: str):
        req = requisito_o_404(codigo)
        r = estado().recordatorio(req)
        if r is None:
            raise HTTPException(400, "Este requisito no tiene recordatorio")
        db.recordatorio_hecho(bd(), espacio()["id"], codigo, r.meses, hoy())
        return RedirectResponse("/", status_code=303)

    # --- Ajustes ---

    def volver_a_ajustes(ancla: str = "") -> RedirectResponse:
        return RedirectResponse("/ajustes" + (f"#{ancla}" if ancla else ""), status_code=303)

    @app.get("/ajustes")
    def ajustes(request: Request, correo_ok: str = "", correo_error: str = ""):
        est = estado()
        e = espacio()["id"]
        marcados = [(r, p, None) for r in guia_portal.requisitos() for p in r.puntos if est.marcado(p)]
        marcados += [(r, p, x) for r in guia_portal.requisitos() for p in r.puntos
                     if est.clase(p) == seguimiento.SISTEMA for x in est.sistemas_de(p) if est.marcado_en(p, x)]
        return plantillas.TemplateResponse(request, "ajustes.html", {
            "seccion": "ajustes",
            "est": est,
            "requisitos": guia_portal.requisitos(),
            "plazos": PLAZOS,
            "recordar": RECORDAR,
            "avisos": {clave: (texto, avisa(clave)) for clave, texto in AVISOS.items()},
            "marcados": marcados,
            "preguntar": PREGUNTAR,
            "preguntar_cada": preguntar_cada(),
            "proxima_pregunta": proxima_pregunta(est),
            # Avisos por correo: apagados por defecto
            "correo": {
                "activado": db.ajuste(bd(), e, correo.ACTIVADOS, "0") == "1",
                "para": db.ajuste(bd(), e, correo.PARA, ""),
                # Los usuarios de la empresa, cada uno con su casilla
                "usuarios": [(u, u.correo.lower() not in {c.lower() for c in correo.destinatarios(
                    db.ajuste(bd(), e, correo.QUITADOS, ""))}) for u in cuentas.usuarios_de(datos, ACTUAL.get().empresa.slug)],
                "cuenta": db.ajuste(bd(), e, correo.CUENTA, ""),
                "cuentas": envio.cuentas(),
                "programada": envio.programada(),
                "mes": db.ajuste(bd(), e, correo.MANDADO_MES, ""),
                "semana": db.ajuste(bd(), e, correo.MANDADO_SEMANA, ""),
                "ok": correo_ok, "error": correo_error,
            },
            "cambiados": sum(est.vence_por_fecha(r) != seguimiento.vence_por_defecto(r) for r in guia_portal.requisitos())
                         + (est.plazo_general != seguimiento.PLAZO_GENERAL)
                         + sum(r.codigo in est.recordatorios for r in guia_portal.requisitos()
                               if (est.recordatorio(r).meses if est.recordatorio(r) else None)
                               != seguimiento.RECORDAR_POR_DEFECTO.get(r.codigo))
                         + (preguntar_cada() != seguimiento.PREGUNTAR_POR_DEFECTO),
        })

    @app.post("/ajustes/antelacion")
    def guardar_antelacion(dias: int = Form(...)):
        if not 0 <= dias <= 365:
            raise HTTPException(400, "La antelación va de 0 a 365 días")
        db.guardar_ajuste(bd(), espacio()["id"], "antelacion", str(dias))
        return volver_a_ajustes("antelacion")

    @app.post("/ajustes/plazo-general")
    def guardar_plazo_general(meses: int = Form(...)):
        if meses not in PLAZOS:
            raise HTTPException(400, "Plazo no válido")
        db.guardar_ajuste(bd(), espacio()["id"], "plazo_general", str(meses))
        return volver_a_ajustes("plazo-general")

    @app.post("/ajustes/plazo/{codigo}")
    def guardar_plazo(codigo: str, vence: str = Form(...)):
        """«si»: vence con la revisión general; «no»: no vence por fecha."""
        requisito_o_404(codigo)
        if vence not in ("si", "no"):
            raise HTTPException(400, "Plazo no válido")
        db.guardar_plazo(bd(), espacio()["id"], codigo, seguimiento.PLAZO_GENERAL if vence == "si" else None)
        return volver_a_ajustes(f"plazo-{codigo}")

    @app.post("/ajustes/recordatorio/{codigo}")
    def guardar_recordatorio(codigo: str, meses: str = Form(...)):
        requisito_o_404(codigo)
        if meses == "no":
            valor = None
        elif meses.isdigit() and int(meses) in RECORDAR:
            valor = int(meses)
        else:
            raise HTTPException(400, "Recordatorio no válido")
        db.guardar_recordatorio(bd(), espacio()["id"], codigo, valor, hoy())
        return volver_a_ajustes(f"plazo-{codigo}")

    @app.post("/ajustes/preguntar")
    def guardar_preguntar(meses: int = Form(...)):
        """Cada cuánto pregunta «¿ha pasado algo?»; 0, nunca."""
        if meses not in PREGUNTAR:
            raise HTTPException(400, "Valor no válido")
        db.guardar_ajuste(bd(), espacio()["id"], "preguntar_cada", str(meses))
        return volver_a_ajustes("preguntar")

    # --- Avisos por correo ---

    def correos_usuarios() -> list[str]:
        return [u.correo for u in cuentas.usuarios_de(datos, ACTUAL.get().empresa.slug)]

    @app.post("/ajustes/correo")
    def guardar_correo(activado: str = Form(""), para: str = Form(""), cuenta: str = Form(""),
                       recibe: list[str] = Form([])):
        e = espacio()["id"]
        # Los usuarios sin la casilla quedan quitados; los demás, y los nuevos, reciben los avisos
        marcados = {c.lower() for c in recibe}
        db.guardar_ajuste(bd(), e, correo.QUITADOS,
                          ", ".join(c for c in correos_usuarios() if c.lower() not in marcados))
        estaba = db.ajuste(bd(), e, correo.ACTIVADOS, "0") == "1"
        if activado and not estaba:
            # Solo cuentan los días 1 y los lunes desde hoy: al activarlos no llega uno atrasado
            db.guardar_ajuste(bd(), e, correo.DESDE, hoy().isoformat())
        db.guardar_ajuste(bd(), e, correo.ACTIVADOS, "1" if activado else "0")
        db.guardar_ajuste(bd(), e, correo.PARA, ", ".join(correo.destinatarios(para)))
        db.guardar_ajuste(bd(), e, correo.CUENTA, cuenta.strip())
        return volver_a_ajustes("correo")

    @app.post("/ajustes/correo/prueba")
    def probar_correo():
        """Manda ya un aviso con el resumen del mes y lo de esta semana. No cuenta como mandado."""
        toca = correo.Toca(mes=hoy().replace(day=1), semana=correo.lunes_de(hoy()))
        try:
            texto = correo.mandar(bd(), espacio(), hoy(), toca, envio, prueba=True, usuarios=correos_usuarios(),
                                  quien=quien())
        except correo.AvisoFallido as e:
            return RedirectResponse(f"/ajustes?correo_error={quote(str(e))}#correo", status_code=303)
        return RedirectResponse(f"/ajustes?correo_ok={quote(texto)}#correo", status_code=303)

    @app.post("/ajustes/avisos")
    async def guardar_avisos(request: Request):
        form = await request.form()
        for clave in AVISOS:
            db.guardar_ajuste(bd(), espacio()["id"], clave, "1" if form.get(clave) else "0")
        return volver_a_ajustes("que-avisa")

    @app.post("/ajustes/plazos/por-defecto")
    def plazos_por_defecto():
        db.borrar_plazos(bd(), espacio()["id"])
        db.guardar_ajuste(bd(), espacio()["id"], "plazo_general", str(seguimiento.PLAZO_GENERAL))
        db.borrar_recordatorios(bd(), espacio()["id"])  # también vuelven a los recomendados
        db.guardar_ajuste(bd(), espacio()["id"], "preguntar_cada", str(seguimiento.PREGUNTAR_POR_DEFECTO))
        return volver_a_ajustes("plazos")

    return app


def _app() -> FastAPI:
    """arrancar.bat pide el portal instalado; los otros arranques, el de siempre."""
    return crear_app(instalador=instalar.Instalador()) if config.INSTALADO else crear_app()


app = _app()
