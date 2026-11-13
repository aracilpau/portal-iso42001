# Manual de uso del portal ISO/IEC 42001

Cómo se usa el portal, pantalla a pantalla. El chat del portal («Preguntar») también lo usa para responder dudas sobre
el uso del portal. Cómo instalarlo, actualizarlo y hacer copias de seguridad, en [`instalar.md`](instalar.md); la licencia (solo uso interno), en
su [aviso legal](instalar.md#aviso-legal).

El portal tiene un solo estilo, **Mesa de control**: el menú arriba, con el buscador y el botón «Preguntar».

## Índice

- **entrar** — Entrar con correo y contraseña, elegir empresa, cambiar de empresa y salir
- **inicio** — Inicio: el avance, lo que queda por hacer y «Ha pasado algo»
- **requisitos** — La lista de requisitos y sus filtros
- **revision-direccion** — Preparar el borrador de la revisión por la dirección (9.3)
- **ficha** — La ficha de un requisito: los puntos, marcarlos, vencimientos, renovar
- **archivos** — Subir archivos, quitarlos, versiones nuevas y versiones anteriores
- **revisor** — «Revisar con IA»: que la IA diga si los archivos de un punto lo cumplen
- **borradores** — «Hacer borrador»: un Word con la plantilla del documento de un requisito
- **sistemas-en-puntos** — Los puntos que van por sistema de IA y los que se cumplen solos
- **inventario** — El inventario de IA: dar de alta, la ficha de cada sistema, retirar
- **declaracion** — La Declaración de Aplicabilidad: decidir si aplica cada control
- **cuestionario** — «Empresa»: el cuestionario de la empresa, todo junto, y el paso a paso de la primera vez
- **propuestas** — Las propuestas de la IA para la Declaración
- **ha-pasado-algo** — «Ha pasado algo» y reabrir requisitos
- **avisos** — Avisos: vencidos, vence pronto, recordatorios
- **avisos-correo** — Avisos por correo y notificación de Windows: el día 1 y cada lunes
- **actividad** — El registro de actividad
- **ajustes** — Ajustes: qué avisa, avisos por correo, revisiones, recordatorios, y tema
- **buscador** — El buscador (Ctrl K)
- **chat** — El chat («Preguntar»)
- **carpetas** — Las carpetas de pruebas en el ordenador
- **arrancar** — Arrancar, la instalación de la primera vez (los dos modos), apagar y el portal de prueba
- **conceptos** — Conceptos: cumplido, vence, por evento, apoyado, recomendado, no aplica

---

## entrar

**Qué es:** lo primero al abrir el portal.

- **Entrar:** correo y contraseña. Si están mal, lo dice sin decir cuál de los dos falla.
- **Elegir empresa:** salen solo las empresas a las que te han asignado. Si no tienes ninguna, lo dice. Cada empresa
  tiene todo lo suyo: seguimiento, Declaración, inventario, cuestionario, ajustes, avisos, Actividad y archivos. Nada
  se mezcla entre empresas. En algunos portales sale también **«General»**: un espacio común en el que entran todas las
  cuentas (no es una empresa que se certifique). En las instalaciones nuevas no se crea.
- **Dónde está todo:** en el portal compartido, en el servidor (un MySQL): las cuentas, las empresas y lo que se
  rellena valen desde cualquier ordenador, y lo que marca uno lo ven los demás. Los archivos de pruebas, en la carpeta
  compartida que elige cada uno en su ordenador (ver «carpetas»). En el modo «solo en este ordenador», todo está en tu
  ordenador.
- **Sin conexión:** si el portal dice «Sin conexión», no llega al servidor donde están los datos. Puede ser que no
  haya internet, que el servidor esté apagado o que no deje entrar desde la red en la que estás (pasa al trabajar fuera
  de la oficina o con los datos del móvil). Si tu equipo ha cambiado la contraseña del MySQL, pulsa «Cambiar los
  datos del MySQL» y escribe la nueva. Si no, avisa a quien instaló el portal; lo que hay que comprobar está en
  `docs/instalar.md`, «Si algo no funciona». Si se corta a mitad de guardar algo, no se guarda nada a medias: vuelve a hacerlo.
- **Sin la carpeta de los archivos:** si en tu ordenador no se ha elegido o ya no está, el portal la pide al entrar (ver
  «carpetas»).
- **En la cabecera,** arriba a la derecha: la empresa y tu nombre, **«Cambiar empresa»** (vuelve a la lista),
  **«Administrar»** (solo el administrador), **«Cambiar contraseña»** y **«Salir»**.
- **Cada vez que se arranca el portal** hay que volver a entrar; también al cerrar el navegador.
- **Cambiar tu contraseña:** «Cambiar contraseña», con la actual y la nueva dos veces (al menos 8 caracteres). Si no te
  sabes la actual, pide al administrador que te ponga otra.
- **Administrar** (solo lo ven los administradores; los demás no lo ven):
  - **Cuentas:** crear una (nombre, correo, contraseña y en qué empresas entra), marcar en qué empresas entra cada una,
    cambiarle la contraseña (la escribe el administrador y se la pasa), **Quitar** (deja de poder entrar aunque tenga el
    portal abierto; lo que hizo se queda en Actividad y se deshace con «Volver a dejar entrar») y nombrar o quitar
    administradores («Hacer administrador» y «Quitar de administrador», con confirmación, que dice qué cambia).
  - **Empresas:** la lista, crear una nueva y **«Cambiar nombre»** (escribes el nuevo y lo confirmas; solo cambia el
    nombre que se ve: sus datos y la carpeta de sus archivos siguen igual, y queda en su Actividad). Borrar una empresa
    no se hace desde el portal, porque se lleva todos sus datos: lo explica `docs/instalar.md`, «Si el administrador
    olvida su contraseña».
  - **Quitarse a uno mismo:** en tu propia fila también salen «Quitar de administrador» y «Quitar», con confirmación.
    Al quitarte de administrador dejas de ver «Administrar»; al quitar tu cuenta, sales y ya no puedes entrar. Para
    volver, te tiene que nombrar o dejar entrar otro administrador.
  - **Para no quedarse fuera:** siempre tiene que quedar un administrador que pueda entrar. Si eres el único, el portal
    no te deja quitarte y te pide que nombres antes a otro.
  - **Quién administra:** al principio, la primera cuenta que se creó (en una instalación nueva, la de quien
    instaló el portal). Después, quien ella nombre.
- **Si el administrador olvida su contraseña:** si hay otro administrador, que se la cambie en «Administrar». Si no,
  se hace con un programa que viene con el portal: lo explica `docs/instalar.md`, «Si el administrador olvida su
  contraseña». **Quien tenga los datos del MySQL puede hacer esto con cualquier cuenta:** dáselos solo a quien sea de
  confianza.
- **Si te quitan de una empresa o la borran,** dejas de verla en cuanto pasas de página.
- **Quién hizo qué:** todo lo que haces queda a tu nombre: en Actividad, en la ficha («Marcado el … por Ana», y en cada
  archivo «Subido por Ana»; si se metió desde el Explorador, «Añadido en la carpeta») y en «Cambios» de la
  Declaración. Lo de antes de las cuentas va sin nombre. Si quitan a alguien, lo que hizo sigue a su nombre.

## inicio

**Qué es:** la primera página. Dice cómo vas y qué tienes pendiente.

- **El avance:** dos porcentajes, «Obligatorios» (las cláusulas 4 a 10, que se cumplen siempre) y «Controles del
  Anexo A» (solo los que aplican). Un requisito cuenta cuando está completo. Los controles sin decidir cuentan como si
  aplicaran; los que no aplican no cuentan. Los puntos recomendados no cuentan en el porcentaje.
- **Lo pendiente:** la lista «Lo siguiente», ordenada por urgencia (vencidos, vencen pronto, recordatorios, sistemas
  nuevos, la pregunta «¿Ha pasado algo?»), cada uno con su botón: «Ir a renovar», «Hecho», «Decidir», «No, nada»
  (ver **avisos**). Además, un mapa con un cuadro por requisito, coloreado por su estado (al pasar el ratón dice cuál
  es).
- **«Ha pasado algo»:** las cinco situaciones a un clic (ver **ha-pasado-algo**).
- Si quedan controles del Anexo A sin decidir, un aviso lleva a la Declaración.
- Si falta algo de «Empresa», otro aviso lleva al cuestionario.

## revision-direccion

**Qué es:** en Inicio, junto al avance, el botón **«Preparar la revisión del año»**. Claude redacta con los datos del
portal un **borrador del acta** de la revisión por la dirección (9.3), en Word, ordenado como pide la norma: acciones
de revisiones anteriores, cambios (lo de «Ha pasado algo», el inventario, la Declaración), desempeño (avance,
vencimientos, mediciones y auditoría), oportunidades de mejora y conclusiones y decisiones.

- **Periodo:** desde la última revisión subida a la 9.3 hasta hoy; si no hay ninguna, el último año. Debajo del botón
  dice qué periodo cubre.
- Las cifras y los hechos salen de los datos del portal. Lo que solo puede poner la dirección (fecha, asistentes,
  conclusiones, decisiones con responsable y plazo, recursos) queda resaltado como **[POR COMPLETAR]**.
- Tarda alrededor de un minuto y se descarga. No se guarda en el portal ni cuenta como prueba: cuando la dirección
  lo apruebe, se sube a la 9.3, y la siguiente revisión empezará desde ese día.
- Necesita Claude Code en el ordenador.

## requisitos

**Qué es:** los 65 requisitos de la norma: 27 obligatorios (cláusulas 4 a 10) y 38 controles del Anexo A.

- Cada fila: código, título, cómo se demuestra (Documento, Registro, Inventario, Práctica), cada cuánto se revisa y el
  avance («3 de 4»). Se pulsa para abrir su ficha.
- Filtros con su número: Todos, Pendientes (los que aplican y no están completos), Vencen o vencidos, Completos, No
  aplican.
- Al pasar el ratón por un requisito sale qué es.

## ficha

**Qué es:** la página de un requisito. Se llega desde la lista, el buscador o cualquier enlace a su código.

- **Arriba:** el código, el título, qué es en llano, cómo se demuestra y cada cuánto, y su porcentaje («2 de 3
  puntos»).
- **Los puntos:** lo que hay que cumplir. Cada uno dice su texto, su tipo (Documento, Registro…), **«Te pedirán»**
  (ejemplos de lo que pide el auditor) y si es recomendado.
- **Marcar un punto:** se pulsa la **casilla** a su izquierda. Pulsarla otra vez lo desmarca. Solo se marcan a mano
  los puntos propios; los que se cumplen solos o van por sistema no tienen casilla (ver **sistemas-en-puntos**).
- **Vencimientos:** al marcar un punto, dice «Vence el …» (un año después, o lo que diga la revisión general). Antes
  de vencer pasa a «Vence pronto»; al vencer, «Vencido: ya no cuenta hasta que se renueve». Los requisitos «por
  evento» no vencen por fecha: dicen «No vence por fecha».
- **Renovar:** el botón «Renovar» del punto dice que sigue valiendo y vuelve a contar desde hoy. Se destaca cuando
  vence pronto o ha vencido.
- **La nota «Cómo lo hacemos aquí»:** lo propio de la empresa (quién se encarga, dónde está cada cosa). Se guarda sola
  mientras se escribe. Está en la columna de la derecha.
- **«¿Ha cambiado algo?»:** en los requisitos que se reabren por evento y tienen algo marcado. Pide confirmación y
  devuelve sus puntos a pendiente. Es una caja a la derecha, con el botón «Reabrir».
- **Controles del Anexo A:** la ficha dice si aplica a tu empresa y enlaza a la Declaración. Si no aplica, no se marca
  nada y no se ven sus archivos.
- **«Lo último»:** a la derecha, lo más reciente que se ha hecho en ese requisito.

## archivos

**Qué es:** las pruebas de cada punto (documentos, registros, capturas…).

- **Subir:** arrastrar uno o varios archivos **encima del punto** (o de la línea de un sistema) y soltarlos. También
  con «+ Archivo». Se guardan en la carpeta de ese punto (ver **carpetas**).
- **Abrir:** pulsar su nombre. Los PDF e imágenes se ven en el navegador; el resto se descarga.
- **Quitar:** pasa el archivo a «Versiones anteriores» del requisito, con el punto y la fecha delante. No se borra.
- **Subir versión nueva:** los archivos actuales del punto pasan a versiones anteriores y entra el nuevo. Si el punto
  estaba marcado y vence, además se renueva desde hoy.
- **Versiones anteriores:** al final de la ficha. Desde ahí se puede **borrar para siempre** (pide confirmación; no se
  puede deshacer).
- Diferencia clave: **renovar** dice que lo que hay sigue valiendo (no cambia archivos); **subir versión nueva**
  sustituye los archivos y, si vence, también renueva.

## revisor

**Qué es:** en cada punto que tiene archivos (y en cada línea de sistema), el botón **«Revisar con IA»**. Claude lee los
archivos de ese punto, todos juntos, y dice si con ellos se cumple: **SÍ** (en verde), **NO** con lo que le falta (en
naranja) o **NO SE PUEDE SABER** (en gris), con el porqué y, en «Ver detalle», en qué parte del archivo se apoya. Si el
archivo no tiene nada que ver con el punto, es un **NO**: lo dice y explica qué documento habría que subir. **NO SE PUEDE
SABER** queda para los archivos que no se pueden leer y lo que no se demuestra con documentos.

- Compara con lo que pide el punto y su «Te pedirán», y con el cuestionario de la empresa.
- Lee Word, Excel, PDF, imágenes y texto. De un PDF también ve quién lo firmó digitalmente y cuándo (el nombre y la
  fecha, sin el DNI), pero no comprueba que la firma sea válida: por eso sale «Firma sin comprobar», y hay que abrirlo en Adobe antes de
  marcar la casilla. Un PDF escaneado sin texto no se puede leer. Si los archivos son muy
  largos, lo dice en vez de revisarlos a medias.
- Tarda alrededor de un minuto. **No marca nada:** la casilla la decides tú.
- La respuesta se queda guardada. Si después cambian los archivos del punto (se sube, se quita o se sustituye uno),
  sale un aviso de que **es de una versión anterior**, y el SÍ o el NO lo dicen, sin su color: conviene «Volver a
  revisar».
- Queda en Actividad como «revisado por la IA». Los archivos salen hacia Claude con la sesión de quien usa el portal.
- Necesita Claude Code en el ordenador.

## borradores

**Qué es:** en la ficha de los requisitos que piden escribir un documento, el botón **«Hacer borrador»** descarga un
Word con el documento redactado por la IA para la empresa. Es una caja a la derecha. Puede tardar un
minuto.

- Hay nueve plantillas: contexto y partes interesadas (4.1 y 4.2), política de IA (5.2 y A.2.2), alcance (4.3),
  roles y responsabilidades (5.3 y A.3.2), procedimiento de riesgos y de impacto (6.1.2 y 6.1.4), objetivos (6.2),
  control de la documentación (7.5), programa de auditoría interna (9.2) y no conformidades (10.2).
- **Base para empezar:** los otros 28 requisitos que piden un documento propio (por ejemplo la 7.4 o muchos controles
  del Anexo A) tienen una plantilla genérica: un apartado por cada punto que se demuestra con un documento, con lo que
  tiene que decir y lo que pedirá el auditor, todo como [POR COMPLETAR], y al final lo que no va en el documento. Solo
  lleva de la empresa el nombre, la fecha y quién aprueba. En la ficha sale como «Base para empezar el documento».
- No hay botón en los requisitos que solo se demuestran con registros o con la práctica (por ejemplo la 7.3), ni en
  los que se cumplen con otros (la 8.1).
- **Con IA:** Claude redacta el documento en formal con todo lo de «Empresa» (también las preguntas abiertas y las de
  la IA ya contestadas), el inventario con la ficha de cada sistema y las notas «Cómo lo hacemos aquí». **No lee los
  archivos subidos.** Arriba lleva «Borrador hecho con IA. Revísalo y apruébalo antes de usarlo».
- **Estructura fija:** los títulos y apartados son siempre los de la plantilla (o los de la base genérica), en el mismo
  orden; la IA solo escribe dentro. Si no ha cambiado nada de lo que se le da, sale el mismo borrador que la vez
  anterior, sin volver a preguntar a la IA.
- **Lo que falta saber:** al final del borrador, las preguntas que la IA necesita para completarlo. Salen también al
  final de «Empresa», en «Lo que pregunta la IA»; lo que se contesta ahí lo usan todos los borradores siguientes. Solo
  pregunta lo que no está ya en el cuestionario o el inventario: lo que falte de ahí se contesta en su sitio.
- Lo que la IA no sabe, o lo que la empresa dice que no tiene, sale como **[POR COMPLETAR]**: el documento no cuenta la
  carencia, y al revisarlo con la IA sale como lo que falta. Si menciona otro documento de la empresa, como la política
  de IA, avisa con un **[A CONFIRMAR]** de que hay que comprobar que está subido y encaja: la IA no lo ha leído. Y lo que propone pero alguien tiene que revisar (las leyes que
  tocan) como **[A CONFIRMAR]**; los dos, en amarillo.
- **Sin IA:** si Claude no está en el ordenador, falla o no respeta la estructura, sale la plantilla rellena como antes,
  con el aviso «Hecho sin IA» y el motivo. Esa se rellena con los datos generales, las respuestas de Sí/No y los
  sistemas del inventario: sale el nombre de la empresa, sus sistemas y solo los apartados que le tocan; con «No lo
  sé», el apartado sale con un aviso para confirmarlo.
- En Actividad: «borrador del documento hecho con IA» o «descargado (sin IA)».
- Si falta algo de «Empresa», encima del botón dice cuántas preguntas quedan por aclarar (sin
  contestar o en «No lo sé»), con un enlace para contestarlas.
- Lo que solo puede decidir la empresa (responsables, riesgo que acepta, dónde se publica, la firma…) sale resaltado
  en amarillo como **[POR COMPLETAR]**.
- No se guarda en el portal ni cuenta como prueba: se completa, se aprueba y se sube. **Debajo del botón dice a qué
  puntos subirlo** (también de otros requisitos que usan el mismo documento, como la 4.1 y la 4.2), a cuáles además una
  vez firmado (la política, al 5.2.e) y qué puntos del requisito no cubre, con lo que hace falta para cada uno.
- Las plantillas son las mismas para cualquier empresa y están en `guia/plantillas/`.

## sistemas-en-puntos

- **Puntos por sistema:** algunos puntos se cumplen una vez por cada sistema de IA del inventario (por ejemplo, la
  evaluación de impacto). Tienen una línea por sistema, cada una con su casilla, sus archivos y su vencimiento. El
  punto está cumplido cuando lo está en todos los sistemas activos a los que les toca. Algunos son «Solo IA del
  producto» y no piden nada a las herramientas de uso.
- **Puntos que se cumplen solos («apoyados»):** se apoyan en otros requisitos y se marcan solos cuando esos están
  completos. No tienen casilla; dicen «Se marcará solo cuando esté completo: …».
- **Puntos de la ficha del sistema:** A.4.2.a a A.4.6.a se cumplen solos al rellenar el campo correspondiente de la
  ficha de cada sistema en el inventario.
- Sin sistemas en el inventario, los puntos por sistema quedan pendientes.

## inventario

**Qué es:** los sistemas de IA de la empresa: la IA del producto y las herramientas de IA que usa la plantilla.

- **Dar de alta:** escribir el nombre, elegir «Del producto» o «Herramienta de uso» y «Añadir». Se abre su ficha.
  - Al dar de alta (o volver a activar) un sistema, la ficha pregunta si se reabren los riesgos (8.2, 8.3) y los
    proveedores (A.10.3), que son de toda la empresa. Se puede reabrir lo marcado o contestar «No hace falta». Si no
    se contesta, la pregunta queda pendiente en los avisos.
- **La ficha de cada sistema:** cinco campos (para qué sirve, datos, herramientas, infraestructura, personas), cada uno
  con su ayuda. Se guarda sola al salir de cada campo. Cada campo lleno cumple uno de los puntos A.4.2.a a A.4.6.a.
- **Retirar:** el sistema deja de contar; su ficha se guarda y sus archivos pasan a versiones anteriores. Se puede
  **volver a activar** desde la lista de retirados.

## declaracion

**Qué es:** la Declaración de Aplicabilidad: para cada uno de los 38 controles del Anexo A, si aplica a la empresa y
por qué. El auditor pregunta por los dos casos.

- **Decidir un control:** elegir «Aplica» o «No aplica» y escribir el porqué. Se guarda solo al dejar de escribir
  (un segundo y medio) o al salir del cuadro.
- **Cambiar una decisión:** al pasar de aplica a no aplica (o al revés), el porqué de antes se vacía y un aviso pide
  el nuevo; ese porqué queda como motivo del cambio en «Cambios».
- **Pestañas:** «Controles» (decidir), «Cambios» (cada decisión y cambio con fecha y motivo) y «Documento» (vista
  previa; se descarga en Word o PDF, o se guarda como prueba en la 6.1.3.c).
- Mientras un control está sin decidir, cuenta en el porcentaje como si aplicara.
- **Desmarcar:** volver a pulsar la opción marcada («Aplica» o «No aplica») la desmarca y el control vuelve a «Sin
  decidir». Queda en «Cambios» («Se deja sin decidir») y en «Actividad»; el porqué escrito se queda en el cuadro.
- Al decidir que un control no aplica, su carpeta de pruebas pasa a llamarse «… (no aplica)».
- Arriba, cuántas preguntas de «Empresa» quedan por aclarar (deciden muchos controles), y las **propuestas** de la IA.

## cuestionario

**Qué es:** la página **«Empresa»**, en el menú de arriba. Cómo es la empresa y cómo usa la IA, todo junto:

- **Datos generales:** nombre, a qué se dedica, tamaño y quién aprueba.
- **Cómo es vuestra IA:** 10 preguntas (Sí / No / No lo sé) de las que depende qué controles de la Declaración aplican.
  La 1 (¿desarrolláis IA?) y la 8 (¿usáis proveedores?) salen marcadas si el inventario ya lo dice.
- **Preguntas abiertas,** en 5 bloques (la empresa y la IA; personas; clientes, leyes y proveedores; cómo trabajáis;
  si desarrolláis IA). Se contestan en llano, como a un compañero; cada una tiene un ejemplo. El bloque 5 solo sale si
  no se ha contestado «No» a si desarrolláis IA. Las leyes no se preguntan.
- Cada respuesta se guarda sola al cambiarla (las abiertas, al salir del cuadro). Arriba dice cuántas están aclaradas:
  «No lo sé» cuenta como por aclarar, igual que una en blanco.
- **Al cambiar una respuesta que ya tenía algo,** debajo sale la lista de requisitos que dependen de ella, como en «Ha
  pasado algo», para reabrir los que hagan falta. Al contestar por primera vez no sale. Los datos generales no reabren
  nada. Cambiar una respuesta no toca lo ya decidido en la Declaración.
- **El paso a paso:** la primera vez que alguien entra en una empresa con el cuestionario sin empezar, sale paso a
  paso (datos, Sí/No y un bloque de abiertas en cada paso), con «Siguiente» (guarda), «Saltar este paso» y «Saltar el
  cuestionario». Terminado o saltado, no vuelve a salir; todo se cambia después en «Empresa».
- Lo usan las propuestas de la IA, los borradores de documentos y el chat (las abiertas, de momento, solo el chat: los
  borradores las usarán cuando los redacte la IA). Mientras quede algo sin contestar o en «No lo sé», Inicio y el botón
  «Hacer borrador» dicen cuántas preguntas quedan por aclarar.

## propuestas

**Qué es:** el botón «Proponer», debajo del cuestionario. Propone, para cada control, APLICA, NO APLICA o FALTA SABER,
con el porqué. Tarda alrededor de medio minuto.

- **Quién decide cada uno (Declaración mixta):**
  - **«Según tu respuesta a la pregunta N»:** lo decide el portal, siempre igual. «Sí» → aplica; «No» → no aplica. Si
    un control depende de dos preguntas, aplica con que una sea «Sí».
  - **«Aplica casi siempre»:** los controles que aplican a casi cualquier empresa.
  - **«Propuesta de la IA»:** los dudosos (pregunta en «No lo sé» o sin contestar, con sistemas en el inventario que
    pueden aclararlo). Los decide Claude, que dice en qué se apoya.
  - Con la pregunta en «No lo sé» o sin contestar y el **inventario vacío**, sale FALTA SABER con la pregunta.
- Claude redacta el porqué de todos, también de los que decide el portal, pero no puede cambiar su decisión.
- **«Míralo:»** sale si algo no cuadra: por ejemplo, el inventario contradice una respuesta, o la IA habría dicho otra
  cosa que el portal. La decisión no cambia; es para que lo revises.

- En cada control: **Aceptar** (la guarda como decisión), **Cambiar** (la pasa al formulario para retocarla) o
  **Descartar**.
- **Falta saber:** lleva una pregunta y un cuadro para contestar; al contestar, Claude vuelve a proponer ese control.
- **Aceptar todas:** acepta las de los controles sin decidir (no las de falta saber).
- En controles ya decididos solo avisa si propondría otra cosa («La IA propondría otra cosa» o «Se propondría otra
  cosa»).
- Nada cambia en la Declaración hasta que se acepta.
- **Sin Claude Code** (o si no responde bien), el botón propone igualmente los que decide el portal; los dudosos se
  quedan como estaban hasta que Claude esté.

## ha-pasado-algo

**Qué es:** hay requisitos que no vencen por fecha (los «por evento»): hay que volver a ellos cuando pasa algo.

- Se elige la situación: persona nueva o cambio de puesto, proveedor de IA nuevo, incidente o queja, cambio en la
  empresa o en la gestión, o cambio de fuera (leyes, clientes, tecnología).
- Sale la lista de requisitos que tocan, con una casilla en los que tienen algo que reabrir. «Reabrir los marcados»
  devuelve sus puntos a pendiente. Queda apuntado en Actividad, aunque no se reabra nada.
- Cada cierto tiempo (por defecto 4 meses) el portal pregunta «¿Ha pasado algo?» en los avisos. Se cambia en Ajustes.
- Un sistema de IA nuevo no va aquí: lo pregunta el inventario al darlo de alta.

## avisos

**Qué es:** lo que hay que atender: puntos vencidos, puntos que vencen pronto, recordatorios que tocan, la pregunta
«¿Ha pasado algo?» y sistemas nuevos con la pregunta de reabrir sin contestar.

- Están en la lista «Lo siguiente» de Inicio (no hay ventana aparte).
- Qué avisa se elige en Ajustes. Los recordatorios se marcan «Hecho».

## avisos-correo

**Qué es:** un correo y una notificación de Windows con lo pendiente, sin tener que abrir el portal.

- **Cuándo llega:** el **día 1 de cada mes**, el resumen del mes (lo mismo que los avisos del portal; si no hay nada,
  «Todo al día»). **Cada lunes**, lo ya vencido y lo que vence esa semana, de lunes a domingo (si no hay nada, «Esta
  semana no vence nada»). Si el día 1 es lunes, un solo correo. A las 9:00 o, si el ordenador estaba apagado, al
  encenderlo; si un lunes no se enciende, llega al día siguiente.
- **Funciona con el portal cerrado:** lo manda una tarea de Windows. Basta con que el ordenador se encienda.
- **Desde dónde:** el **Outlook clásico** de ese ordenador, con la cuenta elegida (sin contraseñas). El «nuevo
  Outlook» no sirve. Les llega a los destinatarios como un correo de quien tiene el portal.
- **Qué lleva:** solo códigos, títulos de requisitos, puntos y fechas. Nunca archivos, su contenido ni nombres de
  sistemas.
- **La notificación:** el recuadro de abajo a la derecha. Al pulsarla se abre Inicio; si el portal estaba apagado, se
  enciende (en una ventana minimizada; se apaga cerrándola o con `parar.bat`).
- **A quién:** a los usuarios de la empresa, cada uno con su casilla en Ajustes → «Avisos por correo»; vienen todos
  marcados (también los que se añadan después) y quien no los quiera se desmarca. Además se pueden escribir otros
  correos, de gente que no usa el portal.
- **Montarlo, una vez:** en Ajustes → «Avisos por correo», marcar la casilla, revisar a quién y desde qué cuenta, y
  Guardar. Después, doble clic en `programar-avisos.bat` (en la carpeta del portal). Para
  comprobarlo, «Mandar un aviso de prueba»: lo manda ya y no cuenta como el del día 1 ni el del lunes.
- **Vienen apagados:** quien se descarga el portal no tiene su correo conectado a nada hasta que los activa. Cada
  empresa tiene los suyos, y el asunto dice de qué empresa es («[Portal ISO 42001 · Mi empresa]»).
- **Si el correo no sale** (Outlook no está, la cuenta no existe…), queda en Actividad con el motivo y sale una
  notificación que lo dice.
- **Varios ordenadores con los avisos programados:** el primero que llega manda el aviso y lo apunta en el servidor;
  los demás ven que ya ha salido y no lo repiten. Por eso puede llegar desde la cuenta de uno u otro.
- **Quitarlos:** desmarcar la casilla en Ajustes. Para borrar también la tarea de Windows: Programador de tareas →
  «Portal ISO 42001 - avisos» → Eliminar.

## actividad

**Qué es:** el registro de todo lo que se hace en el portal (marcar, renovar, subir, quitar, decidir, retirar un
sistema, el cuestionario, las propuestas…), con fecha, hora y quién lo hizo, lo más reciente arriba. Se puede filtrar
por requisito y por persona. Los avisos que manda solo la tarea de Windows salen como «el portal».
Lo que se mete directamente en las carpetas desde el Explorador no sale aquí.

## ajustes

- **Qué avisa:** vencidos, vence pronto, recordatorios.
- **Avisos por correo:** activarlos, a quién, desde qué cuenta de Outlook y «Mandar un aviso de prueba» (ver
  avisos-correo).
- **Cada cuánto pregunta si ha pasado algo:** por defecto cada 4 meses; se puede quitar.
- **Revisión general:** cada cuánto vencen los puntos (por defecto cada año, antes de la auditoría anual).
- **Aspecto:** el tema (Automático, que sigue al de Windows; Claro; Oscuro). Se recuerda en ese ordenador.
- **Opciones avanzadas:** cuántos días antes avisa «vence pronto», la lista de los puntos cumplidos con cuándo vence
  cada uno (solo para consultarla: la fecha no se cambia a mano, se calcula desde que se cumplió o renovó), y en cada
  requisito si vence o no y su recordatorio.
- Si hay cambios respecto a lo recomendado, «Volver a los valores recomendados».

## buscador

La caja de arriba o **Ctrl K** desde cualquier página. Se escribe un código («7.2»,
«A.10») o palabras («riesgos», «proveedor»), sin preocuparse de tildes ni mayúsculas. Flechas para elegir, Intro para
ir, Esc para cerrar. Busca requisitos y puntos (no archivos).

## chat

El botón **«Preguntar»**, en la barra de arriba, abre un panel para
preguntar sobre la norma o sobre el portal. Sabe en qué página estás. Solo consulta: nunca marca, sube ni decide. Las
conversaciones no se guardan al cerrar el portal. Necesita Claude Code en el ordenador.

## carpetas

- En el portal de verdad, las pruebas están en la **carpeta compartida que elige cada ordenador**, con una carpeta dentro
  para cada empresa: `<carpeta>\<empresa>\pruebas\<requisito>\<punto>\` (por ejemplo `…\mi-empresa\pruebas\5.2\5.2.a\`).
  Puede ser, por ejemplo, una carpeta de Teams o SharePoint sincronizada con OneDrive: lo que subes tú, OneDrive lo
  lleva a Teams y a los ordenadores de los demás, y al revés. En el local, en la carpeta del portal: `datos\<empresa>\pruebas\…`. En los
  puntos por sistema, una subcarpeta por sistema. Las versiones anteriores, en `<requisito>\historial\`.
- **Elegir la carpeta, una vez por ordenador:** al entrar, antes de elegir empresa, el portal pregunta «¿Dónde se
  guardan los archivos de pruebas?». **Examinar…** abre la ventana de Windows para elegirla (o se pega su ruta) y
  **Usar esta carpeta** la apunta. Vale para todas las empresas: se elige la de arriba, la que tiene dentro una carpeta
  para cada una (por ejemplo, `empresa-a` y `empresa-b`), no la de una empresa; si se elige la de una, el portal lo
  dice. Tiene que ser la misma en todos los ordenadores. Se guarda en los ajustes de tu usuario de Windows (`AppData`),
  no en la carpeta del programa: al actualizar el portal no vuelve a preguntar. Si un día la carpeta no está (se movió
  o se dejó de sincronizar), lo dice y la vuelve a pedir.
- **Sincronizar una carpeta de Teams, una vez por ordenador:** en Teams, el canal → pestaña «Compartido» (o
  «Archivos») → «Abrir en SharePoint» → «Sincronizar», y aceptar abrir OneDrive (si ofrece copia de seguridad del
  Escritorio o de Documentos, «Omitir»). Después, elegirla en el portal.
- **El aviso de «revisión de una versión anterior»** mira el nombre y el tamaño de los archivos, no la fecha: OneDrive
  cambia a veces la fecha sin que nadie toque el archivo.
- **La primera vez,** el portal crea unas 160 carpetas por empresa: mejor que lo arranque una sola persona y esperar a
  que OneDrive las suba antes de que lo abra otra (si dos las crean a la vez, OneDrive puede duplicar alguna).
- En el Explorador y en Teams se ven las carpetas de **todas** las empresas del canal, aunque en el portal cada uno vea
  solo las suyas.
- **La carpeta manda:** lo que se meta desde el Explorador también sale en el portal.
- La carpeta de un control que no aplica se llama «… (no aplica)».
- Nada de esto se sube a git: son datos de la empresa.

## arrancar

- **`arrancar.bat`** (doble clic): arranca el portal y lo abre en el navegador (http://localhost:8000). Cerrar su
  ventana negra lo apaga. Necesita Python; si no está, lo dice y abre la página de descarga.
- **La primera vez (la instalación):** el portal explica los dos modos y se elige uno:
  - **Solo en este ordenador:** sin instalar nada más. Se elige dónde van los datos (por defecto,
    `Documentos\Portal ISO 42001`), se crea la cuenta y la primera empresa, y se entra.
  - **Compartido con mi equipo:** los datos en un MySQL y los archivos en una carpeta compartida. Se escriben los datos
    del MySQL (**Probar conexión** dice si funcionan), se elige la carpeta (ver «carpetas») y, si eres el primero, se crea
    la cuenta y la primera empresa. Si el MySQL ya tiene cuentas, te unes a un equipo que ya existe: no se crea nada y se
    entra con la cuenta que te haya hecho quien lo administra.
- **Lo elegido se guarda en tu usuario de Windows** (`AppData\Roaming\Portal ISO 42001`: `ajustes.json` y, en el
  compartido, `secretos.env` con los datos del MySQL), fuera de la carpeta del programa: al actualizar el portal no
  vuelve a preguntar. Los portales de antes (con `secretos.env` en la carpeta del programa) se reconocen solos y entran
  como siempre.
- **`arrancar-local.bat`**: el portal **local**, todo en tu ordenador (carpeta `datos`), sin el servidor ni internet
  (http://localhost:8002), con «LOCAL» en la cabecera. Puede estar encendido a la vez que el de verdad.
- **`parar.bat`**: apaga el portal, el de prueba y el local, aunque sus ventanas no estén a la vista.
- **`arrancar-prueba.bat`**: un portal aparte con datos inventados (http://localhost:8001, carpeta `datos-prueba`),
  con «PRUEBA» en la cabecera. Pregunta si empezar de cero. No toca los datos de verdad. Se entra con
  `prueba@ejemplo.com` y la contraseña `prueba`; para crear más cuentas o empresas en él, `scripts\cuentas.py --prueba`.
- **Importar el portal de otra persona** (su `portal.db` y su carpeta de pruebas, aunque sea de una versión anterior):
  `python scripts\importar.py PORTAL.DB CARPETA "EMPRESA" --quien "NOMBRE"`. La empresa tiene que existir y estar
  vacía; va al MySQL y a la carpeta de los archivos elegida en tu ordenador (con `--local`, al portal local). Lo que no dice quién lo hizo queda a
  nombre de NOMBRE. El original no se toca.

## conceptos

- **Cumplido:** un punto marcado (o que se cumple solo) y no vencido.
- **Completo:** un requisito con todos sus puntos obligatorios cumplidos.
- **Vence / vence pronto / vencido:** cuándo hay que volver a revisar algo; vencido ya no cuenta.
- **Por evento:** no vence por fecha; se reabre cuando pasa algo.
- **Apoyado:** se cumple solo al completar otros requisitos.
- **Recomendado:** buena práctica, no exigible; no cuenta en el porcentaje.
- **No aplica:** un control del Anexo A que la empresa excluye, con su porqué, en la Declaración.
- **Recordatorio:** un aviso intermedio para ir haciendo algo durante el año; no cambia el estado de nada.
