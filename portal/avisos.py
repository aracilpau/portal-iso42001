# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Avisos por correo y notificación de Windows.

El día 1 de cada mes, un resumen de lo pendiente (lo mismo que «Lo siguiente» de Inicio); cada lunes, lo vencido y
lo que vence esa semana. Lo lanza una tarea de Windows (scripts/avisos.py), aunque el portal esté cerrado: lee la base de
datos, decide qué toca y lo manda desde el Outlook clásico de este ordenador. Si el día 1 cae en lunes, un solo correo.

Apagados por defecto: hasta que se activan en Ajustes, nada toca el correo. Cada empresa tiene los suyos, y su nombre
va en el asunto. El correo
lleva solo códigos, títulos, puntos y fechas (regla 4 de datos): ni archivos, ni su contenido, ni nombres de sistemas.
"""
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Callable
from xml.sax.saxutils import escape as xml

from portal import cuentas, db, pendiente, seguimiento

TAREA = "Portal ISO 42001 - avisos"
PROTOCOLO = "portal-iso"     # el enlace propio de la notificación: portal-iso://inicio
HORA = "09:00"
ESPERA_OUTLOOK = 60          # segundos como mucho esperando a que el correo salga de la bandeja de salida

# Ajustes del espacio
ACTIVADOS, PARA, CUENTA, DESDE = "correo_activado", "correo_para", "correo_cuenta", "correo_desde"
# Los usuarios de la empresa reciben los avisos salvo que se quiten: se guardan los que se han quitado, así
# uno nuevo los recibe sin hacer nada
QUITADOS = "correo_quitados"
MANDADO_MES, MANDADO_SEMANA = "correo_mes", "correo_semana"


class AvisoFallido(Exception):
    """No se ha podido mandar el correo. El texto es para la persona."""


# --- Qué toca mandar ---

def lunes_de(d: date) -> date:
    return d - timedelta(days=d.weekday())


@dataclass
class Toca:
    mes: date | None = None      # el día 1 del mes que toca resumir
    semana: date | None = None   # el lunes de la semana que toca

    def __bool__(self) -> bool:
        return bool(self.mes or self.semana)


def que_toca(hoy: date, desde: date, mes_mandado: str, semana_mandada: str) -> Toca:
    """El último día 1 y el último lunes, si aún no se han mandado y son del día en que se activaron los avisos o
    después (al activarlos no llega uno atrasado). Si un lunes el ordenador no se enciende, el martes toca ese lunes."""
    dia1, lunes = hoy.replace(day=1), lunes_de(hoy)
    return Toca(mes=dia1 if dia1 >= desde and dia1.isoformat() != mes_mandado else None,
                semana=lunes if lunes >= desde and lunes.isoformat() != semana_mandada else None)


# --- Qué dice ---

@dataclass
class Mensaje:
    asunto: str
    html: str
    corto: str                   # para la notificación


def _fecha(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else "sin fecha"


def _linea(a: seguimiento.Aviso, verbo: str) -> str:
    # Sin el nombre del sistema (regla 4): solo que es de un sistema
    sistema = " (de un sistema del inventario)" if a.sistema else ""
    return f"{a.requisito.codigo} {a.requisito.titulo} · punto {a.punto.codigo}{sistema} · {verbo} el {_fecha(a.vence)}"


def esta_semana(est: seguimiento.Seguimiento, lunes: date) -> list[seguimiento.Aviso]:
    """Lo que vence de lunes a domingo y aún no ha vencido (lo vencido va aparte)."""
    domingo = lunes + timedelta(days=6)
    res = [a for estado in (seguimiento.VENCE_PRONTO, seguimiento.CUMPLIDO) for a in est.avisos(estado)
           if a.vence and lunes <= a.vence <= domingo]
    return sorted(res, key=lambda a: a.vence)


def mensaje(est: seguimiento.Seguimiento, pend: dict, toca: Toca, prueba: bool = False, empresa: str = "") -> Mensaje:
    bloques, cuentas = [], []

    def bloque(titulo: str, lineas: list[str]) -> None:
        bloques.append(f"<h3>{escape(titulo)}</h3><ul>" + "".join(f"<li>{escape(l)}</li>" for l in lineas) + "</ul>")

    if toca.semana:
        vencidos = est.avisos(seguimiento.VENCIDO)
        semana = esta_semana(est, toca.semana)
        domingo = toca.semana + timedelta(days=6)
        titulo = f"Esta semana (del {toca.semana.strftime('%d/%m')} al {domingo.strftime('%d/%m')})"
        if vencidos:
            bloque("Ya vencido", [_linea(a, "venció") for a in vencidos])
        if semana:
            bloque(titulo, [_linea(a, "vence") for a in semana])
        if not vencidos and not semana:
            bloques.append(f"<h3>{escape(titulo)}</h3><p>Esta semana no vence nada.</p>")
        cuentas.append(f"{len(semana)} vence{'n' if len(semana) != 1 else ''} esta semana" if semana
                       else "esta semana no vence nada")
        if vencidos:
            cuentas.append(f"{len(vencidos)} vencido{'s' if len(vencidos) != 1 else ''}")

    if toca.mes:
        lineas = ([_linea(a, "venció") for a in pend["vencidos"]] + [_linea(a, "vence") for a in pend["pronto"]]
                  + [f"Recordatorio: {r.codigo} {r.titulo} (desde el {_fecha(f)})" for r, f in pend["recordatorios"]]
                  + (["Toca preguntarse si ha pasado algo que reabra requisitos («Ha pasado algo», en Inicio)."]
                     if pend["pregunta"] else [])
                  + ([f"Hay {len(pend['altas'])} sistema(s) nuevo(s) o vuelto(s) a activar con una pregunta pendiente."]
                     if pend["altas"] else []))
        if lineas:
            bloque("Resumen del mes", lineas)
            cuentas.insert(0, f"resumen del mes: {len(lineas)} pendiente{'s' if len(lineas) != 1 else ''}")
        else:
            bloques.append("<h3>Resumen del mes</h3><p>Todo al día.</p>")
            cuentas.insert(0, "resumen del mes: todo al día")

    que = " y ".join(x for x in ("resumen del mes" if toca.mes else "", "esta semana" if toca.semana else "") if x)
    asunto = ("[Prueba] " if prueba else "") + f"[Portal ISO 42001{f' · {empresa}' if empresa else ''}] Avisos: {que}"
    html = ("<div style=\"font-family:Segoe UI,Arial,sans-serif;font-size:14px\">"
            + (f"<p><em>Aviso de prueba, mandado desde Ajustes.</em></p>" if prueba else "")
            + "".join(bloques)
            + "<p style=\"color:#666\">Ábrelo en el portal para ver el detalle. Este correo lo manda el portal ISO 42001"
              " desde Outlook; se activa y se desactiva en Ajustes.</p></div>")
    corto = cuentas[0][0].upper() + "; ".join(cuentas)[1:] + "."
    return Mensaje(asunto, html, corto)


# --- Cómo se manda (Outlook clásico y notificación de Windows) ---

def _outlook():
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()  # cada hilo que usa Outlook lo necesita (el portal atiende en varios)
    return win32com.client.Dispatch("Outlook.Application")


def mandar_outlook(para: list[str], asunto: str, html: str, cuenta: str = "") -> None:
    """Lo manda el Outlook clásico de este ordenador, con la sesión abierta: sin contraseñas. Espera a que salga de la
    bandeja de salida, porque si Outlook se ha abierto solo y se cierra antes, el correo se queda atascado."""
    try:
        ol = _outlook()
        ns = ol.GetNamespace("MAPI")
        correo = ol.CreateItem(0)
        correo.To = "; ".join(para)
        correo.Subject = asunto
        correo.HTMLBody = html
        salida = ns.GetDefaultFolder(4)  # bandeja de salida
        if cuenta:
            elegida = next((a for a in ns.Accounts if a.SmtpAddress.lower() == cuenta.lower()), None)
            if elegida is None:
                raise AvisoFallido(f"La cuenta {cuenta} no está en el Outlook clásico de este ordenador.")
            # SendUsingAccount (64209): con pywin32 no se puede asignar como una propiedad normal
            correo._oleobj_.Invoke(64209, 0, 8, 0, elegida)
            salida = elegida.DeliveryStore.GetDefaultFolder(4)
        correo.Send()
    except AvisoFallido:
        raise
    except Exception as e:  # Outlook no instalado, solo el «nuevo Outlook», sin perfil…
        raise AvisoFallido("No se ha podido mandar con Outlook. Hace falta el Outlook clásico con la cuenta puesta "
                           f"({e}).") from e
    limite = time.monotonic() + ESPERA_OUTLOOK
    try:
        while salida.Items.Count and time.monotonic() < limite:
            ns.SendAndReceive(False)
            time.sleep(2)
    except Exception:
        pass  # si no se puede mirar la bandeja, el correo ya está entregado a Outlook


def cuentas_outlook() -> list[str]:
    """Las cuentas del Outlook clásico, solo si ya está abierto (para no abrirlo al entrar en Ajustes)."""
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        ol = win32com.client.GetActiveObject("Outlook.Application")
        return [a.SmtpAddress for a in ol.GetNamespace("MAPI").Accounts]
    except Exception:
        return []


def notificar(titulo: str, texto: str) -> None:
    """El recuadro de Windows. Al pulsarlo, el enlace propio enciende el portal si hace falta y abre Inicio."""
    try:
        from winotify import Notification
        Notification(app_id="Portal ISO 42001", title=titulo, msg=texto, launch=f"{PROTOCOLO}://inicio").show()
    except Exception:
        pass  # sin notificación, el correo sigue valiendo


def tarea_programada() -> bool:
    try:
        return subprocess.run(["schtasks", "/Query", "/TN", TAREA], capture_output=True).returncode == 0
    except OSError:
        return False


@dataclass
class Envio:
    """Cómo se manda. Las pruebas ponen uno de mentira para no mandar nada de verdad."""
    correo: Callable[[list[str], str, str, str], None] = mandar_outlook
    notificacion: Callable[[str, str], None] = notificar
    cuentas: Callable[[], list[str]] = cuentas_outlook
    programada: Callable[[], bool] = tarea_programada


# --- Lo que lanza Windows ---

def destinatarios(texto: str) -> list[str]:
    return [x.strip() for x in texto.replace(";", ",").split(",") if x.strip()]


def para(bd: Path, e: int, usuarios: list[str]) -> list[str]:
    """A quién va el aviso: los correos de los usuarios que no se han quitado y, además, los que se escribieron a mano
    (gente que no usa el portal). Sin repetir."""
    quitados = {c.lower() for c in destinatarios(db.ajuste(bd, e, QUITADOS, ""))}
    lista = [c for c in usuarios if c.lower() not in quitados]
    for c in destinatarios(db.ajuste(bd, e, PARA, "")):
        if c.lower() not in {x.lower() for x in lista}:
            lista.append(c)
    return lista


def mandar(bd: Path, espacio, hoy: date, toca: Toca, envio: Envio, prueba: bool = False, usuarios: list[str] = (),
           quien: str = db.EL_PORTAL) -> str:
    """Manda el aviso de una empresa y lo apunta en «Actividad». `usuarios`: los correos de sus usuarios; `quien`, quién
    lo manda (el portal solo o, el de prueba, la persona). Devuelve qué ha pasado, para la persona. Lanza AvisoFallido
    si el correo no ha salido (la notificación sale igualmente)."""
    e = espacio["id"]
    est = pendiente.estado(bd, espacio, hoy)
    m = mensaje(est, pendiente.pendientes(bd, e, est), toca, prueba, espacio["nombre"])
    titulo = f"Portal ISO 42001 · {espacio['nombre']}"
    a_quien = para(bd, e, list(usuarios))
    cuando = datetime.combine(hoy, datetime.now().time())
    que = ("prueba · " if prueba else "") + m.corto
    try:
        if a_quien:
            envio.correo(a_quien, m.asunto, m.html, db.ajuste(bd, e, CUENTA, ""))
    except AvisoFallido as error:
        db.apuntar(bd, e, cuando, "aviso_fallido", detalle=str(error), quien=quien)
        envio.notificacion(f"{titulo}: el correo no ha salido", f"{m.corto} {error}")
        raise
    db.apuntar(bd, e, cuando, "aviso", detalle=que + (f" · a {', '.join(a_quien)}" if a_quien else " · sin destinatarios"),
               quien=quien)
    envio.notificacion(titulo, m.corto)
    return (f"Aviso mandado a {', '.join(a_quien)}." if a_quien
            else "No hay destinatarios: solo ha salido la notificación.")


def ejecutar(datos: Path, hoy: date, envio: Envio) -> None:
    """Para cada empresa con los avisos activados, manda lo que toque y apunta que se ha mandado.

    Antes de mandar, lo reserva: con el MySQL, varios ordenadores tienen la tarea y el primero que llega es el que lo
    manda; los demás ven que ya está y no lo repiten. Si el correo no sale, se deja como estaba."""
    cuentas.iniciar(datos)
    for empresa in cuentas.empresas(datos):
        bd = cuentas.bd_de(datos, empresa.slug)
        db.iniciar(bd)
        espacio = {**dict(db.el_espacio(bd)), "nombre": empresa.nombre}
        e = espacio["id"]
        if db.ajuste(bd, e, ACTIVADOS, "0") != "1":
            continue
        desde = date.fromisoformat(db.ajuste(bd, e, DESDE, "") or hoy.isoformat())
        antes = {MANDADO_MES: db.ajuste(bd, e, MANDADO_MES, ""), MANDADO_SEMANA: db.ajuste(bd, e, MANDADO_SEMANA, "")}
        toca = que_toca(hoy, desde, antes[MANDADO_MES], antes[MANDADO_SEMANA])
        reservado = {}
        for clave, dia in ((MANDADO_MES, toca.mes), (MANDADO_SEMANA, toca.semana)):
            if dia and db.reservar_ajuste(bd, e, clave, antes[clave], dia.isoformat()):
                reservado[clave] = dia
        toca = Toca(mes=reservado.get(MANDADO_MES), semana=reservado.get(MANDADO_SEMANA))
        if not toca:
            continue  # no tocaba, o ya lo ha mandado otro ordenador
        try:
            mandar(bd, espacio, hoy, toca, envio, usuarios=[u.correo for u in cuentas.usuarios_de(datos, empresa.slug)])
        except AvisoFallido:
            for clave in reservado:  # queda en «Actividad»; no se apunta como mandado
                db.guardar_ajuste(bd, e, clave, antes[clave])


# --- Programarlo, una vez (programar-avisos.bat) ---

MESES = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
         "November", "December")


def xml_tarea(python: Path, programa: Path, carpeta: Path, hoy: date) -> str:
    """La tarea de Windows: el día 1 y los lunes a las 9:00; si a esa hora el ordenador estaba apagado, en cuanto se
    pueda. Solo con la sesión iniciada (Outlook y las notificaciones lo necesitan) y sin permisos de administrador."""
    inicio = f"{hoy.isoformat()}T{HORA}:00"
    meses = "".join(f"<{m}/>" for m in MESES)
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Avisos del portal ISO 42001: el día 1, resumen del mes; los lunes, lo que vence esa semana.</Description></RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{inicio}</StartBoundary><Enabled>true</Enabled>
      <ScheduleByMonth><DaysOfMonth><Day>1</Day></DaysOfMonth><Months>{meses}</Months></ScheduleByMonth>
    </CalendarTrigger>
    <CalendarTrigger>
      <StartBoundary>{inicio}</StartBoundary><Enabled>true</Enabled>
      <ScheduleByWeek><WeeksInterval>1</WeeksInterval><DaysOfWeek><Monday/></DaysOfWeek></ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec><Command>{xml(str(python))}</Command><Arguments>"{xml(str(programa))}"</Arguments><WorkingDirectory>{xml(str(carpeta))}</WorkingDirectory></Exec>
  </Actions>
</Task>
"""


def registrar_protocolo(orden: str) -> None:
    """El enlace portal-iso:// para el usuario actual (sin administrador): lo abre scripts/abrir_portal.py."""
    import winreg
    base = rf"Software\Classes\{PROTOCOLO}"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, "URL:Portal ISO 42001")
        winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\open\command") as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, orden)


def programar(raiz: Path, hoy: date) -> str:
    """Crea (o sustituye) la tarea de Windows y registra el enlace de la notificación."""
    pythonw = raiz / ".venv" / "Scripts" / "pythonw.exe"  # sin ventana negra
    archivo = Path(tempfile.gettempdir()) / "portal_iso_tarea.xml"
    archivo.write_text(xml_tarea(pythonw, raiz / "scripts" / "avisos.py", raiz, hoy), encoding="utf-16")
    hecho = subprocess.run(["schtasks", "/Create", "/TN", TAREA, "/XML", str(archivo), "/F"],
                           capture_output=True, text=True)
    if hecho.returncode != 0:
        return f"No se ha podido crear la tarea de Windows: {(hecho.stderr or hecho.stdout).strip()}"
    registrar_protocolo(f'"{pythonw}" "{raiz / "scripts" / "abrir_portal.py"}" "%1"')
    return (f"Listo. La tarea «{TAREA}» manda los avisos el día 1 y cada lunes a las {HORA} (o al encender el "
            "ordenador, si estaba apagado). Actívalos en Ajustes del portal si aún no lo has hecho.")
