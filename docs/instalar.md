# Instalar y mantener el portal ISO/IEC 42001

Cómo poner el portal en marcha en tu ordenador, cómo conectarlo con tu equipo y cómo cuidarlo después (copias de
seguridad, actualizar, problemas). Para usarlo, pantalla a pantalla, está el [manual de uso](manual.md).

Si algo de aquí te suena demasiado técnico (MySQL, puerto, servidor…), no hace falta que lo entiendas todo: en esos
apartados se dice qué pasarle a tu informático.

**Si tienes Claude Code** (ver [Opcional: la IA (Claude)](#opcional-la-ia-claude)), te puede acompañar paso a paso:
ábrelo en la carpeta del programa y escribe «ayúdame a instalar el portal». Te pregunta qué quieres hacer, comprueba lo
que puede (Python, si se llega al MySQL) y te guía en el resto, también a montar el MySQL en Amazon, Microsoft, Google o
un servidor vuestro. No crea nada por ti ni te pide contraseñas: esas se escriben en el portal. Sin Claude Code, este
manual basta.

## Índice

1. [Qué necesitas](#qué-necesitas)
2. [Descargar y arrancar](#descargar-y-arrancar)
3. [Elegir cómo lo vas a usar](#elegir-cómo-lo-vas-a-usar)
4. [Solo en este ordenador](#solo-en-este-ordenador)
5. [Compartido con tu equipo](#compartido-con-tu-equipo)
6. [El MySQL: qué pedir](#el-mysql-qué-pedir)
7. [La carpeta de los archivos](#la-carpeta-de-los-archivos)
8. [Opcional: la IA (Claude)](#opcional-la-ia-claude)
9. [Opcional: los avisos por correo (Outlook)](#opcional-los-avisos-por-correo-outlook)
10. [Copias de seguridad](#copias-de-seguridad)
11. [Actualizar a una versión nueva](#actualizar-a-una-versión-nueva)
12. [Si el administrador olvida su contraseña](#si-el-administrador-olvida-su-contraseña)
13. [Si algo no funciona](#si-algo-no-funciona)
14. [Seguridad](#seguridad)
15. [Aviso legal](#aviso-legal)

---

## Qué necesitas

- **Un ordenador con Windows** (10 u 11). En Mac y Linux no funciona: el arranque, los avisos por correo y las
  notificaciones son de Windows.
- **Python**, el lenguaje en el que está hecho el portal. Es gratis. Si no lo tienes, el portal lo dice la primera vez
  y abre la página de descarga (ver [Descargar y arrancar](#descargar-y-arrancar)).
- **Internet la primera vez**, para que el portal se descargue las piezas que necesita. Después, en el modo «solo en
  este ordenador», funciona sin internet.
- **Solo si lo compartes con tu equipo:** una base de datos MySQL y una carpeta compartida (ver
  [Compartido con tu equipo](#compartido-con-tu-equipo)).
- **Opcional:** Claude Code, para las ayudas con IA, y el Outlook clásico, para los avisos por correo. Sin ellos, todo
  lo demás funciona igual.

## Descargar y arrancar

1. **Descarga el portal.** En la página del repositorio en GitHub, botón verde **«Code» → «Download ZIP»**.
2. **Descomprímelo** en una carpeta tuya, por ejemplo `C:\Portal ISO 42001`. Esta es la **carpeta del programa**. Tus
   datos no van aquí: van en otra carpeta, para que actualizar o borrar el programa no los toque.
3. **Haz doble clic en `arrancar.bat`**, dentro de esa carpeta.
   - Si sale un aviso azul, «Windows protegió su PC», pulsa «Más información» → «Ejecutar de todas formas». Pasa con
     los programas descargados de internet que no llevan firma de una empresa.
   - **Si no tienes Python,** se abre su página de descarga. Instala la última versión y, en la primera pantalla del
     instalador, **marca «Add python.exe to PATH»** (si no, el portal no lo encuentra). Después, vuelve a hacer doble
     clic en `arrancar.bat`.
   - **La primera vez tarda un par de minutos:** prepara lo que necesita. Las siguientes, unos segundos.
4. **Se abre una ventana negra y el navegador** con el portal. La ventana negra es el portal funcionando: **no la
   cierres mientras lo uses**. Al cerrarla, el portal se apaga. El portal funciona solo en tu ordenador, aunque se vea
   en el navegador: no está en internet.

La primera vez, el portal te enseña la instalación: un par de pantallas para elegir cómo lo vas a usar y crear tu
cuenta.

Para apagarlo, cierra la ventana negra o haz doble clic en `parar.bat`.

## Elegir cómo lo vas a usar

La primera pantalla te deja elegir entre dos formas. Las dos tienen el mismo portal; cambia dónde se guardan los datos y
quién puede entrar.

| | Solo en este ordenador | Compartido con tu equipo |
|---|---|---|
| **Dónde están los datos** | En una carpeta de tu ordenador | En una base de datos MySQL; los archivos, en una carpeta compartida |
| **Qué hay que instalar** | Nada más | El MySQL, una vez para todo el equipo |
| **Quién entra** | Quien use este ordenador | Todo el equipo, cada uno desde su ordenador y con su cuenta |
| **Para quién** | Para empezar, o si lo llevas tú solo | Si sois varios |

Lo que elijas se guarda en tu ordenador, fuera de la carpeta del programa. Así, al actualizar, no vuelve a
preguntar.

## Solo en este ordenador

1. Pulsa **«Usarlo solo en este ordenador»**.
2. **¿Dónde se guardan los datos?** Por defecto, en `Documentos\Portal ISO 42001`. Si no sabes cuál elegir, deja esa.
   Ahí van todo lo que rellenes y los archivos de pruebas.
3. **Tu cuenta y tu empresa:** el nombre de la empresa, tu nombre, tu correo y una contraseña (al menos 8 caracteres).
   Con el correo y la contraseña entrarás cada vez.
4. **«Crear y entrar».** Ya estás dentro: el portal te lleva al cuestionario de tu empresa, unas preguntas para
   empezar.

Tu cuenta es la de **administrador**: puedes crear más cuentas y empresas desde «Administrar», arriba a la derecha (ver
el [manual de uso](manual.md), apartado «entrar»).

## Compartido con tu equipo

**Si eres el primero del equipo:**

1. Consigue el MySQL (ver [El MySQL: qué pedir](#el-mysql-qué-pedir)) y la carpeta compartida (ver
   [La carpeta de los archivos](#la-carpeta-de-los-archivos)).
2. En el portal, pulsa **«Compartirlo con mi equipo»**.
3. **¿Cuál es vuestro MySQL?** Escribe los datos que te ha dado quien lo montó: la dirección del servidor, el puerto,
   el usuario y la contraseña del MySQL (no son los tuyos del portal) y el nombre de la base de datos. Pulsa
   **«Probar conexión»**: dice si funcionan y, si no, por qué.
4. **La carpeta de los archivos:** pulsa «Examinar…» y elígela.
5. **Tu cuenta y tu empresa,** como en el modo «solo en este ordenador». Tu cuenta es la de administrador.
6. Crea las cuentas de los demás en **«Administrar»** y pásales a cada uno su correo y su contraseña, y también los
   datos del MySQL (de forma segura, ver [Seguridad](#seguridad)).

**Si tu equipo ya lo usa:**

1. Pide a quien lo administre los datos del MySQL y tu cuenta (correo y contraseña).
2. Descarga y arranca el portal en tu ordenador. Pulsa **«Compartirlo con mi equipo»** y escribe los datos del MySQL.
3. Elige la carpeta de los archivos: la misma que usa el equipo, sincronizada en tu ordenador. El portal ya sabe que
   tu equipo lo usa y te avisa de que es el último paso: no crea nada.
4. Te lleva a «Entrar», con el aviso «Listo: el portal ya está conectado con el de tu equipo». Entra con tu correo y
   tu contraseña.

Los datos del MySQL se guardan en tu ordenador, en un archivo que solo usa el portal. No hace falta abrirlo ni
tocarlo.

## El MySQL: qué pedir

El MySQL es la base de datos donde el portal guarda lo que rellena el equipo (cuentas, empresas, seguimiento,
Declaración…), para que todos vean lo mismo. Funciona como un archivador central: cada ordenador consulta y guarda en
él. Se monta **una vez para todo el equipo**. Si no sabes montarlo, pídeselo a tu informático o a quien lleve vuestros
servidores, con esta lista.

**Qué tiene que tener:**

- **MySQL 5.7 u 8.** El portal está probado con la 5.7.
- **Que se pueda llegar desde el ordenador de cada persona del equipo,** también desde fuera de la oficina si alguien
  trabaja desde casa o con los datos del móvil. Si el servidor solo deja entrar desde ciertas redes (es lo normal, y es
  más seguro), hay que añadir las de cada uno o usar una VPN (una conexión que hace que tu ordenador esté «dentro» de la
  red de la oficina aunque estés fuera).
- **Una base de datos vacía** para el portal. Las tablas las crea el portal solo, la primera vez.
- **Un usuario para el portal** con permisos solo sobre esa base: leer, guardar, cambiar y borrar datos, y crear y
  cambiar tablas.

**Para quien lo monte,** esto es lo que hace falta, en el lenguaje del MySQL (cambia el nombre de la base, el del
usuario y la contraseña por los vuestros):

```sql
CREATE DATABASE iso42001 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'portal'@'%' IDENTIFIED BY 'una-contraseña-larga';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, REFERENCES ON iso42001.* TO 'portal'@'%';
```

**Qué datos te tiene que dar** (los escribirás en la instalación):

| Dato | Qué es | Ejemplo |
|---|---|---|
| Dirección del servidor | Dónde está el MySQL | `mibase.eu-west-1.rds.amazonaws.com` |
| Puerto | La «puerta» por la que se entra | `3306` (el de siempre del MySQL) |
| Usuario | Con qué usuario entra el portal | `portal` |
| Contraseña | La de ese usuario | |
| Base de datos | El nombre de la base vacía | `iso42001` |

Dónde montarlo es cosa vuestra: un servidor de la empresa o uno en la nube (Amazon, Google, Microsoft y otros los
alquilan ya montados). Tiene que estar encendido siempre que alguien use el portal.

## La carpeta de los archivos

En el modo compartido, los archivos de pruebas (las evidencias de cada requisito) van en una **carpeta compartida**, para
que todo el equipo vea los mismos. Por ejemplo:

- una carpeta de **Teams o SharePoint sincronizada con OneDrive** (en Teams: el canal → «Archivos» → «Abrir en
  SharePoint» → «Sincronizar»);
- una **carpeta de red** de la empresa.

**Cada persona la elige una vez en su ordenador**, durante la instalación. Tiene que ser la misma carpeta para todos.
Elige la carpeta general del equipo para la ISO (por ejemplo, «ISO 42001»), no la de una empresa: dentro, el portal crea
una carpeta para cada empresa. Si un día el portal no la encuentra (se ha movido o ha dejado de sincronizarse), te la
vuelve a pedir.

**La primera vez,** el portal crea unas 160 carpetas por empresa. Si es una carpeta sincronizada, mejor que arranque
una sola persona y esperar a que se suban antes de que entre otra: si dos las crean a la vez, el programa de
sincronización puede duplicar alguna.

En el modo «solo en este ordenador», los archivos van en la carpeta de datos que elegiste y no hay que hacer nada.

## Opcional: la IA (Claude)

El portal puede ayudarse de Claude, la IA de Anthropic, para:

- **revisar archivos:** decir si lo que has subido cumple un punto;
- **proponer** si aplica cada control de la Declaración de Aplicabilidad y redactar el porqué;
- **redactar borradores** de los documentos que pide la norma;
- **preparar el borrador de la revisión por la dirección;**
- el **chat** («Preguntar»), para preguntar sobre la norma o sobre el portal.

**Qué hace falta:** tener instalado **Claude Code** en tu ordenador y haber entrado con tu cuenta de Claude. El portal
usa tu sesión de Claude, es decir, tu suscripción: no hay que poner ninguna clave en el portal. Cada persona del equipo
usa la suya.

1. Instala Claude Code siguiendo las instrucciones de su página oficial: <https://claude.com/claude-code>.
2. Ábrelo una vez y entra con tu cuenta.
3. Vuelve a arrancar el portal.

**Qué sale de tu ordenador:** cuando usas una de estas ayudas, el portal le pasa a Claude lo que necesita para esa
tarea (por ejemplo, el texto del archivo que revisas o las respuestas del cuestionario). Nada más, y solo cuando tú
pulsas el botón.

**Sin Claude:** los botones de IA dicen que no está disponible. Todo lo demás funciona igual.

## Opcional: los avisos por correo (Outlook)

El portal puede mandar un correo y una notificación de Windows con lo pendiente: el día 1 de cada mes y cada lunes, con
el portal cerrado.

**Qué hace falta:** el **Outlook clásico** (el programa de escritorio de siempre) instalado y con tu cuenta de correo
puesta. El «nuevo Outlook» no sirve. El correo sale de tu cuenta, sin escribir contraseñas en el portal.

1. En el portal, **Ajustes → «Avisos por correo»**: marca la casilla, revisa a quién y desde qué cuenta, y guarda.
2. Haz doble clic, una vez, en **`programar-avisos.bat`** (en la carpeta del programa). Crea la tarea de Windows que los
   manda.
3. Para comprobarlo: **«Mandar un aviso de prueba»**, en el mismo sitio.

**Sin Outlook:** no hay avisos por correo. Los avisos dentro del portal («Lo siguiente», en Inicio) funcionan igual.

## Copias de seguridad

El portal no hace copias solo. Hazlas tú, cada cierto tiempo (por ejemplo, una vez al mes y antes de actualizar).

**Solo en este ordenador:**

1. Apaga el portal (cierra la ventana negra o `parar.bat`).
2. Copia **la carpeta de datos** entera (por defecto, `Documentos\Portal ISO 42001`) a otro sitio: un disco externo, una
   carpeta en la nube…
3. Para recuperarla: apaga el portal y pon la copia en su sitio, con el mismo nombre.

**Compartido con tu equipo:** hay dos cosas que copiar.

- **El MySQL:** pide a quien lo lleve que tenga copias automáticas. Los servicios en la nube suelen hacerlas solos; en
  un servidor propio, tu informático sabrá cómo (con la herramienta de copias del MySQL).
- **La carpeta de los archivos:** si es de Teams, SharePoint o una carpeta de red, normalmente ya guardan versiones
  anteriores. Si no, cópiala como la del modo «solo en este ordenador».

**Los ajustes de tu ordenador** (el modo, la carpeta elegida y los datos del MySQL) no hace falta copiarlos: si se
pierden, el portal vuelve a preguntar.

## Actualizar a una versión nueva

Tus datos no están en la carpeta del programa, así que actualizar es cambiar esa carpeta por la nueva:

1. **Haz una copia de seguridad** (ver arriba).
2. **Apaga el portal** (cierra la ventana negra o `parar.bat`).
3. **Descarga el ZIP** de la versión nueva.
4. **Cambia el nombre de la carpeta del programa** a «Portal antiguo» y descomprime la nueva en el mismo sitio, con
   el nombre que tenía la antigua. Tus datos no están en la carpeta del programa (están en la carpeta de datos o en el
   MySQL), así que no se pierden. Cuando compruebes que la nueva funciona, borra «Portal antiguo».
5. **Doble clic en `arrancar.bat`.** La primera vez tarda un par de minutos, como al instalar. No vuelve a preguntar
   nada: entras con tu cuenta y está todo.

Al arrancar, el portal pone al día la base de datos él solo: añade lo que le falte y no borra nada.

**En el modo compartido, que actualice todo el equipo,** cada uno en su ordenador. Si uno usa una versión más antigua
que los demás, puede que algo nuevo no le funcione.

Si habías programado los avisos por correo y pones el programa en otra carpeta, vuelve a hacer doble clic en
`programar-avisos.bat`: la tarea de Windows busca el programa donde estaba.

## Si el administrador olvida su contraseña

Si alguien olvida su contraseña, el administrador le pone otra desde «Administrar». Si quien la olvida es el
administrador, y no hay otro administrador que se la cambie:

1. En la carpeta del programa, haz doble clic en `olvide-contrasena.bat`. Se abre una ventana negra.
2. Escribe tu correo y pulsa Enter.
3. Escribe la contraseña nueva y pulsa Enter; después, otra vez. Lo que escribes no se ve en pantalla: es normal.
4. Si pone «Contraseña de … cambiada», ya puedes entrar con ella. Pulsa una tecla para cerrar la ventana.

Funciona con el portal de ese ordenador: el MySQL si es compartido (tiene que llegar a él, como el portal), o su
carpeta de datos si es «solo en este ordenador».

Borrar una empresa tampoco se hace desde el portal, porque se lleva todos sus datos. (Cambiarle el nombre, sí: en
«Administrar».) Se hace con el programa de cuentas, escribiendo una orden: si no te manejas con esto, pídele a tu informático que lo haga contigo. En
la carpeta del programa, haz clic en la barra de la dirección (arriba), escribe `cmd` y pulsa Enter; en la ventana
negra, `.venv\Scripts\python scripts\cuentas.py --help` enseña todo lo que puede hacer.

## Si algo no funciona

**«El portal necesita Python»:** instálalo como se explica en [Descargar y arrancar](#descargar-y-arrancar), marcando
«Add python.exe to PATH». Si ya lo instalaste sin marcarlo, vuelve a abrir el instalador de Python, elige «Modify» y
márcalo.

**«Ya hay un portal encendido»:** hay otro abierto, quizá en una ventana que no ves. Haz doble clic en `parar.bat` y
vuelve a arrancar.

**El portal no se abre porque otro programa ocupa su «puerto»** (la puerta por la que el navegador habla con el
portal; el del portal es el 8000). Pásale esto a tu informático: en una ventana `cmd` en la carpeta del programa,
`set PORTAL_PUERTO=8010` y, después, `arrancar.bat`.

**«Sin conexión» (modo compartido):** el portal no llega al MySQL. Tarda unos segundos en decirlo, porque espera a que
el servidor conteste. Comprueba, por orden:

1. **Que tienes internet.**
2. **Que el servidor está encendido:** pregunta a quien lo lleve, o a un compañero si a él le funciona.
3. **Que el servidor deja entrar desde tu red.** Es lo más frecuente cuando funciona en la oficina y no en casa o con
   los datos del móvil (o al revés). Pásale esto a tu informático: en PowerShell (en el menú Inicio), con la dirección
   de vuestro servidor,

   ```
   Test-NetConnection mibase.ejemplo.com -Port 3306
   ```

   Si al final dice `TcpTestSucceeded : False`, desde esta red no se llega. Pide a quien lleve el servidor que añada tu
   red, o usa la VPN de la empresa.
4. **Que los datos del MySQL no han cambiado.** Si tu equipo ha cambiado la contraseña del MySQL o su dirección, pulsa
   **«Cambiar los datos del MySQL»** en la misma pantalla de «Sin conexión», escribe los nuevos y «Guardar y entrar».
   Vienen los de ahora, salvo la contraseña. No se pierde nada: los datos del portal están en el MySQL.

**El portal pide la carpeta de los archivos otra vez:** no encuentra la que elegiste. Puede que se haya movido, que se
haya dejado de sincronizar o que la unidad de red no esté conectada. Si vuelve a estar, pulsa «Usar esta carpeta»; si
no, elige dónde está ahora.

**Los botones de IA dicen que no está disponible:** ver [Opcional: la IA (Claude)](#opcional-la-ia-claude).

**El correo de aviso no sale:** queda apuntado en «Actividad» con el motivo. Lo normal es que no haya Outlook clásico o
que la cuenta elegida no esté en ese Outlook.

## Seguridad

- **Los datos del MySQL dan acceso a todo.** Quien los tenga puede entrar en la base de datos directamente, sin pasar
  por el portal, y cambiar cuentas, contraseñas o datos de las empresas. «Administrar» solo controla lo que se hace
  dentro del portal. Dáselos solo a gente de confianza del equipo, y nunca por un canal abierto (un correo a mucha gente,
  un chat público).
- **Que el MySQL solo deje entrar desde vuestras redes** (ver [El MySQL: qué pedir](#el-mysql-qué-pedir)), y con un
  usuario que solo tenga permisos sobre la base del portal.
- **Si alguien deja el equipo,** quítale la cuenta en «Administrar». Si tenía los datos del MySQL, cambiad la contraseña
  del usuario del MySQL y escribid la nueva en cada ordenador: al arrancar, el portal dirá «Sin conexión»; pulsa
  **«Cambiar los datos del MySQL»**, escribe la contraseña nueva y **«Guardar y entrar»**. No se pierde nada.
- **En el modo «solo en este ordenador»,** los datos están en una carpeta normal de tu ordenador: quien entre con tu
  usuario de Windows puede verlos.
- **El portal solo se ve desde tu ordenador:** no se abre a la red ni a internet.

## Aviso legal

Desarrollado en Movired.

El portal tiene una **licencia de uso interno** (PolyForm Internal Use 1.0.0). En resumen:

- **Puedes** usarlo y modificarlo para el trabajo interno de tu empresa; todos los que trabajan en ella pueden usarlo.
- **No puedes** pasarle una copia a otra empresa ni a nadie de fuera: quien lo quiera, que lo descargue del repositorio
  de GitHub.
- **Tampoco puedes** venderlo, ofrecerlo como servicio a otros ni instalarlo a un cliente.

Esto es un resumen: el texto que vale es el del fichero `LICENSE`, en inglés. También se ve en el portal, en el enlace
«Licencia de uso interno» del pie de cada pantalla.

- El portal ayuda a llevar al día el sistema de gestión de la IA según la norma ISO/IEC 42001, pero **no certifica
  nada** ni sustituye a la norma, a una auditoría ni al consejo de un experto. La guía que trae explica los requisitos
  con palabras propias; para la certificación hace falta la norma original.
- ISO/IEC 42001 es una norma de ISO e IEC. Este portal no está relacionado con esas organizaciones ni respaldado por
  ellas.
- Lo que redacta la IA son **borradores**: revísalos antes de usarlos.
- Se ofrece tal cual, sin garantías. Haz copias de seguridad.
- **Si ves el portal a la venta**, ofrecido como servicio o instalado a clientes, avísanos: [pauaracil@mvdataworks.com](mailto:pauaracil@mvdataworks.com).
