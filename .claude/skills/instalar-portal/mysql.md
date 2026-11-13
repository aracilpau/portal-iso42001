# Montar el MySQL del portal, según dónde

Lo común a todos los sitios está en el manual, «El MySQL: qué pedir»: MySQL 5.7 u 8, una base vacía, un usuario solo
para el portal con permisos sobre esa base, y que se llegue desde el ordenador de cada persona del equipo. Aquí, cómo se
consigue en cada sitio.

**Cómo guiar:** un paso cada vez. Di qué hay que elegir y cómo suele llamarse la opción; si la persona no la encuentra,
que busque en la ayuda de esa nube con las palabras que le das. No des precios: que mire la página de precios de cada
nube antes de crear nada (crear un servidor en la nube puede costar dinero cada mes, aunque no se use). Lo crea la
persona, no tú.

## Lo mismo en cualquier sitio

- **El tamaño más pequeño basta.** El portal guarda poco y lo usan pocas personas. Si hay opción gratuita o de pruebas,
  vale para empezar; si no, la más pequeña.
- **Una región cercana** (en Europa, una europea), por velocidad y por dónde quedan los datos.
- **Copias automáticas activadas.** Casi siempre vienen así; que lo compruebe.
- **Quién puede entrar:** solo desde las redes del equipo. Cada nube tiene una lista de direcciones de internet («IP»)
  permitidas. La IP de su conexión la puede ver buscando «cuál es mi IP» en el navegador; muchas nubes tienen un botón
  «Mi IP» o «Añadir mi IP». Hay que añadir la de cada sitio desde donde se trabaje (oficina, casa…). Dejarlo abierto a
  todo internet («0.0.0.0/0») funciona pero no es seguro: desaconséjalo.
- **La contraseña del administrador del MySQL** (la que pide la nube al crearlo) no es la del portal: con ella se crea
  después el usuario `portal`. Que la guarde en un sitio seguro.
- **Crear la base y el usuario del portal:** con las órdenes del manual (las preparas tú, sin contraseña). Para
  ejecutarlas hace falta un programa que hable con el MySQL: el más sencillo es **MySQL Workbench** (gratis, de la web
  de MySQL), conectándose con la dirección, el puerto y el administrador. Algunas nubes tienen su propia consola, que se
  dice abajo.
- **La dirección del servidor** es la que el portal pide como «Dirección del servidor». Cada nube la llama de una forma
  (abajo).

## Amazon (AWS): Amazon RDS for MySQL

1. En la consola de AWS, el servicio **RDS** → «Create database».
2. Motor **MySQL**. Plantilla **«Free tier»** si sale, o «Dev/Test».
3. Un nombre para el servidor, el usuario administrador («master username») y su contraseña.
4. Tamaño: la clase más pequeña que ofrezca (las «micro»). Almacenamiento: el mínimo.
5. **Conectividad:** «Public access» en **Yes** (si el equipo no tiene VPN con AWS). En el «security group» (la lista de
   quién puede entrar), una regla de entrada **MySQL/Aurora, puerto 3306**, con la IP de cada sitio («My IP» añade la
   suya).
6. Crear y esperar unos minutos a que esté «Available».
7. **La dirección** es el «Endpoint», en «Connectivity & security».
8. La base y el usuario: con MySQL Workbench y el usuario administrador.

## Microsoft (Azure): Azure Database for MySQL – Flexible Server

1. En el portal de Azure, crear **«Azure Database for MySQL Flexible Server»**.
2. Tipo de uso para desarrollo o proyectos pequeños; tamaño **«Burstable»**, el más pequeño.
3. Usuario administrador y contraseña.
4. **Redes:** «Acceso público» y, en las reglas del firewall, la IP de cada sitio («Agregar la dirección IP del cliente
   actual» añade la suya).
5. **La dirección** es el «Nombre del servidor» (termina en `.mysql.database.azure.com`).
6. La base y el usuario: con MySQL Workbench. La base también se puede crear en «Bases de datos» del propio servidor.

## Google Cloud: Cloud SQL for MySQL

1. En la consola de Google Cloud, **Cloud SQL** → «Crear instancia» → **MySQL**.
2. La edición y el ajuste más pequeños (los de desarrollo o «sandbox»), con una máquina de núcleo compartido.
3. Contraseña del usuario `root` (el administrador).
4. **Conexiones:** «IP pública» activada y, en «Redes autorizadas», la IP de cada sitio.
5. **La dirección** es la «Dirección IP pública» de la instancia.
6. La base se puede crear en la pestaña «Bases de datos» y el usuario en «Usuarios», pero los permisos justos se dan
   mejor con las órdenes del manual: desde MySQL Workbench o desde Cloud Shell (`gcloud sql connect <instancia>
   --user=root`).

## Un servidor o un hosting que ya tengáis

- **Un servidor de la empresa:** que el informático ejecute las órdenes del manual. Para que se llegue desde fuera:
  que el MySQL escuche en la red (no solo en el propio servidor) y que el cortafuegos deje pasar el puerto 3306 desde
  las redes del equipo, o que se entre por la VPN.
- **Un hosting con panel (cPanel, Plesk…):** en «Bases de datos MySQL» se crean la base, el usuario y se le dan
  permisos a la base. Para entrar desde fuera suele haber un «MySQL remoto» donde se añaden las IP permitidas. **Ojo:**
  muchos hostings compartidos no dejan entrar desde fuera; si no sale esa opción, que pregunte al proveedor.
- La dirección es el nombre o la IP del servidor que dé el informático o el proveedor (en un hosting, a veces no es el
  mismo nombre que la web).

## Comprobar

Con la dirección, `Test-NetConnection <dirección> -Port 3306` desde su ordenador. `TcpTestSucceeded : True`: se llega,
y lo siguiente es la pantalla de instalación del portal, donde «Probar conexión» comprueba el usuario y la contraseña.
`False`: no deja entrar desde esta red; revisa la lista de IP permitidas.
