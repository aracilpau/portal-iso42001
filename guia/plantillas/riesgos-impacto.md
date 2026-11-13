# Procedimiento de evaluación de riesgos y de impacto de la IA de {nombre}

Versión 1.0 · Fecha: {fecha} · Aprobado por: {direccion} · Firma: [POR COMPLETAR: firma de quien aprueba]

## Qué es este documento

Dice cómo evalúa {nombre} los riesgos de sus sistemas de inteligencia artificial (IA) y su impacto en las personas,
los grupos y la sociedad, para que las evaluaciones se hagan siempre igual y se puedan comparar. Aquí se define el
método; las evaluaciones hechas se guardan aparte.

## Cuándo se evalúa

Se evalúan los riesgos y el impacto de cada sistema de IA del inventario:

- antes de ponerlo en marcha o de empezar a usarlo;
- cuando cambia de forma importante (otro uso, otros datos, otro proveedor, otro modelo);
- después de un incidente grave o una queja relacionada con él;
- y, como mínimo, una vez al año, para comprobar que sigue valiendo.

Hoy los sistemas a evaluar son:

{sistemas}

## Quién la hace

La evaluación de riesgos la hace [POR COMPLETAR: el rol de gestión de riesgos de IA], y la de impacto,
[POR COMPLETAR: el rol de evaluaciones de impacto], con la persona responsable de cada sistema. Los resultados los
aprueba [POR COMPLETAR: quién, por ejemplo la responsable del sistema de gestión de la IA].

## Paso 1. Evaluar el impacto en las personas

Para cada sistema se responde, por escrito:

- **Para qué se usa** y quién lo usa.
- **A quién puede afectar:** clientes, usuarios, empleados, candidatos, el público…
- **Cómo les puede afectar:** decisiones injustas o con sesgo, errores, falta de información, privacidad, seguridad,
  dependencia excesiva de la IA.
- **Qué medidas hay** para evitarlo o reducirlo (por ejemplo, que una persona revise lo que hace la IA).
[si personas]

Como la IA de la empresa puede afectar a personas, esta parte se hace con especial cuidado y se tiene en cuenta en la
evaluación de riesgos (paso 2).
[/si]
[si alcance]

Como algún sistema tiene un alcance amplio (mucha gente o información pública), se valora también su impacto en la
sociedad.
[/si]

## Paso 2. Identificar y analizar los riesgos

Se hace una lista de lo que puede salir mal con cada sistema: para la empresa (legal, económico, de reputación), para
las personas (lo que salió en el paso 1) y para la sociedad. De cada riesgo se valora:

| Probabilidad | Qué quiere decir |
|---|---|
| 1 · Baja | Muy raro que pase |
| 2 · Media | Puede pasar alguna vez |
| 3 · Alta | Es fácil que pase |

| Consecuencia | Qué quiere decir |
|---|---|
| 1 · Leve | Molestia que se arregla fácil |
| 2 · Grave | Daño a alguien o a la empresa que cuesta arreglar |
| 3 · Muy grave | Daño serio a personas, incumplimiento de la ley o daño difícil de reparar |

El **nivel de riesgo** es probabilidad × consecuencia (de 1 a 9).

## Paso 3. Valorar los riesgos

| Nivel | Qué se hace |
|---|---|
| 1 a 2 · Aceptable | Se acepta y se vigila |
| 3 a 4 · A reducir | Se toman medidas para bajarlo, con responsable y plazo |
| 6 a 9 · No aceptable | No se usa el sistema (o ese uso) hasta bajarlo; lo aprueba la dirección |

[POR COMPLETAR: ajustad estos umbrales al riesgo que la empresa acepta según su política de IA].

## Paso 4. Tratar los riesgos y guardar los resultados

Para cada riesgo que no se acepta se decide qué medida se toma, quién la aplica y para cuándo. El riesgo que queda
después de las medidas lo acepta [POR COMPLETAR: quién, por ejemplo la dirección].
[si proveedores]
En los sistemas de proveedores, se tienen en cuenta también los riesgos que vienen del proveedor (que cambie el
modelo, que falle, qué hace con nuestros datos).
[/si]

Cada evaluación de riesgos y de impacto se guarda, con su fecha y su versión, en [POR COMPLETAR: dónde, por ejemplo
el portal de la ISO, en los puntos 8.2 y 8.4].
