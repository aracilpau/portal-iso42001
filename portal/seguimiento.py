# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Las cuentas del seguimiento: qué está cumplido, hasta cuándo y los porcentajes.

Solo se guardan los puntos marcados a mano (con el día en que se cumplieron o renovaron), por
punto o, en los puntos por sistema, por punto y sistema. Todo lo demás se calcula aquí cada vez:
- un punto propio vence al pasar el plazo de su requisito, contado desde que se cumplió o
  renovó, salvo que se haya recolocado a mano; 30 días antes pasa a «vence
  pronto» y sigue contando; vencido, deja de contar;
- un punto apoyado se cumple cuando están completos **todos** los requisitos en los que se
  apoya;
- un punto por sistema tiene una línea por cada sistema activo al que le toca (todos, o solo los
  del producto) y se cumple cuando lo están todas. Las líneas de A.4.2.a a A.4.6.a se
  cumplen con la ficha del inventario; las que se apoyan en otros requisitos miran la
  línea del mismo sistema, y los apoyos que no tocan a ese sistema no se miran. Sin
  sistemas en el inventario, quedan pendientes; si hay sistemas pero a ninguno le toca, «no hacen
  falta por ahora»: ni cuentan como hechos ni como pendientes;
- un requisito está completo cuando lo están todos sus puntos que no son «Recomendado» y hacen
  falta; si ninguno hace falta, el requisito «no hace falta por ahora» y no entra en los porcentajes
  (para los que se apoyan en él, no estorba);
- la 4.4 (sin puntos) está completa cuando lo están todos los demás requisitos;
- un control que no aplica (Declaración de Aplicabilidad) no cuenta en nada, y los puntos (o
  líneas) que se apoyaban en él pasan a ser trabajo propio (notas de 8.1, A.9.4 y A.10.4).
"""
import calendar
from dataclasses import dataclass
from datetime import date
from functools import cached_property

from portal import guia
from portal.db import Marca, Recordatorio, Sistema

# Cómo se cumple cada punto (o cada línea de un punto por sistema)
PROPIO = "propio"        # se marca a mano
APOYADO = "apoyado"      # se cumple solo con otros requisitos
SISTEMA = "sistema"      # por sistema: una línea por sistema del inventario
FICHA = "ficha"          # por sistema, y cada línea se cumple con la ficha del inventario

# Qué campo de la ficha cumple cada punto
CAMPO_DE = {"A.4.2.a": "para_que", "A.4.3.a": "datos", "A.4.4.a": "herramientas",
            "A.4.5.a": "infraestructura", "A.4.6.a": "personas"}

# Los cuatro estados de un punto
PENDIENTE = "pendiente"
CUMPLIDO = "cumplido"
VENCE_PRONTO = "vence_pronto"
VENCIDO = "vencido"
NO_HACE_FALTA = "no_hace_falta"  # por sistema, cuando hay sistemas pero a ninguno le toca
CUENTAN = (CUMPLIDO, VENCE_PRONTO)

ANTELACION = 30  # días antes de vencer en que un punto pasa a «vence pronto»


def clase(p: guia.Punto) -> str:
    if p.codigo in CAMPO_DE:
        return FICHA
    if p.por_sistema:
        return SISTEMA
    if p.apoyos:
        return APOYADO
    return PROPIO


def toca(p: guia.Punto, x: Sistema) -> bool:
    """Si un punto por sistema le toca a un sistema: «solo producto» no toca a las herramientas."""
    return bool(p.por_sistema) and (p.por_sistema != guia.POR_SISTEMA["Solo producto"] or x.tipo == "producto")


PLAZO_GENERAL = 12  # la revisión general, en meses: la auditoría anual


def vence_por_defecto(req: guia.Requisito) -> bool:
    """Los periódicos y los de «una vez y revisar» vencen con la revisión general;
    los de solo «por evento» no vencen por fecha: se reabren."""
    return "Periódico" in req.cada_cuanto or "Una vez y revisar" in req.cada_cuanto


# Recordatorios por defecto: solo donde hay que ir haciendo cosas durante el año.
# Son recomendaciones del portal: la norma no fija frecuencias.
RECORDAR_POR_DEFECTO = {"6.2": 3, "9.1": 3, "10.1": 3, "A.6.2.6": 3,
                        "7.2": 6, "7.3": 6, "8.2": 6, "A.4.2": 6}


# Cada cuántos meses pregunta el portal si ha pasado algo que reabra requisitos
PREGUNTAR_POR_DEFECTO = 4


def proxima_pregunta(meses: int, desde: date, contestada: date | None) -> date | None:
    """Cuándo toca preguntar «¿ha pasado algo?»: pasados sus meses desde la última respuesta (o desde
    que se creó el espacio). Con 0 meses no se pregunta."""
    if not meses:
        return None
    return sumar_meses(max(f for f in (desde, contestada) if f), meses)


def se_reabre(req: guia.Requisito) -> bool:
    """Los que se reabren cuando pasa algo: «por evento» y «una vez y revisar»."""
    return "Por evento" in req.cada_cuanto or "Una vez y revisar" in req.cada_cuanto


def sumar_meses(d: date, meses: int) -> date:
    """Mismo día N meses después; si ese mes es más corto, el último día del mes."""
    m = d.month - 1 + meses
    año, mes = d.year + m // 12, m % 12 + 1
    return date(año, mes, min(d.day, calendar.monthrange(año, mes)[1]))


# El requisito al que pertenece cada punto
REQUISITO_DE = {p.codigo: r for r in guia.requisitos() for p in r.puntos}


def _peor(estados: set[str]) -> str:
    """El estado de un conjunto de líneas: manda el peor."""
    for e in (PENDIENTE, VENCIDO, VENCE_PRONTO):
        if e in estados:
            return e
    return CUMPLIDO


@dataclass
class Avance:
    hechos: int
    total: int

    @property
    def porcentaje(self) -> int:
        return round(100 * self.hechos / self.total) if self.total else 0


@dataclass
class Aviso:
    """Una entrada del panel de vencimientos: un punto o una línea de un punto por sistema."""
    requisito: guia.Requisito
    punto: guia.Punto
    sistema: Sistema | None
    vence: date | None


class Seguimiento:
    """El estado de un espacio, a partir de lo marcado a mano y del inventario.

    `marcados` puede ser un conjunto de códigos (cumplidos hoy, como en las pruebas de las cuentas)
    o las marcas de la base de datos, con sus fechas. `lineas` son las marcas de los puntos por
    sistema, por (punto, id del sistema).
    """

    def __init__(self, marcados: set[str] | dict[str, Marca], *, plazos: dict[str, int | None] | None = None,
                 antelacion: int = ANTELACION, hoy: date | None = None, excluidos: set[str] = frozenset(),
                 sistemas: list[Sistema] = (), lineas: dict[tuple[str, int], Marca] | None = None,
                 recordatorios: dict[str, Recordatorio] | None = None, inicio: date | None = None,
                 plazo_general: int = PLAZO_GENERAL):
        self.hoy = hoy or date.today()
        if not isinstance(marcados, dict):
            marcados = {c: Marca(self.hoy) for c in marcados}
        self.marcas = marcados
        self.lineas = lineas or {}
        self.recordatorios = recordatorios or {}
        self.inicio = inicio or self.hoy  # cuándo se creó el espacio: desde ahí cuentan los de por defecto
        self.plazos = plazos or {}  # por requisito, si se cambió: None no vence; otro valor, sí
        self.plazo_general = plazo_general
        self.antelacion = antelacion
        self.excluidos = excluidos
        self.sistemas = [x for x in sistemas if x.retirado is None]  # los retirados no cuentan
        self._completo: dict[str, bool] = {}
        self._completo_para: dict[tuple[str, int], bool] = {}

    # --- Aplicabilidad ---

    def aplica(self, codigo: str) -> bool:
        return codigo not in self.excluidos

    def requisitos(self) -> list[guia.Requisito]:
        """Los que cuentan: todos menos los controles que no aplican."""
        return [r for r in guia.requisitos() if self.aplica(r.codigo)]

    def clase(self, p: guia.Punto) -> str:
        """Como `clase`, pero si se apoya en un control que no aplica, pasa a ser propio."""
        c = clase(p)
        if c == APOYADO and any(a in self.excluidos for a in p.apoyos):
            return PROPIO
        return c

    def clase_linea(self, p: guia.Punto) -> str:
        """Cómo se cumple cada línea de un punto por sistema: con la ficha, sola o a mano."""
        if clase(p) == FICHA:
            return FICHA
        if p.apoyos and not any(a in self.excluidos for a in p.apoyos):
            return APOYADO
        return PROPIO

    def reparto(self, req: guia.Requisito) -> dict[str, int]:
        """Cuántos puntos obligatorios de un requisito son propios, apoyados o por sistema."""
        cuenta = {PROPIO: 0, APOYADO: 0, SISTEMA: 0}
        for p in req.puntos:
            if not p.recomendado:
                c = self.clase(p)
                cuenta[SISTEMA if c == FICHA else c] += 1
        return cuenta

    # --- Plazos y fechas ---

    def vence_por_fecha(self, req: guia.Requisito) -> bool:
        if req.codigo in self.plazos:
            return self.plazos[req.codigo] is not None
        return vence_por_defecto(req)

    def plazo(self, req: guia.Requisito) -> int | None:
        """Meses hasta que vence: los de la revisión general, o None si no vence por fecha."""
        return self.plazo_general if self.vence_por_fecha(req) else None

    def _vence_marca(self, p: guia.Punto, m: Marca | None) -> date | None:
        if m is None:
            return None
        if m.vence_manual:
            return m.vence_manual
        meses = self.plazo(REQUISITO_DE[p.codigo])
        return sumar_meses(m.desde, meses) if meses else None

    def _por_fecha(self, vence: date | None) -> str:
        if vence is None:
            return CUMPLIDO
        if self.hoy > vence:
            return VENCIDO
        if (vence - self.hoy).days <= self.antelacion:
            return VENCE_PRONTO
        return CUMPLIDO

    def vence(self, p: guia.Punto) -> date | None:
        """Cuándo vence un punto; en los de por sistema, la línea que vence antes."""
        if self.clase(p) in (SISTEMA, FICHA):
            fechas = [v for x in self.sistemas_de(p) if (v := self.vence_en(p, x))]
            return min(fechas) if fechas else None
        return self._vence_marca(p, self.marcas.get(p.codigo))

    # --- Líneas de los puntos por sistema ---

    def sistemas_de(self, p: guia.Punto) -> list[Sistema]:
        """Los sistemas activos a los que les toca un punto por sistema."""
        return [x for x in self.sistemas if toca(p, x)]

    def vence_en(self, p: guia.Punto, x: Sistema) -> date | None:
        c = self.clase_linea(p)
        if c == FICHA:
            # Por defecto no vencen: A.4.2 a A.4.6 son «por evento»
            meses = self.plazo(REQUISITO_DE[p.codigo])
            return sumar_meses(x.actualizado, meses) if meses else None
        if c == APOYADO:
            return None
        return self._vence_marca(p, self.lineas.get((p.codigo, x.id)))

    def estado_en(self, p: guia.Punto, x: Sistema) -> str:
        """El estado de la línea de un sistema en un punto por sistema."""
        c = self.clase_linea(p)
        if c == FICHA:
            if not x.campo(CAMPO_DE[p.codigo]).strip():
                return PENDIENTE
            return self._por_fecha(self.vence_en(p, x))
        if c == APOYADO:
            return CUMPLIDO if all(self._apoyo_vale(a, x) for a in p.apoyos) else PENDIENTE
        if (p.codigo, x.id) not in self.lineas:
            return PENDIENTE
        return self._por_fecha(self.vence_en(p, x))

    def marcado_en(self, p: guia.Punto, x: Sistema) -> bool:
        """Si la línea tiene el tick puesto, aunque esté vencida (para enseñar Desmarcar y Renovar)."""
        return self.clase_linea(p) == PROPIO and (p.codigo, x.id) in self.lineas

    def faltan_sistemas(self, p: guia.Punto) -> list[Sistema]:
        return [x for x in self.sistemas_de(p) if self.estado_en(p, x) == PENDIENTE]

    def faltan_en(self, p: guia.Punto, x: Sistema) -> list[str]:
        """En una línea apoyada, los requisitos que aún le faltan a ese sistema."""
        return [a for a in p.apoyos if not self._apoyo_vale(a, x)]

    def _apoyo_vale(self, codigo: str, x: Sistema) -> bool:
        """Un apoyo, mirado para un sistema: si no le toca, no se mira; si le toca, tienen
        que estar sus puntos de empresa y su línea de ese sistema."""
        req = guia.requisito(codigo)
        if not req.puntos:
            return self.completo(codigo)
        obligatorios = [q for q in req.puntos if not q.recomendado]
        le_toca = [q for q in obligatorios if not q.por_sistema or toca(q, x)]
        if not le_toca:
            return True
        return self.completo_para(codigo, x)

    def completo_para(self, codigo: str, x: Sistema) -> bool:
        """Un requisito, para un sistema: sus puntos de empresa y la línea de ese sistema en los
        puntos por sistema que le tocan."""
        clave = (codigo, x.id)
        if clave not in self._completo_para:
            puntos = [q for q in guia.requisito(codigo).puntos if not q.recomendado]
            self._completo_para[clave] = all(
                (self.estado_en(q, x) in CUENTAN) if q.por_sistema else self.cumplido(q)
                for q in puntos if not q.por_sistema or toca(q, x))
        return self._completo_para[clave]

    # --- Puntos ---

    def estado(self, p: guia.Punto) -> str:
        c = self.clase(p)
        if c == APOYADO:
            return CUMPLIDO if all(self.completo(a) for a in p.apoyos) else PENDIENTE
        if c in (SISTEMA, FICHA):
            if not self.sistemas:
                return PENDIENTE  # sin inventario no hay nada que valga
            suyos = self.sistemas_de(p)
            if not suyos:
                return NO_HACE_FALTA  # hay sistemas, pero a ninguno le toca
            return _peor({self.estado_en(p, x) for x in suyos})
        if p.codigo not in self.marcas:
            return PENDIENTE
        return self._por_fecha(self.vence(p))

    def marcado(self, p: guia.Punto) -> bool:
        """Si tiene el tick puesto, aunque esté vencido (para enseñar Desmarcar y Renovar)."""
        return self.clase(p) == PROPIO and p.codigo in self.marcas

    def algo_marcado(self, req: guia.Requisito) -> bool:
        """Si el requisito tiene algo marcado a mano, por punto o por sistema (para enseñar Reabrir)."""
        return any(self.marcado(p) or any(self.marcado_en(p, x) for x in self.sistemas_de(p))
                   for p in req.puntos)

    # --- Reabrir cuando pasa algo ---

    def a_reabrir(self, req: guia.Requisito) -> list[tuple[guia.Punto, Sistema | None]]:
        """Lo marcado a mano que vuelve a pendiente al reabrir: los puntos propios y las líneas de los
        puntos por sistema. Lo que se cumple solo (apoyado o con la ficha del inventario) no se toca."""
        res = []
        for p in req.puntos:
            c = self.clase(p)
            if c == PROPIO and self.marcado(p):
                res.append((p, None))
            elif c == SISTEMA:
                res += [(p, x) for x in self.sistemas_de(p) if self.marcado_en(p, x)]
        return res

    def con_ficha(self, req: guia.Requisito) -> bool:
        """Si alguno de sus puntos se cumple con la ficha del inventario (se pone al día ahí)."""
        return any(clase(p) == FICHA for p in req.puntos)

    def hace_falta(self, p: guia.Punto) -> bool:
        return self.estado(p) != NO_HACE_FALTA

    def cumplido(self, p: guia.Punto) -> bool:
        """Si cuenta en el porcentaje: cumplido o vence pronto."""
        return self.estado(p) in CUENTAN

    def faltan(self, p: guia.Punto) -> list[str]:
        """Los requisitos en los que se apoya y que aún no están completos."""
        return [a for a in p.apoyos if not self.completo(a)]

    def avisos(self, estado: str) -> list[Aviso]:
        """Para el panel: los puntos propios y las líneas por sistema en un estado; lo que vence antes, primero."""
        res = []
        for r in self.requisitos():
            for p in r.puntos:
                c = self.clase(p)
                if c == PROPIO and self.estado(p) == estado:
                    res.append(Aviso(r, p, None, self.vence(p)))
                elif c in (SISTEMA, FICHA):
                    res += [Aviso(r, p, x, self.vence_en(p, x)) for x in self.sistemas_de(p)
                            if self.estado_en(p, x) == estado]
        return sorted(res, key=lambda a: a.vence or date.max)

    # --- Recordatorios intermedios ---

    def ultimo_marcado(self, req: guia.Requisito) -> date | None:
        """La última vez que se marcó o renovó algo del requisito, por punto o por sistema."""
        codigos = {p.codigo for p in req.puntos}
        fechas = [m.desde for c, m in self.marcas.items() if c in codigos]
        fechas += [m.desde for (c, _), m in self.lineas.items() if c in codigos]
        return max(fechas) if fechas else None

    def recordatorio(self, req: guia.Requisito) -> Recordatorio | None:
        """El que se ha puesto en Ajustes o, si no se ha tocado, el de por defecto."""
        r = self.recordatorios.get(req.codigo)
        if r is not None:
            return r if r.meses else None  # 0: «sin recordatorio» elegido a mano
        meses = RECORDAR_POR_DEFECTO.get(req.codigo)
        return Recordatorio(meses, self.inicio) if meses else None

    def proximo_recordatorio(self, req: guia.Requisito) -> date | None:
        """Cuándo toca el siguiente recordatorio: pasados sus meses desde lo último que se hizo (se
        configuró, se marcó o renovó algo, o se pulsó «Hecho»)."""
        r = self.recordatorio(req)
        if r is None or not self.aplica(req.codigo):
            return None
        ancla = max(f for f in (r.desde, r.hecho, self.ultimo_marcado(req)) if f)
        return sumar_meses(ancla, r.meses)

    def recordatorios_hoy(self) -> list[tuple[guia.Requisito, date]]:
        """Los recordatorios que tocan hoy (o antes y no se han hecho), el más antiguo primero."""
        res = [(r, f) for r in self.requisitos() if (f := self.proximo_recordatorio(r)) and f <= self.hoy]
        return sorted(res, key=lambda rf: rf[1])

    # --- Requisitos ---

    def completo(self, codigo: str) -> bool:
        # No hay círculos entre requisitos, así que esta recursión siempre termina
        if codigo not in self._completo:
            req = guia.requisito(codigo)
            obligatorios = [p for p in req.puntos if not p.recomendado]
            if obligatorios:
                self._completo[codigo] = all(self.cumplido(p) for p in obligatorios if self.hace_falta(p))
            else:
                self._completo[codigo] = all(self.completo(c) for c in self._otros(codigo))
        return self._completo[codigo]

    def no_hace_falta(self, codigo: str) -> bool:
        """Si ninguno de sus puntos obligatorios hace falta por ahora (solo IA del producto y no hay)."""
        obligatorios = [p for p in guia.requisito(codigo).puntos if not p.recomendado]
        return bool(obligatorios) and not any(self.hace_falta(p) for p in obligatorios)

    def _otros(self, codigo: str) -> list[str]:
        """Para la 4.4: todos los demás que cuentan."""
        return [r.codigo for r in self.requisitos()
                if r.codigo != codigo and r.puntos and not self.no_hace_falta(r.codigo)]

    def avance(self, codigo: str) -> Avance:
        req = guia.requisito(codigo)
        obligatorios = [p for p in req.puntos if not p.recomendado]
        if obligatorios:
            necesarios = [p for p in obligatorios if self.hace_falta(p)]
            return Avance(sum(self.cumplido(p) for p in necesarios), len(necesarios))
        otros = self._otros(codigo)
        return Avance(sum(self.completo(c) for c in otros), len(otros))

    # --- Panel ---

    @cached_property
    def obligatorios(self) -> Avance:
        reqs = [r for r in guia.requisitos() if r.obligatorio and not self.no_hace_falta(r.codigo)]
        return Avance(sum(self.completo(r.codigo) for r in reqs), len(reqs))

    @cached_property
    def controles(self) -> Avance:
        # Los sin decidir cuentan como si aplicaran; solo excluir baja el total
        reqs = [r for r in self.requisitos() if not r.obligatorio and not self.no_hace_falta(r.codigo)]
        return Avance(sum(self.completo(r.codigo) for r in reqs), len(reqs))

    @cached_property
    def sin_hacer_falta(self) -> list[guia.Requisito]:
        """Los controles que aplican pero no hacen falta por ahora (para decirlo en Inicio)."""
        return [r for r in self.requisitos() if self.no_hace_falta(r.codigo)]

    @cached_property
    def recomendados(self) -> Avance:
        puntos = [p for r in self.requisitos() for p in r.puntos if p.recomendado]
        return Avance(sum(self.cumplido(p) for p in puntos), len(puntos))
