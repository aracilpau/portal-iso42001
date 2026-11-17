# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""El borrador de la revisión por la dirección (9.3).

Claude redacta, con los datos del portal del periodo, un borrador del acta ordenado según lo que pide la 9.3:
acciones de revisiones anteriores, cambios, desempeño, oportunidades de mejora y decisiones. Las cifras y los hechos
salen de los datos; lo que solo puede poner la dirección queda «[POR COMPLETAR: …]». Se descarga en Word; no es una
prueba hasta que la dirección lo aprueba y se sube a la 9.3.
"""
import re
from datetime import date

from portal import seguimiento

ESFUERZO = "medium"
NOMBRE = "Revision por la direccion"  # sin tildes en el nombre del archivo, como el de la Declaración

INSTRUCCIONES = """Preparas el borrador del acta de la revisión por la dirección (requisito 9.3 de la ISO/IEC 42001) de
una empresa. Te paso los datos de su portal de seguimiento del periodo que cubre la revisión.

Escribe el borrador en español, en prosa clara y bien redactada, que se entienda leyéndolo sin conocer el portal.
Usa exactamente esta estructura (líneas que empiezan por «# » y «## »), con párrafos y, si ayudan, listas con «- »:

# Revisión por la dirección del sistema de gestión de la IA
(un párrafo: empresa, periodo que cubre y para qué es esta revisión)
## Datos de la reunión
## 1. Acciones de revisiones anteriores
## 2. Cambios en el contexto y en las partes interesadas
## 3. Desempeño del sistema de gestión de la IA
## 4. Oportunidades de mejora
## 5. Conclusiones y decisiones de la dirección

Reglas:
- Las cifras, fechas y hechos salen SOLO de los datos que te paso. No inventes nada: si de algo no hay datos, dilo
  («El portal no registra auditorías internas en el periodo»).
- En «Desempeño», trata el avance, lo que venció y si se renovó, las no conformidades e incidentes, las mediciones
  (9.1) y la auditoría interna (9.2), según lo que haya en los datos.
- En «Oportunidades de mejora», propón mejoras concretas que salgan de los datos (lo pendiente, lo vencido, lo que
  falta); la dirección decidirá.
- Lo que solo puede poner la dirección va marcado así: [POR COMPLETAR: qué falta]. En «Datos de la reunión»: fecha,
  asistentes. En «Conclusiones y decisiones»: conclusiones, decisiones de mejora o cambio con responsable y plazo, y
  recursos. Si no hay revisiones anteriores en los datos, dilo en el apartado 1 y deja lo que haya que completar.
- No uses tablas ni negritas. No escribas nada antes del título ni después del último apartado."""


def periodo(actividad: list, hoy: date) -> tuple[date, date, bool]:
    """Desde la última revisión subida a la 9.3 (el último archivo subido a la 9.3, según «Actividad») hasta hoy. Si
    no hay ninguna, el último año. El tercer valor dice si había revisión anterior."""
    subidas = [f["cuando"][:10] for f in actividad
               if f["requisito"] == "9.3" and f["accion"] in ("subido", "version")]
    if subidas:
        return date.fromisoformat(max(subidas)), hoy, True
    return seguimiento.sumar_meses(hoy, -12), hoy, False


def _dentro(f, desde: date, hasta: date) -> bool:
    return desde.isoformat() <= f["cuando"][:10] <= hasta.isoformat()


def mensaje(*, perfil: dict, desde: date, hasta: date, anterior: bool, est, actividad: list, cambios: list,
            sistemas: list, pendientes: dict, nombres_acciones: dict, requisitos: list) -> str:
    """Los datos del periodo, en texto, para Claude."""
    d = perfil["datos"]
    lineas = [f"# Empresa: {d.get('nombre') or '(sin nombre en el cuestionario)'}",
              f"- A qué se dedica: {d.get('actividad') or 'sin contestar'}",
              f"- Quién aprueba (la dirección): {d.get('direccion') or 'sin contestar'}",
              f"- Periodo de la revisión: del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}",
              f"- Revisión anterior: {'sí, subida a la 9.3 el ' + desde.strftime('%d/%m/%Y') if anterior else 'no consta ninguna en el portal'}",
              "", "# Avance a fecha de hoy",
              f"- Requisitos obligatorios completos: {est.obligatorios.hechos} de {est.obligatorios.total} ({est.obligatorios.porcentaje} %)",
              f"- Controles del Anexo A que aplican, completos: {est.controles.hechos} de {est.controles.total} ({est.controles.porcentaje} %)",
              f"- Puntos recomendados cumplidos: {est.recomendados.hechos} de {est.recomendados.total}"]
    sin_completar = [f"{r.codigo} {r.titulo} ({est.avance(r.codigo).hechos} de {est.avance(r.codigo).total})"
                     for r in requisitos if est.aplica(r.codigo) and not est.completo(r.codigo)]
    lineas.append(f"- Requisitos sin completar ({len(sin_completar)}): " + ("; ".join(sin_completar) or "ninguno"))
    lineas += ["", "## Los requisitos que alimentan la revisión"]
    for codigo in ("4.1", "4.2", "9.1", "9.2", "10.2"):
        r = next(x for x in requisitos if x.codigo == codigo)
        av = est.avance(codigo)
        lineas.append(f"- {codigo} {r.titulo}: {'completo' if est.completo(codigo) else 'sin completar'} "
                      f"({av.hechos} de {av.total} puntos)")

    del_periodo = [f for f in actividad if _dentro(f, desde, hasta)]
    lineas += ["", "# Lo hecho en el periodo (registro de actividad)"]
    cuentas: dict[str, int] = {}
    for f in del_periodo:
        cuentas[f["accion"]] = cuentas.get(f["accion"], 0) + 1
    for accion, n in sorted(cuentas.items(), key=lambda x: -x[1]):
        lineas.append(f"- {nombres_acciones.get(accion, accion)}: {n}")
    if not cuentas:
        lineas.append("- No hay actividad registrada en el periodo.")

    lineas += ["", "# Cambios: situaciones de «Ha pasado algo» (cambios de contexto, personas, proveedores, incidentes)"]
    eventos = [f for f in del_periodo if f["accion"] == "evento"]
    lineas += [f"- {f['cuando'][:10]}: {f['detalle']}" for f in eventos] or ["- Ninguna registrada en el periodo."]
    lineas += ["", "# Cambios en el inventario de sistemas de IA"]
    altas = [f for f in del_periodo if f["accion"] in ("sistema_alta", "sistema_retirado", "sistema_activado")]
    lineas += [f"- {f['cuando'][:10]}: {nombres_acciones.get(f['accion'], f['accion'])}: {f['sistema']}" for f in altas] \
        or ["- Ninguno en el periodo."]
    activos = [x for x in sistemas if x.retirado is None]
    lineas.append(f"- Sistemas activos hoy ({len(activos)}): " + (", ".join(
        f"{x.nombre} ({'la ofrecemos a clientes' if x.tipo == 'producto' else 'la usa el equipo'})" for x in activos) or "ninguno"))
    lineas += ["", "# Cambios en la Declaración de Aplicabilidad"]
    del_periodo_cambios = [c for c in cambios if desde.isoformat() <= c["fecha"] <= hasta.isoformat()]
    lineas += [f"- {c['fecha']}: {c['control']}: {c['antes']} → {c['ahora']}. Motivo: {c['motivo']}"
               for c in del_periodo_cambios] or ["- Ninguno en el periodo."]

    lineas += ["", "# Vencimientos"]
    lineas += [f"- Vencido hoy: {a.punto.codigo}{' (' + a.sistema.nombre + ')' if a.sistema else ''} "
               f"{a.requisito.titulo}, venció el {a.vence:%d/%m/%Y}" for a in pendientes["vencidos"]] \
        or ["- No hay nada vencido hoy."]
    lineas += [f"- Vence pronto: {a.punto.codigo} {a.requisito.titulo}, el {a.vence:%d/%m/%Y}" for a in pendientes["pronto"]]
    renovados = cuentas.get("renovado", 0) + cuentas.get("version", 0)
    lineas.append(f"- Renovaciones o versiones nuevas en el periodo: {renovados}")
    revisados = [f for f in del_periodo if f["accion"] == "revisado"]
    if revisados:
        lineas += ["", "# Revisiones de archivos hechas con la IA en el periodo"]
        lineas += [f"- {f['punto']}{' (' + f['sistema'] + ')' if f['sistema'] else ''}: {f['detalle']}" for f in revisados]
    return "\n".join(lineas)


def valida(texto: str) -> bool:
    """Que tenga el título y los apartados pedidos."""
    return texto.lstrip().startswith("# ") and len(re.findall(r"^## ", texto, re.M)) >= 5


def word(texto: str) -> bytes:
    """El borrador en Word, con un aviso arriba y los [POR COMPLETAR] resaltados (portal/word.py)."""
    from portal import word as conversor
    return conversor.documento(texto, aviso="Borrador preparado con IA a partir de los datos del portal. Revísalo, "
                                            "complétalo y apruébalo antes de usarlo; aprobado, súbelo a la 9.3.")


def nombre_archivo(desde: date, hasta: date) -> str:
    return f"{NOMBRE} {desde.isoformat()} a {hasta.isoformat()}.docx"
