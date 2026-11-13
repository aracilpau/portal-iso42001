# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Los datos de la guía ISO/IEC 42001: requisitos, puntos, ayuda de aplicabilidad y glosario.

Es la única fuente de la guía. La leen el portal y scripts/generar_requisitos.py (que dibuja el
Excel). Para cambiar la guía se cambian los datos aquí.
"""

# Ejes 2 y 3: D=documento, R=registro, I=inventario, P=práctica | Pe=periódico, Ev=por evento, U=una vez y revisar
# (código, bloque, título, resumen, tipos, dudoso, notas)
C = [
    ("4.1", "4 Contexto", "Contexto de la organización", "Identificar qué factores internos y externos afectan al uso de la IA en la empresa y qué papel tiene con la IA (la desarrolla, la integra en su producto o la usa).", "D U", False, "La norma no exige tenerlo por escrito, pero es muy recomendable: el auditor lo pedirá y otros requisitos se comparan con él (p. ej. la política)."),
    ("4.2", "4 Contexto", "Partes interesadas", "Saber a quién afecta el sistema (clientes, empleados, proveedores, reguladores…), qué esperan y cuáles de esas expectativas se asumen.", "D U", False, "La norma no exige tenerlo por escrito, pero una tabla basta para demostrarlo."),
    ("4.3", "4 Contexto", "Alcance del sistema de gestión", "Fijar qué entra y qué no en el sistema de gestión de la IA (áreas, sistemas, sedes). Debe estar por escrito.", "D U", False, ""),
    ("4.4", "4 Contexto", "Sistema de gestión de la IA", "Montar, mantener y mejorar el sistema de gestión según la norma.", "S", False, "Es la unión de todos los demás requisitos: se cumple cumpliéndolos. No es una tarea: en el portal será el indicador general de cumplimiento."),
    ("5.1", "5 Liderazgo", "Liderazgo y compromiso", "La dirección se implica: alinea la IA con la estrategia, da recursos y apoya la mejora.", "P Pe", False, "El auditor pregunta a la dirección. Casi todas las pruebas son documentos de otros requisitos."),
    ("5.2", "5 Liderazgo", "Política de IA", "La dirección aprueba una política de IA adecuada a la empresa, con compromisos de cumplir y de mejorar; escrita y comunicada.", "D U", False, "Se revisa según A.2.4."),
    ("5.3", "5 Liderazgo", "Roles, responsabilidades y autoridades", "La dirección asigna y comunica quién es responsable de qué en el sistema de gestión.", "D U", False, ""),
    ("6.1.1", "6 Planificación", "Riesgos y oportunidades: generalidades", "Detectar los riesgos y oportunidades del propio sistema de gestión (no de cada sistema de IA), fijar cuándo un riesgo de IA es aceptable y planificar acciones.", "D U", False, ""),
    ("6.1.2", "6 Planificación", "Proceso de evaluación de riesgos de IA", "Definir cómo se evalúan los riesgos de la IA (criterios, método) para que los resultados sean coherentes y comparables.", "D U", False, "Aquí se define el proceso; hacerlo es 8.2."),
    ("6.1.3", "6 Planificación", "Proceso de tratamiento de riesgos de IA", "Definir cómo se trata cada riesgo, elegir los controles necesarios comparándolos con el Anexo A y redactar la Declaración de Aplicabilidad (qué controles del Anexo A aplican y por qué).", "D U", False, "De aquí nace la Declaración de Aplicabilidad. Aplicarlo es 8.3."),
    ("6.1.4", "6 Planificación", "Proceso de evaluación de impacto de la IA", "Definir cómo se evalúa el impacto de los sistemas de IA en personas, grupos y sociedad.", "D U", False, "Aquí se define el proceso; hacerlo es 8.4."),
    ("6.2", "6 Planificación", "Objetivos de IA", "Fijar objetivos medibles alineados con la política, hacerles seguimiento, comunicarlos y actualizarlos.", "D Pe", False, ""),
    ("6.3", "6 Planificación", "Planificación de cambios", "Cuando haya que cambiar el sistema de gestión (el responsable, el alcance, la política, un proceso…), hacerlo de forma planificada. No se refiere a los cambios del software.", "R Ev", False, "Solo cambios del propio sistema de gestión (responsable, alcance, política, procesos), no del software. Casi todo lo cubren 9.3 y 7.5; lo propio es un plan breve en los cambios grandes."),
    ("7.1", "7 Soporte", "Recursos", "Dar los recursos necesarios (personas, tiempo, presupuesto, herramientas) para el sistema de gestión.", "P Pe", False, "Son los recursos del sistema de gestión (tiempo de personas, dinero, herramientas), no los de cada sistema de IA (eso es A.4). La mejor prueba es que las tareas vayan al día."),
    ("7.2", "7 Soporte", "Competencia", "Asegurar que quien trabaja en el sistema está capacitado y guardar pruebas de ello.", "R Pe Ev", False, "Salta por evento con cada incorporación o cambio de puesto."),
    ("7.3", "7 Soporte", "Concienciación", "Que el personal conozca la política de IA, su papel y qué pasa si no se cumple.", "P Pe Ev", False, "El auditor pregunta a empleados al azar. Es informar a todos, no formar a quienes tienen un papel (eso es 7.2). Suele bastar una sesión corta al aprobar la política, a cada incorporación y cada año, con registro de asistencia."),
    ("7.4", "7 Soporte", "Comunicación", "Decidir qué se comunica sobre el sistema, a quién, cuándo y cómo, dentro y fuera de la empresa.", "D U", False, "Basta un plan de comunicación en forma de tabla sencilla (qué, a quién, cuándo, cómo, quién lo comunica)."),
    ("7.5", "7 Soporte", "Información documentada", "Crear, actualizar y controlar la documentación del sistema (versiones, aprobación, acceso, conservación).", "D P U", False, ""),
    ("8.1", "8 Operación", "Planificación y control operacional", "Ejecutar lo planificado, controlar los cambios y los procesos subcontratados, y guardar pruebas.", "S", False, "No tiene trabajo propio: sus 4 puntos se cumplen con otros requisitos. Ojo: si se excluyera A.10.3, controlar lo subcontratado (8.1.d) pasaría a ser trabajo propio, porque la 8.1 es obligatoria siempre."),
    ("8.2", "8 Operación", "Evaluación de riesgos de IA", "Hacer la evaluación de riesgos a intervalos planificados o cuando haya cambios importantes, y guardar los resultados.", "R Pe Ev", False, ""),
    ("8.3", "8 Operación", "Tratamiento de riesgos de IA", "Aplicar el plan de tratamiento de riesgos, guardar resultados y actualizarlo si aparecen riesgos nuevos o no funciona.", "R Ev", False, ""),
    ("8.4", "8 Operación", "Evaluación de impacto de la IA", "Hacer las evaluaciones de impacto a intervalos planificados o cuando haya cambios importantes, y guardar los resultados.", "R Pe Ev", False, "No confundir con el tratamiento de riesgos (6.1.3 y 8.3): aquí van las evaluaciones de impacto."),
    ("9.1", "9 Evaluación", "Seguimiento, medición, análisis y evaluación", "Decidir qué se mide y cada cuánto, medir el funcionamiento del sistema y guardar los resultados.", "R Pe", False, ""),
    ("9.2", "9 Evaluación", "Auditoría interna", "Tener un programa de auditorías internas con auditores imparciales, hacerlas y guardar los resultados.", "D R Pe", False, ""),
    ("9.3", "9 Evaluación", "Revisión por la dirección", "La dirección revisa el sistema a intervalos planificados y se guardan las conclusiones.", "R Pe", False, ""),
    ("10.1", "10 Mejora", "Mejora continua", "Mejorar el sistema de forma continua.", "D Pe", False, "Basta un documento anual con las mejoras del año (qué, cuándo, por qué), repasado en la revisión por la dirección. Tienen que ser mejoras reales: el auditor puede pedir la prueba de alguna."),
    ("10.2", "10 Mejora", "No conformidades y acciones correctivas", "Cuando algo no se cumple: corregirlo, buscar la causa, evitar que se repita y guardar pruebas.", "R Ev", False, ""),
]

A = [
    ("A.2.2", "A.2 Políticas de IA", "Política de IA", "Tener una política escrita sobre el desarrollo o uso de sistemas de IA.", "D U", False, "Se solapa con la cláusula 5.2."),
    ("A.2.3", "A.2 Políticas de IA", "Alineación con otras políticas", "Ver qué otras políticas de la empresa (calidad, seguridad, privacidad…) afectan o se ven afectadas por la IA.", "D U", False, "Basta un documento corto o una tabla con cada política existente, si le afecta la IA y qué se ha ajustado."),
    ("A.2.4", "A.2 Políticas de IA", "Revisión de la política de IA", "Revisar la política a intervalos planificados o cuando haya cambios importantes.", "R Pe Ev", False, ""),
    ("A.3.2", "A.3 Organización interna", "Roles y responsabilidades de IA", "Definir y asignar roles y responsabilidades sobre la IA.", "D U", False, "Se solapa con la cláusula 5.3."),
    ("A.3.3", "A.3 Organización interna", "Informe de preocupaciones", "Tener un canal para que cualquiera pueda avisar de preocupaciones sobre la IA de la empresa.", "D P U", False, ""),
    ("A.4.2", "A.4 Recursos", "Documentación de recursos", "Tener un inventario de los sistemas de IA de la empresa con los recursos que necesita cada uno (datos, herramientas, infraestructura y personas).", "I Ev", False, ""),
    ("A.4.3", "A.4 Recursos", "Recursos de datos", "Documentar los datos que usa cada sistema de IA.", "I Ev", False, ""),
    ("A.4.4", "A.4 Recursos", "Recursos de herramientas", "Documentar las herramientas (modelos, librerías, plataformas) que usa cada sistema de IA.", "I Ev", False, ""),
    ("A.4.5", "A.4 Recursos", "Sistemas y recursos de computación", "Documentar la infraestructura (servidores, nube, hardware) que usa cada sistema de IA.", "I Ev", False, ""),
    ("A.4.6", "A.4 Recursos", "Recursos humanos", "Documentar qué personas y competencias intervienen en cada fase de cada sistema de IA.", "I Ev", False, ""),
    ("A.5.2", "A.5 Evaluación de impactos", "Proceso de evaluación de impacto", "Tener un proceso para evaluar las consecuencias de la IA en personas, grupos y sociedad durante todo su ciclo de vida.", "D U", False, "Se solapa con la cláusula 6.1.4."),
    ("A.5.3", "A.5 Evaluación de impactos", "Documentación de las evaluaciones de impacto", "Guardar los resultados de las evaluaciones de impacto durante un tiempo definido.", "R Ev", False, ""),
    ("A.5.4", "A.5 Evaluación de impactos", "Impacto en personas y grupos", "Evaluar y documentar el impacto de cada sistema de IA en personas o grupos.", "R Ev", False, ""),
    ("A.5.5", "A.5 Evaluación de impactos", "Impacto social", "Evaluar y documentar el impacto de cada sistema de IA en la sociedad.", "R Ev", False, ""),
    ("A.6.1.2", "A.6 Ciclo de vida", "Objetivos para el desarrollo responsable", "Fijar objetivos que guíen el desarrollo responsable de IA e integrarlos en el proceso de desarrollo.", "D U", False, "Aplica sobre todo si la empresa desarrolla IA."),
    ("A.6.1.3", "A.6 Ciclo de vida", "Procesos de diseño y desarrollo responsable", "Definir por escrito cómo se diseña y desarrolla IA de forma responsable.", "D U", False, "Aplica sobre todo si la empresa desarrolla IA."),
    ("A.6.2.2", "A.6 Ciclo de vida", "Requisitos y especificaciones", "Especificar por escrito los requisitos de cada sistema de IA nuevo o de cada mejora importante.", "D Ev", False, ""),
    ("A.6.2.3", "A.6 Ciclo de vida", "Documentación del diseño y desarrollo", "Documentar cómo se ha diseñado y desarrollado cada sistema de IA.", "D Ev", False, ""),
    ("A.6.2.4", "A.6 Ciclo de vida", "Verificación y validación", "Definir cómo se prueba cada sistema de IA y con qué criterios se da por bueno.", "D R Ev", False, ""),
    ("A.6.2.5", "A.6 Ciclo de vida", "Despliegue", "Tener un plan de puesta en marcha y comprobar los requisitos antes de desplegar.", "D Ev", False, ""),
    ("A.6.2.6", "A.6 Ciclo de vida", "Operación y seguimiento", "Definir qué hace falta para operar cada sistema de IA: seguimiento del rendimiento, reparaciones, actualizaciones y soporte.", "D Pe", False, ""),
    ("A.6.2.7", "A.6 Ciclo de vida", "Documentación técnica", "Decidir qué documentación técnica necesita cada tipo de interesado (usuarios, socios, autoridades) y dársela.", "D Ev", False, ""),
    ("A.6.2.8", "A.6 Ciclo de vida", "Registro de eventos (logs)", "Que cada sistema de IA guarde automáticamente un registro de lo que hace (logs), al menos mientras está en uso, y tener decidido qué se registra y cuánto se guarda.", "D R Ev U", False, "Solo para las funciones de IA del producto, incluidas las que usan modelos de terceros (la responsabilidad es de la empresa, no del proveedor). No afecta a cómo usa la IA cada empleado. Hay que programar en el producto que registre cada uso; se monta una vez por función y luego se genera solo. Ojo con los datos personales en los registros."),
    ("A.7.2", "A.7 Datos", "Datos para desarrollo y mejora", "Definir y aplicar procesos de gestión de los datos usados para desarrollar IA.", "D U", False, "Aplica sobre todo si la empresa desarrolla IA."),
    ("A.7.3", "A.7 Datos", "Adquisición de datos", "Documentar de dónde y cómo se obtienen y seleccionan los datos.", "I Ev", False, ""),
    ("A.7.4", "A.7 Datos", "Calidad de los datos", "Definir requisitos de calidad de los datos y comprobar que se cumplen.", "D R Ev", False, ""),
    ("A.7.5", "A.7 Datos", "Procedencia de los datos", "Tener un proceso para registrar el origen de los datos a lo largo de su vida.", "D I Ev", False, ""),
    ("A.7.6", "A.7 Datos", "Preparación de datos", "Definir los criterios y métodos para preparar los datos (limpieza, etiquetado…).", "D U", False, ""),
    ("A.8.2", "A.8 Información a interesados", "Documentación e información para usuarios", "Dar a los usuarios la información que necesitan sobre el sistema de IA.", "D Ev", False, "Solo para funciones de IA del producto. Va de la información que reciben los usuarios del sistema; no de los recursos del sistema de gestión, que son la 7.1."),
    ("A.8.3", "A.8 Información a interesados", "Informes externos", "Dar a los interesados externos una forma de avisar de efectos negativos de la IA.", "P U", False, ""),
    ("A.8.4", "A.8 Información a interesados", "Comunicación de incidentes", "Tener un plan para comunicar incidentes a los usuarios del sistema de IA.", "D Ev", False, ""),
    ("A.8.5", "A.8 Información a interesados", "Información a partes interesadas", "Documentar qué obligaciones tiene la empresa de informar sobre sus sistemas de IA y a quién.", "D U", False, ""),
    ("A.9.2", "A.9 Uso de sistemas de IA", "Procesos para el uso responsable", "Definir por escrito cómo se usan los sistemas de IA de forma responsable.", "D U", False, ""),
    ("A.9.3", "A.9 Uso de sistemas de IA", "Objetivos para el uso responsable", "Fijar objetivos que guíen el uso responsable de la IA.", "S", False, "No tiene trabajo propio: sus objetivos pueden ir junto a los objetivos de IA de la 6.2."),
    ("A.9.4", "A.9 Uso de sistemas de IA", "Uso previsto", "Asegurar que cada sistema de IA se usa para lo que está previsto y según su documentación.", "S", False, "No tiene trabajo propio: sus 3 puntos se cumplen con otros requisitos. Aplica a la IA del producto y a las herramientas de IA que usa la plantilla. Si se excluye alguno de los controles en que se apoya, ese punto pasa a ser trabajo propio."),
    ("A.10.2", "A.10 Terceros y clientes", "Reparto de responsabilidades", "Dejar claro qué responsabilidades tiene la empresa y cuáles sus socios, proveedores y clientes.", "D Ev", False, "Suele plasmarse en contratos o acuerdos."),
    ("A.10.3", "A.10 Terceros y clientes", "Proveedores", "Tener un proceso para que lo que dan los proveedores encaje con el uso responsable de IA de la empresa.", "D R Ev", False, ""),
    ("A.10.4", "A.10 Terceros y clientes", "Clientes", "Tener en cuenta las expectativas y necesidades de los clientes en el uso responsable de la IA.", "S", False, "No tiene trabajo propio: sus 4 puntos se cumplen con otros requisitos. Si se excluye alguno de los controles en que se apoya, ese punto pasa a ser trabajo propio."),
]


# Ayuda para decidir en la Declaración de Aplicabilidad (6.1.3.c) si un control aplica
CUANDO = {
    "A.2.2": "Casi siempre: cualquier empresa con un sistema de gestión de la IA necesita una política (además la exige la 5.2).",
    "A.2.3": "Aplica si la empresa ya tiene otras políticas (privacidad, seguridad, calidad…). Solo se excluiría si no tiene ninguna.",
    "A.2.4": "Casi siempre: si hay política, hay que revisarla.",
    "A.3.2": "Casi siempre: hacen falta responsables de los temas de IA.",
    "A.3.3": "Casi siempre: cualquier empresa que use IA debería tener un canal para avisar de problemas.",
    "A.4.2": "Casi siempre: aplica si la empresa tiene sistemas de IA propios o integrados en sus productos o procesos; el inventario es la base del resto.",
    "A.4.3": "Aplica si los sistemas de IA usan datos de la empresa (para entrenar, ajustar o funcionar). Excluible si la IA no maneja datos propios.",
    "A.4.4": "Aplica si la empresa desarrolla o integra sistemas de IA.",
    "A.4.5": "Aplica si la empresa ejecuta sistemas de IA en infraestructura propia o en una nube que gestiona. Más ligero si todo es un servicio de terceros.",
    "A.4.6": "Aplica si hay personas de la empresa que desarrollan, operan o supervisan sistemas de IA.",
    "A.5.2": "Casi siempre: la evaluación de impacto también la exige la 6.1.4.",
    "A.5.3": "Casi siempre, junto con la A.5.2.",
    "A.5.4": "Aplica si los sistemas de IA pueden afectar a personas (usuarios, clientes, empleados, candidatos…).",
    "A.5.5": "Aplica si los sistemas de IA pueden tener efectos amplios en la sociedad (gran escala, información pública, medio ambiente). Excluible en usos internos de poco alcance, justificándolo.",
    "A.6.1.2": "Aplica si la empresa desarrolla sistemas de IA. Excluible si solo usa IA de terceros.",
    "A.6.1.3": "Aplica si la empresa desarrolla sistemas de IA. Excluible si solo usa IA de terceros.",
    "A.6.2.2": "Aplica si la empresa desarrolla o mejora sistemas de IA, también si integra un modelo de terceros en un producto propio.",
    "A.6.2.3": "Aplica si la empresa diseña o desarrolla sistemas de IA.",
    "A.6.2.4": "Aplica si la empresa desarrolla o integra sistemas de IA y los pone en marcha.",
    "A.6.2.5": "Aplica si la empresa despliega sistemas de IA (para clientes o para uso interno).",
    "A.6.2.6": "Aplica si la empresa opera sistemas de IA en funcionamiento.",
    "A.6.2.7": "Aplica si la empresa ofrece sistemas de IA a otros (usuarios, clientes, socios) o tiene que informar a autoridades.",
    "A.6.2.8": "Aplica si la empresa tiene sistemas de IA en uso bajo su control, incluidos los que usan modelos de terceros dentro de un producto propio.",
    "A.7.2": "Aplica si la empresa usa datos para desarrollar, entrenar o ajustar IA.",
    "A.7.3": "Aplica si la empresa obtiene datos para sus sistemas de IA.",
    "A.7.4": "Aplica si la calidad de los datos influye en los resultados de sus sistemas de IA (casi siempre que haya datos propios).",
    "A.7.5": "Aplica si la empresa usa datos en sus sistemas de IA y necesita saber de dónde vienen.",
    "A.7.6": "Aplica si la empresa entrena o ajusta modelos con sus propios datos. Excluible si solo usa modelos de terceros ya entrenados.",
    "A.8.2": "Aplica si la empresa ofrece sistemas de IA a usuarios, internos o externos.",
    "A.8.3": "Aplica si los sistemas de IA de la empresa afectan a personas de fuera (clientes, usuarios, público).",
    "A.8.4": "Aplica si hay usuarios de sus sistemas de IA a los que avisar de incidentes.",
    "A.8.5": "Aplica si la empresa tiene obligaciones (legales o contractuales) de informar sobre sus sistemas de IA.",
    "A.9.2": "Casi siempre: toda empresa que usa IA necesita normas de uso responsable.",
    "A.9.3": "Casi siempre, junto con la A.9.2.",
    "A.9.4": "Casi siempre: cualquier sistema de IA tiene un uso previsto.",
    "A.10.2": "Casi siempre: aplica si intervienen terceros (proveedores, socios, clientes) en el ciclo de vida de los sistemas de IA.",
    "A.10.3": "Casi siempre: aplica si la empresa usa modelos, herramientas o datos de IA de proveedores.",
    "A.10.4": "Aplica si la empresa ofrece productos o servicios con IA a clientes.",
}

TIPOS = ["D", "R", "I", "P", "S", "Pe", "Ev", "U"]

filas = []
for cod, bloque, tit, res, tipos, dudoso, nota in C:
    filas.append((cod, "Cláusulas 4-10", bloque, tit, res, "Siempre", tipos, dudoso, nota))
for cod, bloque, tit, res, tipos, dudoso, nota in A:
    filas.append((cod, "Anexo A", bloque, tit, res, "Si aplica", tipos, dudoso, nota))

# Hoja «Puntos»: los hijos de cada requisito (lo que hay que cumplir para darlo por bueno)
# (padre, código, qué hay que cumplir, tipo, pruebas típicas, se apoya en)
P = [
    ("5.1", "5.1.a", "Asegurar que hay política y objetivos de IA, alineados con la estrategia de la empresa.", "D", "Política aprobada por dirección; objetivos de IA. Pregunta: «¿Cómo encaja la IA en la estrategia?»", "5.2, 6.2"),
    ("5.1", "5.1.b", "Integrar la gestión de la IA en los procesos del día a día.", "D", "Procedimientos que incluyan pasos de IA (p. ej. revisar riesgos antes de lanzar una función con IA). Pregunta: «¿Dónde se nota el sistema en el trabajo diario?»", ""),
    ("5.1", "5.1.c", "Asegurar los recursos necesarios.", "R", "Presupuesto aprobado; personas asignadas. Pregunta: «¿Qué recursos habéis dedicado?»", "7.1"),
    ("5.1", "5.1.d", "Comunicar la importancia de gestionar bien la IA.", "P", "Correos, comunicados o reuniones de la dirección sobre el tema. Pregunta: «¿Cómo lo ha transmitido la dirección?»", ""),
    ("5.1", "5.1.e", "Asegurar que el sistema da los resultados previstos.", "R", "Actas de la revisión por la dirección con los resultados. Pregunta: «¿Cómo sabéis que funciona?»", "9.3"),
    ("5.1", "5.1.f", "Dirigir y apoyar a las personas que hacen funcionar el sistema.", "D", "Nombramiento del responsable de IA; formaciones aprobadas. Pregunta: «¿Quién lleva esto y qué apoyo tiene?»", "5.3, 7.2"),
    ("5.1", "5.1.g", "Promover la mejora continua.", "R", "Decisiones de mejora en actas; acciones correctivas aprobadas. Pregunta: «¿Qué habéis mejorado este año?»", "10.1, 10.2"),
    ("5.1", "5.1.h", "Apoyar a otros responsables para que ejerzan su liderazgo en sus áreas.", "P", "Reuniones con responsables de área; delegaciones. Pregunta: «¿Cómo apoya la dirección a los demás responsables?»", ""),
    ("6.3", "6.3.a", "Que los cambios del sistema de gestión los decida la dirección.", "R", "Acta de la revisión por la dirección donde se decide el cambio. Pregunta: «Cambiasteis X en marzo, ¿quién lo decidió?»", "9.3"),
    ("6.3", "6.3.b", "Dejar constancia de qué cambió, cuándo y quién lo aprobó.", "D", "Historial de versiones de los documentos afectados (p. ej. política v1 → v2).", "7.5"),
    ("6.3", "6.3.c", "En los cambios grandes (p. ej. ampliar el alcance), un plan breve: qué, por qué, quién, cuándo y qué riesgos tiene.", "R", "Nota del plan del cambio. Para los riesgos puede apoyarse en la evaluación de riesgos (8.2). Los cambios pequeños no la necesitan.", ""),
    ("7.1", "7.1.a", "Que haya alguien con tiempo real para llevar el sistema de gestión.", "P", "Pregunta al responsable: «¿Cuántas horas dedicas a esto? ¿Te da tiempo?»", "5.3"),
    ("7.1", "7.1.b", "Que haya dinero para lo que cuesta el sistema: saber qué cuesta, que la dirección lo apruebe y que se pague.", "R", "Aprobación de la dirección de los costes del año (basta un correo o un acta) y facturas o contratos: certificación y auditorías de vigilancia, formación, herramientas, auditor interno externo si lo hay. Pregunta: «¿Cuánto cuesta mantener esto y quién lo aprobó?»", ""),
    ("7.1", "7.1.c", "Que las tareas del sistema vayan al día (la prueba de que los recursos bastan).", "R", "Auditoría interna y revisión por la dirección hechas en su fecha. Si llevan meses de retraso, faltan recursos.", "9.2, 9.3"),
    ("7.3", "7.3.a", "Que la plantilla conozca la política de IA: que existe, dónde está y sus ideas principales (qué herramientas se pueden usar, qué datos no se meten, a quién preguntar).", "P", "Pregunta a un empleado: «¿Sabes si la empresa tiene una política sobre IA? ¿Qué dice?». Prueba: el correo o la reunión donde se comunicó.", "5.2"),
    ("7.3", "7.3.b", "Que cada persona sepa qué le toca al usar IA en su trabajo: qué herramientas puede usar, qué datos no debe meter y que revisa lo que genera la IA antes de usarlo.", "P", "Pregunta: «En tu trabajo, ¿qué tienes que tener en cuenta al usar IA?». Prueba: sesión informativa corta con registro de asistencia.", ""),
    ("7.3", "7.3.c", "Que cada persona sepa qué pasa si no se siguen las normas de IA: los riesgos (p. ej. filtrar datos de clientes) y las consecuencias que fija la política.", "P", "Pregunta: «¿Qué pasa si alguien no sigue la política?». Prueba: que la sesión o la política lo expliquen.", ""),
    ("7.4", "7.4.a", "Tener decidido qué se comunica sobre el sistema, a quién, cuándo, cómo y quién lo comunica.", "D", "Plan de comunicación: una tabla sencilla (p. ej. «Política de IA · toda la plantilla · al aprobarla y a cada incorporación · sesión + correo · responsable de IA»). Pregunta: «¿Cómo decidís qué se comunica sobre IA?»", ""),
    ("7.4", "7.4.b", "Que la comunicación interna se haga.", "P", "El correo o la reunión donde se comunicó la política; registro de la sesión informativa.", "5.2, 7.3"),
    ("7.4", "7.4.c", "Que la comunicación externa se haga.", "P", "Lo que se ha contado a clientes u otros interesados sobre la IA del producto.", "A.8.5"),
    ("8.1", "8.1.a", "Que cada proceso del sistema tenga criterios claros de cómo se hace.", "D", "Los procesos escritos de evaluación de riesgos, tratamiento de riesgos y evaluación de impacto.", "6.1.2, 6.1.3, 6.1.4"),
    ("8.1", "8.1.b", "Que quede constancia de que los procesos se hacen según lo planificado.", "R", "Los registros de las evaluaciones de riesgos, tratamientos y evaluaciones de impacto hechas.", "8.2, 8.3, 8.4"),
    ("8.1", "8.1.c", "Controlar los cambios planificados y revisar las consecuencias de los no planificados.", "R", "Plan del cambio e historial de versiones.", "6.3"),
    ("8.1", "8.1.d", "Controlar lo que hacen proveedores o terceros (p. ej. IA de otra empresa).", "R", "Qué proveedores intervienen y cómo se controlan. Pregunta: «¿Usáis IA de terceros? ¿Cómo os aseguráis de que cumple?»", "A.10.3"),
    ("10.1", "10.1.a", "Detectar oportunidades de mejora.", "R", "Hallazgos de la auditoría interna y conclusiones de la revisión por la dirección.", "9.2, 9.3"),
    ("10.1", "10.1.b", "Corregir los fallos que aparezcan.", "R", "Acciones correctivas hechas.", "10.2"),
    ("10.1", "10.1.c", "Tener cada año la lista de mejoras hechas.", "D", "Documento anual con las mejoras: qué, cuándo y por qué (p. ej. «marzo: simplificamos la evaluación de riesgos porque tardaba demasiado»). Pregunta: «¿Qué habéis mejorado este año?», y puede pedir la prueba de alguna.", ""),
    ("A.6.2.8", "A.6.2.8.a", "Tener decidido qué registra cada función de IA del producto, en qué fases y cuánto tiempo se guarda.", "D", "Documento corto por función de IA (suele ir en su documentación técnica), p. ej. «el asistente de IA del producto registra cada petición, la respuesta del modelo y la acción del producto; se guarda 12 meses».", "A.6.2.7"),
    ("A.6.2.8", "A.6.2.8.b", "Que los registros existan de verdad mientras la función está en uso. Qué hay que montar: programar en el producto, donde se llama a la IA, que guarde cada uso (quién, cuándo, qué se pidió, qué respondió, qué hizo el producto). Se hace una vez por función y luego se genera solo.", "R", "Registros generados automáticamente por el producto (tabla en base de datos o fichero de registros). Pregunta: «Enséñame los registros de ayer de esta función».", ""),
    ("A.8.2", "A.8.2.a", "Tener decidido qué información necesita cada tipo de usuario de cada función de IA.", "D", "Lista por función de IA: qué se cuenta al usuario final y qué al técnico (que es una IA, para qué sirve, cómo anularla, limitaciones, fiabilidad, si necesita supervisión).", "A.6.2.7"),
    ("A.8.2", "A.8.2.b", "Que esa información llegue de verdad al usuario. Qué hay que montar: los avisos en pantalla y la ayuda dentro del producto.", "P", "Lo que ve el usuario, p. ej. un aviso «Esta sugerencia la genera una IA; revísala antes de confirmar», el manual o la ayuda.", ""),
    ("A.9.4", "A.9.4.a", "Tener escrito para qué sirve cada sistema de IA.", "D", "La ficha de cada sistema en el inventario, que dice para qué sirve. En herramientas de terceros, además, qué uso permite la empresa (normas de uso) y las condiciones del proveedor.", "A.4.2, A.9.2"),
    ("A.9.4", "A.9.4.b", "Que cada sistema de IA se use para lo que está previsto: quien lo usa sabe para qué sirve y qué no debe hacer con él (p. ej. meter datos de clientes en una herramienta no aprobada).", "P", "Pregunta a un programador: «¿Para qué usas la herramienta de IA? ¿Metes datos de clientes?». En el producto, los registros de uso.", "A.6.2.8, 7.3"),
    ("A.9.4", "A.9.4.c", "Tener forma de detectar usos indebidos.", "P", "El canal para avisar de problemas con la IA.", "A.3.3"),
    ("A.10.4", "A.10.4.a", "Saber qué esperan los clientes de la IA de la empresa.", "I", "Los clientes en la lista de partes interesadas, con sus expectativas (saber cuándo decide una IA, qué pasa con sus datos, poder desactivarla, a quién reclamar).", "4.2"),
    ("A.10.4", "A.10.4.b", "Reflejarlo en las condiciones o el contrato.", "D", "Cláusulas que digan qué hace la IA, quién responde de qué y qué pasa con los datos.", "A.10.2"),
    ("A.10.4", "A.10.4.c", "Informar a los clientes como necesitan.", "P", "Avisos en el producto, ayuda, información sobre la IA.", "A.8.2, A.8.5"),
    ("A.10.4", "A.10.4.d", "Que los clientes puedan avisar o quejarse.", "P", "Canal de avisos para externos.", "A.8.3"),
]
P += [
    # --- Cláusula 4 ---
    ("4.1", "4.1.a", "Tener identificadas las cuestiones externas que afectan al uso de la IA: leyes aplicables (incluidos usos de IA prohibidos), reguladores, mercado y competencia, ética y cultura.", "D", "Documento de contexto (p. ej. un DAFO o una tabla de cuestiones externas). Pregunta: «¿Qué leyes y factores externos os afectan en el uso de la IA?»", ""),
    ("4.1", "4.1.b", "Tener identificadas las cuestiones internas: organización y gobierno, obligaciones contractuales y para qué sirve la IA que se desarrolla o usa.", "D", "La parte interna del mismo documento de contexto: cómo se organiza la empresa, qué contratos le obligan y para qué usa o desarrolla IA. Pregunta: «¿Para qué usáis la IA en la empresa?»", ""),
    ("4.1", "4.1.c", "Tener determinado el papel de la empresa respecto a la IA: si la desarrolla, la ofrece en sus productos o solo la usa.", "D", "Una línea clara en el documento de contexto. Pregunta: «¿Qué papel tenéis con la IA?». De ese papel depende qué controles del Anexo A aplican.", ""),
    ("4.1", "4.1.d", "Revisar el contexto cada año y cuando cambie algo importante.", "R", "Fecha de la última revisión del documento; los cambios de contexto se tratan en la revisión por la dirección.", "9.3"),
    ("4.2", "4.2.a", "Tener la lista de partes interesadas relevantes (clientes, empleados, proveedores, reguladores, accionistas…).", "D", "Tabla de partes interesadas. Pregunta: «¿A quién afecta vuestro uso de la IA?»", ""),
    ("4.2", "4.2.b", "Saber qué espera o exige cada una.", "D", "Columna de expectativas en la misma tabla (p. ej. clientes: saber cuándo decide una IA; reguladores: cumplir la normativa de IA).", ""),
    ("4.2", "4.2.c", "Decidir cuáles de esas expectativas asume el sistema de gestión.", "D", "Columna «¿lo asumimos?» en la tabla, con el motivo cuando no.", ""),
    ("4.3", "4.3.a", "Fijar los límites: qué áreas, procesos, sistemas de IA y ubicaciones entran en el sistema de gestión.", "D", "Declaración de alcance. Pregunta: «¿Qué entra y qué no en vuestro sistema?»", ""),
    ("4.3", "4.3.b", "Que el alcance tenga en cuenta el contexto y las partes interesadas.", "D", "Que el alcance sea coherente con el documento de contexto (4.1) y la tabla de partes interesadas (4.2). Pregunta: «¿Por qué el alcance es este y no otro?»", ""),
    ("4.3", "4.3.c", "Tener el alcance por escrito y disponible.", "D", "El documento de alcance aprobado y accesible para quien lo necesite.", ""),
    ("4.3", "4.3.d", "Justificar lo que se deja fuera (recomendado).", "D", "El motivo de cada exclusión en el documento de alcance. El auditor desconfía de alcances que dejan fuera justo lo difícil.", ""),
    # --- Cláusula 5 ---
    ("5.2", "5.2.a", "Que la política sea apropiada para lo que hace la empresa.", "D", "Que hable de la IA que la empresa usa o desarrolla de verdad y cuadre con el contexto. Prueba práctica: si al cambiar el nombre de la empresa sigue valiendo igual, es demasiado genérica.", ""),
    ("5.2", "5.2.b", "Que sirva de marco para fijar los objetivos de IA.", "D", "Que los objetivos de IA (6.2) salgan de lo que dice la política. Pregunta: «¿Qué objetivos salen de vuestra política?»", ""),
    ("5.2", "5.2.c", "Que incluya el compromiso de cumplir los requisitos aplicables (leyes, contratos…).", "D", "Frase explícita en la política.", ""),
    ("5.2", "5.2.d", "Que incluya el compromiso de mejora continua.", "D", "Frase explícita en la política.", ""),
    ("5.2", "5.2.e", "Que esté aprobada por la alta dirección.", "R", "Firma o acta de aprobación, con fecha y versión.", ""),
    ("5.2", "5.2.f", "Que la política de IA se haya comunicado y esté a mano (intranet, carpeta compartida). Cada persona tiene que saber que existe y dónde encontrarla.", "P", "Correo o sesión donde se comunicó; política accesible (intranet, web). Pregunta a un empleado: «¿Conoces la política de IA?»", ""),
    ("5.3", "5.3.a", "Asignar a alguien la responsabilidad de que el sistema cumpla la norma.", "D", "Nombramiento por escrito. Pregunta: «¿Quién es responsable del sistema?»", ""),
    ("5.3", "5.3.b", "Asignar quién informa a la dirección de cómo funciona el sistema.", "D", "Nombramiento o descripción del rol; suele ser el mismo responsable del sistema. Pregunta: «¿Quién informa a la dirección y cada cuánto?»", ""),
    ("5.3", "5.3.c", "Repartir y comunicar el resto de responsabilidades del sistema.", "D", "Tabla de roles y responsabilidades, comunicada a los implicados. Puede ser la misma que la del control A.3.2.", ""),
    # --- Cláusula 6 ---
    ("6.1.1", "6.1.1.a", "Identificar los riesgos y oportunidades que pueden impedir que el sistema de gestión consiga sus resultados, teniendo en cuenta el contexto y las partes interesadas.", "D", "Lista de riesgos y oportunidades del sistema de gestión en sí, no de cada sistema de IA (p. ej. riesgo: «el responsable no tiene tiempo»; oportunidad: «usar la certificación ante clientes»). Pregunta: «¿Qué puede impedir que vuestro sistema funcione?»", ""),
    ("6.1.1", "6.1.1.b", "Fijar criterios de riesgo de IA: cuándo un riesgo es aceptable y cuándo no.", "D", "Escala de riesgo (p. ej. probabilidad × impacto) y umbral de aceptación. Pregunta: «¿Cómo decidís si un riesgo es aceptable?»", ""),
    ("6.1.1", "6.1.1.c", "Planificar acciones para tratarlos y cómo se comprobará que funcionan.", "D", "Plan de acciones con responsable, plazo y cómo se medirá.", ""),
    ("6.1.2", "6.1.2.a", "Tener un método escrito de evaluación de riesgos de IA, alineado con la política y los objetivos.", "D", "Procedimiento de evaluación de riesgos: quién la hace, cada cuánto, qué pasos sigue y qué escala usa. Pregunta: «¿Cómo evaluáis los riesgos de vuestros sistemas de IA?»", ""),
    ("6.1.2", "6.1.2.b", "Que el método dé resultados coherentes y comparables si se repite.", "D", "Criterios y escalas fijos en el procedimiento: dos evaluaciones del mismo sistema no deberían dar resultados sin sentido.", ""),
    ("6.1.2", "6.1.2.c", "Que incluya identificar los riesgos, analizarlos (consecuencias para la empresa, las personas y la sociedad, y probabilidad) y valorarlos frente a los criterios.", "D", "Pasos del procedimiento. La parte de consecuencias para personas y sociedad usa la evaluación de impacto (6.1.4).", ""),
    ("6.1.3", "6.1.3.a", "Tener un método escrito para decidir cómo se trata cada riesgo (reducir, evitar, transferir o aceptar).", "D", "Procedimiento de tratamiento: para cada riesgo por encima del umbral, qué se hace (reducirlo con medidas, evitarlo dejando de hacer algo, transferirlo con un contrato o seguro, o aceptarlo) y quién lo decide.", ""),
    ("6.1.3", "6.1.3.b", "Elegir los controles necesarios y compararlos con el Anexo A para no olvidar ninguno.", "D", "Relación riesgo → controles elegidos (p. ej. «respuestas incorrectas del asistente de IA» → revisión humana y pruebas antes de publicar).", ""),
    ("6.1.3", "6.1.3.c", "Redactar la Declaración de Aplicabilidad: todos los controles del Anexo A, si aplican o no, y por qué.", "D", "La Declaración de Aplicabilidad, uno de los primeros documentos que mira el auditor. Pregunta: «¿Por qué excluisteis este control?»", ""),
    ("6.1.3", "6.1.3.d", "Tener un plan de tratamiento aprobado, y que la dirección o los responsables acepten el riesgo que queda después de las medidas (riesgo residual).", "R", "Plan de tratamiento con su aprobación y la aceptación firmada del riesgo residual. Pregunta: «¿Quién aprobó asumir este riesgo?»", ""),
    ("6.1.4", "6.1.4.a", "Tener un método escrito para evaluar el impacto de los sistemas de IA en personas, grupos y sociedad.", "D", "Procedimiento de evaluación de impacto: qué se evalúa (a quién puede afectar el sistema y cómo), quién la hace y con qué plantilla.", ""),
    ("6.1.4", "6.1.4.b", "Definir cuándo se hace (p. ej. sistema nuevo o cambio importante) y cómo se usan sus resultados en la evaluación de riesgos.", "D", "Disparadores y conexión con el proceso de riesgos, en el procedimiento.", ""),
    ("6.1.4", "6.1.4.c", "Documentar los resultados de las evaluaciones de impacto.", "R", "Evaluaciones de impacto hechas y archivadas.", "8.4, A.5.3"),
    ("6.2", "6.2.a", "Fijar objetivos de IA coherentes con la política y medibles cuando sea posible.", "D", "Lista de objetivos con su indicador (p. ej. «todos los sistemas de IA con evaluación de impacto antes de lanzarse»).", ""),
    ("6.2", "6.2.b", "Planificar cada objetivo: qué se hará, con qué recursos, quién es responsable, para cuándo y cómo se evaluará.", "D", "Una tabla con esas columnas, p. ej. «evaluar el impacto de todos los sistemas · responsable de IA · 20 horas · antes de junio · % de sistemas evaluados».", ""),
    ("6.2", "6.2.c", "Hacer seguimiento de los objetivos, comunicarlos y actualizarlos.", "R", "Estado de los objetivos medido y revisado en la revisión por la dirección.", "9.1, 9.3"),
    # --- Cláusula 7 ---
    ("7.2", "7.2.a", "Determinar qué competencias necesita cada rol del sistema.", "D", "Tabla rol → conocimientos necesarios (p. ej. responsable del sistema: gestión de riesgos y la norma; auditor interno: técnicas de auditoría).", ""),
    ("7.2", "7.2.b", "Asegurar que las personas las tienen (formación, estudios o experiencia).", "R", "Certificados, cursos, experiencia. Pregunta al responsable: «¿Qué formación tienes en gestión de la IA?»", ""),
    ("7.2", "7.2.c", "Cuando falten, actuar (formar, contratar, reasignar) y comprobar que ha funcionado.", "R", "Registro de la formación hecha y de cómo se comprobó su eficacia.", ""),
    ("7.5", "7.5.a", "Tener los documentos que exige la norma y los que la empresa considere necesarios.", "D", "Lista de documentos del sistema: el índice de todo lo demás. Pregunta: «¿Qué documentos forman vuestro sistema?»", ""),
    ("7.5", "7.5.b", "Que cada documento tenga identificación, versión, fecha, autor y aprobación.", "D", "Cabecera estándar e historial de versiones.", ""),
    ("7.5", "7.5.c", "Controlarlos: accesibles para quien los necesita, protegidos, con control de versiones y con un tiempo de conservación definido.", "P", "Dónde se guardan y quién accede. Pregunta: «¿Cómo sé que esta es la versión vigente?». El propio portal puede cubrir buena parte de esto.", ""),
    # --- Cláusula 8 ---
    ("8.2", "8.2.a", "Hacer la evaluación de riesgos de IA según el método, a intervalos planificados.", "R", "Informe de cada evaluación, con fecha, al ritmo fijado en el procedimiento (p. ej. anual). Pregunta: «¿Cuándo fue la última evaluación de riesgos?»", ""),
    ("8.2", "8.2.b", "Repetirla cuando haya cambios importantes.", "R", "Evaluación hecha tras el cambio. Pregunta: «Cuando lanzasteis este sistema, ¿evaluasteis sus riesgos?»", ""),
    ("8.2", "8.2.c", "Guardar los resultados de cada evaluación de riesgos.", "R", "Registro de riesgos actualizado: cada riesgo con su nivel, responsable y estado.", ""),
    ("8.3", "8.3.a", "Aplicar el plan de tratamiento de riesgos y guardar los resultados.", "R", "Estado de cada acción del plan (hecha, en curso). Pregunta: «¿Qué medidas del plan están hechas y cuáles pendientes?»", ""),
    ("8.3", "8.3.b", "Comprobar que las medidas funcionan y, si no, volver a tratar el riesgo.", "R", "Revisión de si las medidas han reducido el riesgo (p. ej. menos incidentes después de añadir revisión humana).", ""),
    ("8.3", "8.3.c", "Tratar los riesgos nuevos que aparezcan.", "R", "Riesgos nuevos añadidos al plan.", ""),
    ("8.4", "8.4.a", "Hacer las evaluaciones de impacto según el método, a intervalos planificados y cuando haya cambios importantes.", "R", "Evaluación de impacto de cada sistema, con fecha. Pregunta: «¿Cuándo evaluasteis el impacto de este sistema?»", ""),
    ("8.4", "8.4.b", "Guardar los resultados de cada evaluación de impacto.", "R", "Evaluaciones archivadas.", ""),
    # --- Cláusula 9 ---
    ("9.1", "9.1.a", "Decidir qué se mide, cómo, cuándo y cuándo se analizan los resultados.", "D", "Tabla de indicadores (p. ej. % de sistemas evaluados, incidentes, formaciones hechas) con frecuencia y responsable.", ""),
    ("9.1", "9.1.b", "Medir y guardar los resultados.", "R", "Resultados de los indicadores en cada periodo (p. ej. un cuadro trimestral).", ""),
    ("9.1", "9.1.c", "Evaluar si el sistema funciona.", "R", "Análisis de los resultados, normalmente en la revisión por la dirección.", "9.3"),
    ("9.2", "9.2.a", "Tener un programa de auditorías internas: frecuencia, métodos, responsables y cómo se informa.", "D", "Programa de auditoría (normalmente anual).", ""),
    ("9.2", "9.2.b", "Definir el alcance y los criterios de cada auditoría.", "D", "Plan de cada auditoría: qué se revisa, con qué criterios (la norma y los procedimientos propios), quién la hace y cuándo.", ""),
    ("9.2", "9.2.c", "Que los auditores sean objetivos e imparciales: nadie audita su propio trabajo.", "P", "Quién auditó. Si solo hay una persona que lleva el sistema, suele contratarse a alguien de fuera.", ""),
    ("9.2", "9.2.d", "Hacer la auditoría, informar a la dirección y guardar los resultados.", "R", "Informe de auditoría con los hallazgos, enviado a la dirección. Los incumplimientos que salgan se tratan como no conformidades (10.2).", ""),
    ("9.3", "9.3.a", "Hacer la revisión por la dirección a intervalos planificados (normalmente cada año).", "R", "Acta con fecha y asistentes.", ""),
    ("9.3", "9.3.b", "Que la revisión trate lo que pide la norma: acciones de revisiones anteriores, cambios de contexto y de partes interesadas, no conformidades, resultados de las mediciones y de las auditorías, y oportunidades de mejora.", "R", "Orden del día del acta con esos puntos. Los datos salen de 4.1, 4.2, 9.1, 9.2 y 10.2.", ""),
    ("9.3", "9.3.c", "Que salgan decisiones: mejoras y cambios necesarios.", "R", "Decisiones en el acta, con responsables.", ""),
    # --- Cláusula 10 ---
    ("10.2", "10.2.a", "Cuando algo no se cumple, corregirlo y atender sus consecuencias.", "R", "Registro de la no conformidad (qué falló, cuándo, quién lo detectó) y de la corrección inmediata. Pregunta: «¿Qué fallos habéis tenido y qué hicisteis?»", ""),
    ("10.2", "10.2.b", "Buscar la causa y ver si puede pasar en otro sitio.", "R", "Análisis de causa (p. ej. preguntar «¿por qué?» varias veces hasta llegar al origen).", ""),
    ("10.2", "10.2.c", "Aplicar acciones para que no se repita y comprobar que han funcionado.", "R", "Acción correctiva con responsable, plazo y verificación de eficacia.", ""),
    # --- A.2 Políticas ---
    ("A.2.2", "A.2.2.a", "Tener una política escrita sobre el desarrollo o uso de IA.", "D", "La misma política de la cláusula 5.2.", "5.2"),
    ("A.2.2", "A.2.2.b", "Que la política tenga en cuenta la estrategia, los valores, el nivel de riesgo aceptado, las leyes y el impacto en los interesados (recomendado).", "D", "Contenido de la política.", ""),
    ("A.2.2", "A.2.2.c", "Que incluya principios y qué hacer ante excepciones (recomendado).", "D", "Apartados de principios y de excepciones en la política.", ""),
    ("A.2.3", "A.2.3.a", "Listar las demás políticas de la empresa (privacidad, seguridad, calidad…) y ver si la IA les afecta.", "D", "Tabla política → ¿le afecta la IA? → qué se ha ajustado. Pregunta: «¿Habéis revisado vuestras otras políticas al introducir la IA?»", ""),
    ("A.2.3", "A.2.3.b", "Ajustar las que choquen con la política de IA.", "R", "Versiones nuevas de esas políticas.", ""),
    ("A.2.4", "A.2.4.a", "Revisar la política a intervalos planificados.", "R", "Fecha de la última revisión; tratada en la revisión por la dirección.", "9.3"),
    ("A.2.4", "A.2.4.b", "Revisarla también cuando haya cambios importantes.", "R", "Revisión hecha tras el cambio.", ""),
    ("A.2.4", "A.2.4.c", "Que haya un responsable de la política aprobado por la dirección.", "D", "El rol en la tabla de responsabilidades.", "5.3"),
    # --- A.3 Organización interna ---
    ("A.3.2", "A.3.2.a", "Definir los roles de IA necesarios (p. ej. gestión de riesgos, evaluaciones de impacto, seguridad, privacidad, calidad de datos, supervisión humana, relación con proveedores).", "D", "Tabla de roles de IA.", ""),
    ("A.3.2", "A.3.2.b", "Asignar cada rol a una persona.", "D", "Nombres en la tabla de roles.", "5.3"),
    ("A.3.3", "A.3.3.a", "Tener un canal para que empleados y colaboradores avisen de preocupaciones sobre la IA, y que la plantilla sepa cuál es y que puede usarlo.", "P", "Buzón, correo o formulario conocido por la plantilla. Puede reutilizarse un canal de denuncias existente. Pregunta a un empleado: «Si ves un mal uso de la IA, ¿a quién lo dices?»", ""),
    ("A.3.3", "A.3.3.b", "Que el canal permita confidencialidad o anonimato y proteja de represalias.", "P", "Se ve en el propio canal (p. ej. un formulario que no pide el nombre). Lo de no tomar represalias basta con que lo diga la política.", ""),
    ("A.3.3", "A.3.3.c", "Que esté decidido quién investiga lo que llega, en qué plazo se responde y cuándo se escala.", "D", "Basta con media página o un apartado de la política o de las normas de uso. Pregunta: «¿Qué pasa cuando llega un aviso?»", ""),
    ("A.3.3", "A.3.3.d", "Registrar los casos recibidos y qué se hizo con ellos.", "R", "Registro de casos: fecha, qué se avisó, quién lo gestionó, cómo se resolvió.", ""),
    # --- A.4 Recursos ---
    ("A.4.2", "A.4.2.a", "Tener un inventario de los sistemas de IA con los recursos que necesita cada uno en cada fase.", "I", "Inventario de sistemas de IA: nombre, para qué sirve, responsable, si es propio o de terceros y qué recursos usa. Es la base de todo el bloque A.4. Pregunta: «¿Qué sistemas de IA tenéis?»", ""),
    ("A.4.2", "A.4.2.b", "Mantenerlo al día cuando entra, cambia o se retira un sistema.", "R", "Fecha de la última actualización.", ""),
    ("A.4.3", "A.4.3.a", "Documentar los datos que usa cada sistema: origen, categorías, fecha de última actualización, uso previsto, calidad, sesgos conocidos, conservación y borrado.", "I", "Ficha de datos por sistema, dentro del inventario.", ""),
    ("A.4.4", "A.4.4.a", "Documentar las herramientas de cada sistema: modelos y algoritmos, y herramientas de desarrollo, de preparación de datos y de evaluación.", "I", "Ficha de herramientas por sistema. Si el modelo es de un tercero, su nombre y versión.", ""),
    ("A.4.5", "A.4.5.a", "Documentar la infraestructura de cada sistema: dónde se ejecuta (propia o en la nube), capacidad de cálculo, red y almacenamiento.", "I", "Ficha de infraestructura por sistema.", ""),
    ("A.4.6", "A.4.6.a", "Documentar qué personas y competencias intervienen en cada fase de cada sistema (desarrollo, despliegue, operación, supervisión, retirada).", "I", "Ficha de personas por sistema.", ""),
    # --- A.5 Evaluación de impactos ---
    ("A.5.2", "A.5.2.a", "Tener un proceso para evaluar el impacto de la IA en personas, grupos y sociedad durante todo su ciclo de vida.", "D", "El mismo procedimiento de la cláusula 6.1.4.", "6.1.4"),
    ("A.5.2", "A.5.2.b", "Que el proceso gradúe el detalle según el propósito del sistema, su complejidad y la sensibilidad de los datos.", "D", "Criterios de profundidad en el procedimiento.", ""),
    ("A.5.3", "A.5.3.a", "Guardar los resultados de las evaluaciones de impacto.", "R", "Evaluaciones archivadas.", "8.4"),
    ("A.5.3", "A.5.3.b", "Definir cuánto tiempo se conservan.", "D", "Plazo de conservación en el procedimiento.", ""),
    ("A.5.4", "A.5.4.a", "Evaluar y documentar el impacto en personas o grupos: equidad, transparencia, explicabilidad, privacidad, seguridad y salud, consecuencias económicas, accesibilidad y derechos.", "R", "Evaluación de impacto de cada sistema con esos apartados. Pregunta: «¿Qué impacto puede tener este sistema en quien lo usa o se ve afectado por él?»", ""),
    ("A.5.5", "A.5.5.a", "Evaluar y documentar el impacto social: medio ambiente, economía, desinformación, salud y seguridad, normas culturales.", "R", "Apartado de impacto social en la evaluación de cada sistema.", ""),
    # --- A.6 Ciclo de vida ---
    ("A.6.1.2", "A.6.1.2.a", "Fijar objetivos para el desarrollo responsable (p. ej. equidad, transparencia, seguridad).", "D", "Lista de objetivos de desarrollo responsable.", ""),
    ("A.6.1.2", "A.6.1.2.b", "Integrarlos en el proceso de desarrollo con medidas concretas.", "D", "Dónde aparecen en el proceso (p. ej. revisión de sesgos antes de publicar).", "A.6.1.3"),
    ("A.6.1.3", "A.6.1.3.a", "Definir por escrito el proceso de diseño y desarrollo de IA: fases, pruebas, supervisión humana, cuándo se hacen evaluaciones de impacto, criterios de salida a producción y aprobaciones.", "D", "Procedimiento de desarrollo de IA.", ""),
    ("A.6.1.3", "A.6.1.3.b", "Que el proceso de desarrollo se siga de verdad en cada sistema.", "R", "Pruebas y aprobaciones de un desarrollo reciente. Pregunta: «Enséñame cómo se desarrolló el último sistema».", ""),
    ("A.6.2.2", "A.6.2.2.a", "Documentar por qué se desarrolla cada sistema y sus objetivos.", "D", "Ficha de requisitos del sistema. Pregunta: «¿Por qué decidisteis desarrollar este sistema?»", ""),
    ("A.6.2.2", "A.6.2.2.b", "Especificar sus requisitos (funcionales, de datos, de rendimiento) teniendo en cuenta todo su ciclo de vida.", "D", "Especificación del sistema.", ""),
    ("A.6.2.3", "A.6.2.3.a", "Documentar las decisiones de diseño: tipo de modelo y enfoque, datos, hardware y software, seguridad, interfaz y supervisión humana.", "D", "Documento de diseño de cada sistema. Pregunta: «¿Por qué elegisteis este modelo?»", ""),
    ("A.6.2.4", "A.6.2.4.a", "Definir cómo se prueba cada sistema: métodos, datos de prueba representativos del uso real y criterios para darlo por bueno (p. ej. tasa de error aceptable).", "D", "Plan de pruebas.", ""),
    ("A.6.2.4", "A.6.2.4.b", "Probar cada sistema según ese plan y guardar los resultados.", "R", "Resultados de las pruebas, con fecha y si se cumplieron los criterios.", ""),
    ("A.6.2.5", "A.6.2.5.a", "Tener un plan de despliegue.", "D", "Plan: dónde, cuándo, cómo y cómo se da marcha atrás.", ""),
    ("A.6.2.5", "A.6.2.5.b", "Comprobar los requisitos antes de desplegar.", "R", "Lista de comprobación aprobada antes de salir a producción.", ""),
    ("A.6.2.6", "A.6.2.6.a", "Definir qué hace falta para operar cada sistema: seguimiento del rendimiento, reparaciones, actualizaciones y soporte.", "D", "Procedimiento de operación.", ""),
    ("A.6.2.6", "A.6.2.6.b", "Vigilar que el sistema sigue funcionando bien (p. ej. que su precisión no empeora con el tiempo).", "R", "Registros de seguimiento y alertas.", ""),
    ("A.6.2.7", "A.6.2.7.a", "Decidir qué documentación técnica necesita cada tipo de interesado (usuarios, socios, autoridades).", "D", "Tabla interesado → documentación.", ""),
    ("A.6.2.7", "A.6.2.7.b", "Entregársela en la forma adecuada: descripción, instrucciones, supuestos técnicos y limitaciones.", "D", "La documentación entregada.", ""),
    # --- A.7 Datos ---
    ("A.7.2", "A.7.2.a", "Definir procesos de gestión de los datos usados para desarrollar IA: privacidad y seguridad, representatividad, exactitud e integridad.", "D", "Procedimiento de gestión de datos.", ""),
    ("A.7.2", "A.7.2.b", "Aplicar esos procesos en cada desarrollo.", "R", "Pruebas de un desarrollo reciente (p. ej. la revisión de privacidad de los datos usados). Pregunta: «¿Cómo gestionasteis los datos en el último desarrollo?»", ""),
    ("A.7.3", "A.7.3.a", "Documentar de dónde salen los datos de cada sistema: fuentes, categorías, cantidad, derechos de uso y tratamiento previo.", "I", "Ficha de adquisición de datos por sistema.", ""),
    ("A.7.4", "A.7.4.a", "Definir requisitos de calidad de los datos (exactitud, completitud, sesgos…).", "D", "Criterios de calidad de datos.", ""),
    ("A.7.4", "A.7.4.b", "Comprobar que los datos los cumplen.", "R", "Resultados de las comprobaciones.", ""),
    ("A.7.5", "A.7.5.a", "Tener un proceso para registrar el origen de los datos y lo que les pasa (creación, cambios, validación, traspasos).", "D", "Procedimiento de trazabilidad de datos.", ""),
    ("A.7.5", "A.7.5.b", "Mantener al día el registro de procedencia de los datos.", "I", "Registro de procedencia de los datos.", ""),
    ("A.7.6", "A.7.6.a", "Definir criterios y métodos de preparación de datos (limpieza, completado de huecos, normalización, etiquetado…).", "D", "Procedimiento de preparación de datos.", ""),
    # --- A.8 Información a interesados ---
    ("A.8.3", "A.8.3.a", "Dar a los interesados externos una forma de avisar de efectos negativos de la IA.", "P", "Formulario, correo o vía de soporte visible. Pregunta: «¿Cómo os avisa un usuario si la IA le perjudica?»", ""),
    ("A.8.3", "A.8.3.b", "Revisar y responder esos avisos.", "R", "Registro de avisos recibidos y respuestas.", ""),
    ("A.8.4", "A.8.4.a", "Tener un plan para comunicar incidentes de IA a los usuarios: qué es un incidente, quién avisa, cómo y en qué plazo.", "D", "Plan de comunicación de incidentes. Pregunta: «Si la IA falla y afecta a usuarios, ¿cómo se les avisa?»", ""),
    ("A.8.4", "A.8.4.b", "Conocer las obligaciones legales de notificación (p. ej. brechas de datos).", "D", "Referencia a esas obligaciones en el plan.", ""),
    ("A.8.5", "A.8.5.a", "Documentar qué obligaciones tiene la empresa de informar sobre sus sistemas de IA y a quién (usuarios, clientes, autoridades).", "D", "Lista de obligaciones de información.", ""),
    ("A.8.5", "A.8.5.b", "Cumplir esas obligaciones de información.", "R", "Comunicaciones hechas a quien correspondía (usuarios, clientes, autoridades), con fecha.", ""),
    # --- A.9 Uso ---
    ("A.9.2", "A.9.2.a", "Definir por escrito cómo se usan los sistemas de IA de forma responsable: aprobaciones necesarias, requisitos legales, costes y de dónde se obtienen.", "D", "Normas de uso de IA (pueden ir como anexo de la política).", ""),
    ("A.9.2", "A.9.2.b", "Que las normas de uso de IA se sigan de verdad: cada persona sabe qué hacer antes de empezar a usar una herramienta de IA nueva (p. ej. pedir aprobación).", "P", "Aprobaciones de herramientas nuevas. Pregunta a un empleado: «¿Qué necesitas para empezar a usar una herramienta de IA nueva?»", ""),
    ("A.9.3", "A.9.3.a", "Fijar objetivos para el uso responsable de la IA.", "D", "Lista de objetivos de uso responsable; pueden ir junto a los de la 6.2.", "6.2"),
    # --- A.10 Terceros ---
    ("A.10.2", "A.10.2.a", "Dejar claro qué responsabilidades del ciclo de vida de cada sistema tiene la empresa y cuáles sus socios, proveedores y clientes.", "D", "Contratos, acuerdos o una tabla de reparto. Pregunta: «Si falla el modelo de vuestro proveedor, ¿quién responde?»", ""),
    ("A.10.3", "A.10.3.a", "Tener un proceso para elegir y evaluar proveedores de IA (modelos, datos, herramientas) según los criterios de uso responsable de la empresa.", "D", "Procedimiento de proveedores con criterios (qué hacen con los datos, dónde los guardan, si los usan para entrenar).", ""),
    ("A.10.3", "A.10.3.b", "Aplicarlo a los proveedores actuales.", "R", "Ficha de evaluación de cada proveedor. Pregunta: «¿Cómo elegisteis este proveedor de IA?»", ""),
]
_orden = [x[0] for x in C] + [x[0] for x in A]
P.sort(key=lambda f: (_orden.index(f[0]), f[1]))
NOMBRE = {"D": "📄 Documento", "R": "🗂️ Registro", "I": "📋 Inventario", "P": "👥 Práctica"}

# Puntos que se cumplen por cada sistema de IA del inventario: «Todos» los sistemas,
# o «Solo producto» (la IA que desarrolla la empresa, no las herramientas que usa la plantilla)
_TODOS = ["A.4.2.a", "A.4.3.a", "A.4.4.a", "A.4.5.a", "A.4.6.a",
          "6.1.4.c", "8.4.a", "8.4.b", "A.5.3.a", "A.5.4.a", "A.5.5.a",
          "A.9.4.a", "A.9.4.b", "A.10.2.a", "A.7.3.a"]
_PRODUCTO = ["A.6.1.3.b",
             "A.6.2.2.a", "A.6.2.2.b", "A.6.2.3.a", "A.6.2.4.a", "A.6.2.4.b", "A.6.2.5.a", "A.6.2.5.b",
             "A.6.2.6.a", "A.6.2.6.b", "A.6.2.7.a", "A.6.2.7.b", "A.6.2.8.a", "A.6.2.8.b",
             "A.7.2.b", "A.7.4.b", "A.7.5.b", "A.8.2.a", "A.8.2.b"]
POR_SISTEMA = {**{c: "Todos" for c in _TODOS}, **{c: "Solo producto" for c in _PRODUCTO}}

# Las situaciones que reabren los requisitos «por evento»: casi todos saltan por
# estas pocas cosas. Sacadas de lo que dice cada requisito y de los cambios
# internos y externos del alcance y la revisión de la política.
# Un sistema de IA nuevo no está aquí: se da de alta en el inventario.
# (clave, título, cuándo, requisitos que reabre)
SITUACIONES = [
    ("persona", "Persona nueva o cambio de puesto",
     "Alguien entra en la empresa o cambia de papel, sobre todo si va a usar o llevar la IA.",
     ["7.2", "7.3", "A.4.6"]),
    ("proveedor", "Proveedor de IA nuevo",
     "Contratáis un modelo, unos datos o una herramienta de IA a una empresa con la que no trabajabais.",
     ["A.10.2", "A.10.3", "8.2"]),
    ("incidente", "Incidente, queja o algo que no se cumple",
     "La IA falla o perjudica a alguien, llega un aviso o una queja, o una auditoría encuentra algo que no se "
     "cumple.",
     ["10.2", "8.2", "8.3", "A.8.4"]),
    ("empresa", "Cambio en la empresa o en la gestión",
     "Una reorganización, un producto o servicio nuevo, otro responsable de la IA, otro alcance o una política "
     "nueva.",
     ["6.3", "4.1", "4.3", "5.3", "A.3.2", "A.2.4"]),
    ("fuera", "Cambio de fuera",
     "Una ley nueva, un cliente que exige algo o un cambio tecnológico que os afecta.",
     ["4.1", "4.2", "8.2", "A.2.4", "A.8.5"]),
]

# Al dar de alta un sistema en el inventario, lo que va por sistema sale pendiente solo; esto es de
# toda la empresa y no se abre solo, así que el inventario pregunta si se reabre
AL_DAR_DE_ALTA = ["8.2", "8.3", "A.10.3"]

# Cuestionario de la empresa: las preguntas de las que depende que aplique cada control del
# Anexo A, sacadas de su «¿Aplica a tu empresa?» (CUANDO). Se contestan Sí / No / No lo sé.
# (clave, pregunta, controles que decide)
PREGUNTAS = [
    ("desarrolla", "¿Desarrolláis IA o la integráis en un producto o servicio vuestro?",
     ["A.4.4", "A.6.1.2", "A.6.1.3", "A.6.2.2", "A.6.2.3", "A.6.2.4"]),
    ("entrena", "¿Entrenáis o ajustáis modelos con datos vuestros?", ["A.7.2", "A.7.6"]),
    ("datos", "¿Vuestra IA usa datos de la empresa para funcionar (no solo para entrenar)?",
     ["A.4.3", "A.7.3", "A.7.4", "A.7.5"]),
    ("clientes", "¿Ofrecéis IA a clientes o a usuarios de fuera?", ["A.10.4", "A.6.2.7", "A.8.2", "A.8.3", "A.8.4"]),
    ("personas", "¿La IA puede afectar a personas (clientes, empleados, candidatos…)?", ["A.5.4", "A.8.3"]),
    ("alcance", "¿Tiene un alcance amplio (mucha gente, información pública)?", ["A.5.5"]),
    ("infraestructura", "¿Alguna IA funciona en servidores o en una nube que gestionáis vosotros? (No, si solo usáis servicios ya hechos, como ChatGPT)",
     ["A.4.5", "A.6.2.5", "A.6.2.6", "A.6.2.8"]),
    ("proveedores", "¿Usáis modelos, herramientas o datos de IA de proveedores?", ["A.10.2", "A.10.3"]),
    ("informar", "¿Tenéis obligaciones legales o de contrato de informar sobre vuestra IA?", ["A.8.5"]),
    ("politicas", "¿Tenéis ya otras políticas (privacidad, seguridad, calidad…)?", ["A.2.3"]),
]
# Los controles que aplican casi siempre: no necesitan pregunta
# Las explicaciones en llano: qué pide el requisito, quién lo hace y por dónde empezar; y cada
# punto con un título en llano y una explicación con un ejemplo. Se escriben por bloques; donde no hay, el portal
# enseña el resumen y el texto de siempre.
LLANO = {
    "4.1": ("Un documento que explique qué cosas de fuera y de dentro de la empresa afectan a cómo usáis la IA, y qué "
            "papel tenéis con ella: si la hacéis, la metéis en lo que vendéis o solo usáis la de otros.",
            "Lo prepara quien lleve la ISO, con ayuda de la dirección, que conoce la estrategia y los contratos; lo "
            "revisa la dirección.",
            "Pulsa «Hacer borrador»: la plantilla «Contexto y partes interesadas» sirve para la 4.1 y la 4.2 a la vez. "
            "Empieza por el papel con la IA (punto c), porque de él depende casi todo lo demás."),
    "4.2": ("Una tabla con quién se ve afectado por vuestra IA (clientes, plantilla, proveedores, reguladores…), qué "
            "espera cada uno y si os comprometéis a dárselo.",
            "Quien lleve la ISO, preguntando a quien trata con cada grupo (comercial, recursos humanos…); la revisa la "
            "dirección.",
            "Pulsa «Hacer borrador»: va en el mismo documento que la 4.1. Empieza por la lista de grupos y después añade "
            "las otras dos columnas."),
    "4.3": ("Un documento corto que diga qué partes de la empresa y qué sistemas de IA entran en la certificación, cuáles "
            "no y por qué.",
            "Quien lleve la ISO lo propone; lo decide y lo aprueba la dirección.",
            "Ten antes el inventario de sistemas de IA (pantalla «Inventario») y la 4.1: el alcance sale de ahí. Después "
            "pulsa «Hacer borrador»."),
    "5.1": ("Que la dirección se implique de verdad: que dé recursos, que hable del tema y que se note que le importa. No "
            "es un documento: el auditor lo comprueba hablando con la dirección y mirando lo que ha firmado.",
            "La dirección. Quien lleve la ISO le ayuda a dejar rastro de lo que hace (correos, actas).",
            "Cinco de los ocho puntos se marcan solos al completar otros requisitos; quedan tres propios: el b, el d y el "
            "h. El más fácil es el d: un correo de la dirección a toda la plantilla explicando por qué importa gestionar "
            "bien la IA."),
    "5.2": ("Un documento corto, firmado por la dirección, que diga para qué usa la empresa la IA, con qué reglas y a qué "
            "se compromete.",
            "Lo redacta quien lleve la ISO en la empresa; lo aprueba y lo firma la dirección.",
            "Pulsa «Hacer borrador» (más abajo), rellena los [POR COMPLETAR], que lo firme la dirección, súbelo y mándalo "
            "a la plantilla."),
    "5.3": ("Decidir y poner por escrito quién se encarga de qué en la gestión de la IA, y que esas personas lo sepan.",
            "Lo decide y lo firma la dirección; lo redacta quien lleve la ISO.",
            "Pulsa «Hacer borrador»: la plantilla «Roles y responsabilidades» sirve para la 5.3 y el control A.3.2 a la "
            "vez. Empieza nombrando al responsable del sistema (punto a)."),
}
LLANO_PUNTOS = {
    "4.1.a": ("Lo de fuera que os afecta.",
              "Las leyes (el Reglamento europeo de IA, la protección de datos), lo que hacen los clientes y la "
              "competencia, y lo que la sociedad espera de la IA. Por ejemplo: «El Reglamento europeo de IA nos obliga a "
              "avisar a quien habla con nuestro chatbot de que es una IA». Basta una tabla o un DAFO; no hace falta un "
              "estudio."),
    "4.1.b": ("Lo de dentro que os afecta.",
              "Cómo está organizada la empresa, qué contratos os obligan a algo con la IA y para qué la usáis. Por "
              "ejemplo: «El equipo comercial usa ChatGPT para redactar ofertas; el contrato con un cliente prohíbe meter "
              "sus datos en herramientas de fuera»."),
    "4.1.c": ("Qué papel tenéis con la IA.",
              "Una frase clara: la desarrolláis, la metéis en vuestros productos o solo usáis la de otros (como ChatGPT o "
              "Copilot). Puede ser más de uno. Importa mucho: de esto depende qué controles del Anexo A os tocan."),
    "4.1.d": ("Repasarlo cada año.",
              "Una vez al año, y cuando cambie algo importante (una ley nueva, una IA nueva en la empresa), se mira si el "
              "documento sigue valiendo. Se hace en la revisión por la dirección (9.3): este punto se marca solo cuando "
              "esa esté hecha."),
    "4.2.a": ("A quién afecta vuestra IA.",
              "Una lista de grupos, no de personas: clientes, plantilla, proveedores, reguladores, socios… Por ejemplo, si "
              "un chatbot atiende a vuestros clientes, los clientes van en la lista."),
    "4.2.b": ("Qué espera cada uno.",
              "Al lado de cada grupo, qué espera de vuestra IA. Por ejemplo: los clientes, «saber cuándo les responde una "
              "IA y no una persona»; la plantilla, «que la IA no se use para vigilarla»."),
    "4.2.c": ("Qué os comprometéis a cumplir.",
              "Una columna «¿Lo asumimos?» con sí o no y, si es no, el motivo. Lo que digáis que sí hay que cumplirlo "
              "después: mejor pocas cosas y realistas."),
    "4.3.a": ("Qué entra y qué no.",
              "Qué departamentos, qué procesos, qué sistemas de IA y qué oficinas. Por ejemplo: «Entran todas las áreas de "
              "la oficina de Madrid y los cinco sistemas del inventario; queda fuera la filial de Portugal»."),
    "4.3.b": ("Que cuadre con la 4.1 y la 4.2.",
              "Si en el contexto decís que vuestra IA más importante es el chatbot de clientes, el chatbot tiene que "
              "estar dentro. El auditor compara los tres documentos."),
    "4.3.c": ("Que esté por escrito y a mano.",
              "El documento aprobado y guardado donde lo pueda abrir quien lo necesite. Es de lo primero que pide el "
              "auditor."),
    "4.3.d": ("Explicar lo que se deja fuera.",
              "Una línea con el motivo de cada cosa excluida, por ejemplo: «La filial de Portugal no usa IA». Es "
              "recomendable, no obligatorio, pero el auditor desconfía si se deja fuera justo lo difícil sin explicar "
              "por qué."),
    "5.1.a": ("Que haya política y objetivos.",
              "Se marca solo cuando estén la política (5.2) y los objetivos (6.2). El auditor preguntará a la dirección "
              "cómo encaja la IA en la estrategia de la empresa: conviene que sepa contestarlo con sus palabras."),
    "5.1.b": ("Que se note en el trabajo diario.",
              "Que la gestión de la IA esté metida en cómo se trabaja, no en un cajón. Por ejemplo: en el proceso de "
              "compras, un paso que diga «si la herramienta lleva IA, revisar sus riesgos antes de contratarla»."),
    "5.1.c": ("Que haya recursos.",
              "Se marca solo al completar la 7.1 (recursos): presupuesto y personas para llevar todo esto."),
    "5.1.d": ("Que la dirección hable del tema.",
              "Un correo, un comunicado o un punto en una reunión de empresa donde la dirección explique por qué importa "
              "usar bien la IA. Guarda el correo o el acta: es la prueba."),
    "5.1.e": ("Comprobar que funciona.",
              "Se marca solo al hacer la revisión por la dirección (9.3), que es donde la dirección mira si el sistema "
              "da resultados."),
    "5.1.f": ("Apoyar a quien lo lleva.",
              "Se marca solo al completar la 5.3 (quién es responsable de qué) y la 7.2 (formación)."),
    "5.1.g": ("Empujar la mejora.",
              "Se marca solo al completar la 10.1 (mejora continua) y la 10.2 (fallos y cómo se corrigen)."),
    "5.1.h": ("Apoyar a los demás responsables.",
              "Que la dirección ayude a los jefes de cada área a llevar la IA en lo suyo. Por ejemplo: una reunión con "
              "los responsables de área para repasar cómo usa la IA cada uno, con su acta, o un correo delegando en "
              "ellos."),
    "5.2.a": ("Que esté hecha para vuestra empresa, no copiada.",
              "Tiene que nombrar la IA que usáis de verdad y para qué (por ejemplo, «usamos ChatGPT para redactar "
              "ofertas»). Comprobación: si cambias el nombre de la empresa y el texto sirve igual para otra, es "
              "demasiado genérica."),
    "5.2.b": ("Que de ella salgan los objetivos de IA.",
              "Los objetivos que fijéis cada año (requisito 6.2) tienen que poder explicarse con algo que dice la "
              "política. Por ejemplo, si la política dice «lo que hace la IA lo revisa siempre una persona», un objetivo "
              "puede ser «que toda la plantilla sepa revisar lo que hace la IA antes de fin de año»."),
    "5.2.c": ("Que diga que cumpliréis las leyes y los contratos.",
              "Una frase que lo diga claro, por ejemplo: «Nos comprometemos a cumplir las leyes que afectan a nuestra IA, "
              "como el Reglamento europeo de IA y la protección de datos, y lo pactado con clientes y proveedores». La "
              "plantilla ya la trae."),
    "5.2.d": ("Que diga que la iréis mejorando.",
              "Una frase como «La dirección se compromete a mejorar de forma continua el sistema de gestión de la IA y lo "
              "revisa cada año». La plantilla ya la trae."),
    "5.2.e": ("Que la firme la dirección.",
              "Quien dirige la empresa la firma, con la fecha y el número de versión. Vale la firma en el propio "
              "documento o el acta de la reunión donde se aprobó."),
    "5.2.f": ("Que la plantilla sepa que existe y dónde está.",
              "Guardadla en un sitio que todos puedan abrir (por ejemplo, una carpeta compartida de Teams) y mandad un "
              "correo a toda la plantilla con el enlace: ese correo es la prueba. Si el auditor pregunta a cualquiera, "
              "tiene que saber contestar «sí, está en…»."),
    "5.3.a": ("Nombrar al responsable.",
              "Una persona que se encarga de que todo esto cumpla la norma. Basta un documento o un correo de la "
              "dirección: «Nombramos a Ana García responsable del sistema de gestión de la IA». En una empresa pequeña "
              "suele ser quien lleva la ISO."),
    "5.3.b": ("Quién informa a la dirección.",
              "Quién le cuenta a la dirección cómo va todo y cada cuánto. Suele ser el mismo responsable del punto a: "
              "entonces basta con añadirlo a su nombramiento («informará a la dirección cada tres meses»)."),
    "5.3.c": ("Repartir el resto y que se sepa.",
              "Una tabla con quién hace cada cosa (quién revisa los riesgos, quién da la formación, quién atiende las "
              "incidencias…) y un correo a esas personas con la tabla. El correo es la prueba de que se ha comunicado."),
}

CASI_SIEMPRE = ["A.2.2", "A.2.4", "A.3.2", "A.3.3", "A.4.2", "A.4.6", "A.5.2", "A.5.3", "A.9.2", "A.9.3", "A.9.4"]
# Los datos generales de la empresa, para los borradores: (clave, qué se pregunta, ejemplo)
DATOS_EMPRESA = [
    ("nombre", "Nombre de la empresa", "Ejemplo, S.L."),
    ("actividad", "A qué se dedica", "Software de reservas para hoteles"),
    ("tamaño", "Tamaño aproximado", "Unas 40 personas"),
    ("direccion", "Quién es la dirección que aprueba", "La directora general"),
]

# Las preguntas abiertas del cuestionario: para que la IA sepa cómo es la empresa
# y redacte los borradores. Se contestan en llano. Por bloques: (número, título); y cada pregunta:
# (bloque, clave, pregunta, ejemplo de respuesta, requisitos cuyos borradores la usan más, que se proponen reabrir si
# cambia la respuesta)
BLOQUES = [
    (1, "La empresa y la IA"),
    (2, "Personas"),
    (3, "Clientes, leyes y proveedores"),
    (4, "Cómo trabajáis"),
    (5, "Si desarrolláis IA"),
]
# El bloque que solo sale si la respuesta a «desarrolla» no es «No»
SOLO_SI_DESARROLLA = 5
ABIERTAS = [
    (1, "uso", "¿Para qué usáis la IA y qué os aporta?",
     "Un asistente en la web que contesta a los huéspedes, y ChatGPT para redactar correos. Ahorra tiempo al equipo de "
     "atención.", ["4.1", "5.2", "6.2"]),
    (1, "riesgos", "¿Qué os preocupa de la IA? ¿Qué podría salir mal?",
     "Que el asistente dé precios equivocados o que alguien pegue datos de clientes en ChatGPT.",
     ["6.1.2", "5.2", "A.5.2"]),
    (2, "responsables", "¿Quién lleva el tema de la IA en el día a día, y quién decide?",
     "Lo lleva Ana (operaciones); decide la directora general.", ["5.3", "A.3.2"]),
    (2, "participan", "¿Quién más participa? (técnicos, protección de datos, seguridad, legal…)",
     "El equipo de desarrollo (3 personas), un DPO externo y la gestoría para contratos.", ["5.3", "A.3.2", "7.1"]),
    (2, "formacion", "¿Cuánto sabe la plantilla de IA? ¿Habéis dado alguna formación?",
     "Poco; una charla de una hora el año pasado sobre ChatGPT.", ["7.2", "7.3", "4.1"]),
    (2, "auditoria", "¿Quién haría la auditoría interna?",
     "Una consultora de fuera, o alguien de calidad que no lleve la IA.", ["9.2"]),
    (3, "clientes_cert", "¿Quiénes son vuestros clientes, y quién os pide la certificación?",
     "Hoteles. Nos la piden en dos concursos públicos y algún cliente grande.", ["4.1", "4.2", "6.2", "A.10.4"]),
    (3, "datos_personales", "¿Qué datos personales o confidenciales pasan por la IA?",
     "Nombre, correo y fechas de reserva de los huéspedes.", ["4.1", "A.7.3", "6.1.4"]),
    (3, "proveedores_ia", "¿De qué proveedores de IA dependéis y qué tenéis firmado con ellos?",
     "OpenAI (cuenta de empresa, sin entrenar con nuestros datos).", ["A.10.2", "A.10.3", "4.1"]),
    (4, "normas", "¿Qué otras normas o políticas tenéis ya? (ISO 27001, 9001, privacidad…)",
     "ISO 27001 desde 2024 y una política de privacidad.", ["A.2.3", "5.2", "7.5"]),
    (4, "comunicacion", "¿Cómo comunicáis las cosas a la plantilla, y cómo se avisa de un problema con la IA?",
     "Por correo y en la reunión de los lunes; los problemas, a Ana por Teams.", ["7.4", "A.3.3", "10.2"]),
    (4, "revision", "¿Cómo revisáis cómo va todo? (reuniones, cada cuánto, quién)",
     "Comité de dirección una vez al trimestre.", ["9.1", "9.3", "10.1"]),
    (5, "desarrollo", "¿Cómo desarrolláis la IA? (quién, con qué herramientas, cómo lo probáis antes de publicarlo)",
     "El equipo de desarrollo, con la API de OpenAI; probamos con 50 preguntas tipo antes de cada versión.",
     ["A.6.1.2", "A.6.1.3", "A.6.2.2", "A.6.2.3", "A.6.2.4"]),
    (5, "vigilancia", "¿Cómo vigiláis la IA una vez en marcha? (registros, quejas, cifras)",
     "Guardamos las conversaciones 90 días y revisamos las quejas cada semana.", ["A.6.2.6", "A.6.2.8", "9.1"]),
    (5, "origen_datos", "¿De dónde salen los datos que usa la IA y cómo los cuidáis?",
     "De nuestra base de reservas; los revisa desarrollo antes de cada cambio.",
     ["A.7.2", "A.7.3", "A.7.4", "A.7.5", "A.7.6"]),
]

# El eje 2 de cada requisito se calcula a partir de sus puntos, salvo los 🧩 Resumen
_tipos_hijos = {}
for f in P:
    _tipos_hijos.setdefault(f[0], set()).add(f[3])
for n, f in enumerate(filas):
    t = f[6].split()
    if "S" in t or f[0] not in _tipos_hijos:
        continue
    eje3 = [x for x in t if x in ("Pe", "Ev", "U")]
    eje2 = [x for x in ("D", "R", "I", "P") if x in _tipos_hijos[f[0]]]
    filas[n] = f[:6] + (" ".join(eje2 + eje3),) + f[7:]

# Términos de la norma explicados en llano (hoja «Glosario» del Excel)
GLOSARIO = [
    ("Acción correctiva", "Lo que se hace para que un fallo no se repita: buscar su causa y eliminarla. No es lo mismo que corregir el fallo, que es arreglarlo una vez."),
    ("Alcance", "Qué partes de la empresa entran en el sistema de gestión (áreas, procesos, sistemas de IA, sedes). Lo que queda fuera no se audita."),
    ("Alta dirección", "Quien dirige la empresa al más alto nivel (dirección general, gerencia)."),
    ("Anexo A", "La lista de 38 controles de la norma. No todos son obligatorios: cada empresa elige los que le aplican."),
    ("Auditoría de certificación", "La que hace un organismo certificador externo para dar el certificado. Tiene dos etapas: revisión de documentos y comprobación de que se hace lo que dicen."),
    ("Auditoría de vigilancia", "Auditoría anual del certificador, tras certificarse, para comprobar que el sistema sigue funcionando. Revisa una muestra, no todo."),
    ("Auditoría interna", "Revisión que hace la propia empresa (o alguien contratado) para comprobar que cumple la norma, antes de que venga el certificador. Quien audita no puede revisar su propio trabajo."),
    ("Ciclo de vida", "Todas las fases de un sistema de IA: idea, diseño, desarrollo, pruebas, puesta en marcha, uso, mantenimiento y retirada."),
    ("Control", "Una medida concreta para reducir un riesgo (p. ej. revisar por una persona lo que genera la IA antes de publicarlo)."),
    ("Criterios de riesgo", "Las reglas para decidir si un riesgo es aceptable o hay que tratarlo (p. ej. una escala de probabilidad × impacto con un umbral)."),
    ("DAFO", "Análisis de Debilidades, Amenazas, Fortalezas y Oportunidades. Una forma habitual de escribir el contexto de la empresa."),
    ("Declaración de Aplicabilidad", "Documento con los 38 controles del Anexo A: si aplican o no a la empresa y por qué. Es de lo primero que mira el auditor."),
    ("Evaluación de impacto", "Análisis de cómo puede afectar un sistema de IA a las personas, a grupos y a la sociedad (p. ej. si puede discriminar o afectar a la privacidad)."),
    ("Evaluación de riesgos", "Identificar qué puede salir mal con la IA, cómo de probable es y cuánto daño haría, y compararlo con los criterios."),
    ("Evidencia", "Cualquier prueba que demuestra que algo se cumple: un documento, un registro, un correo, lo que responde una persona."),
    ("Información documentada", "El nombre que da la norma a todo lo que está por escrito: documentos y registros."),
    ("Mejora continua", "Que el sistema vaya siendo mejor con el tiempo, no solo que se mantenga."),
    ("No conformidad", "Un incumplimiento de un requisito, detectado en una auditoría o en el día a día. Hay que corregirlo y buscar su causa."),
    ("Partes interesadas", "Todos a los que afecta o interesa el uso de IA de la empresa: clientes, empleados, proveedores, reguladores, accionistas…"),
    ("Política de IA", "Documento aprobado por la dirección que dice cómo se compromete la empresa a usar y desarrollar la IA de forma responsable."),
    ("Procedimiento", "Descripción por escrito de cómo se hace algo: quién, cuándo, qué pasos."),
    ("Proveedor / tercero", "Otra empresa que aporta algo al sistema de IA: un modelo, datos, una herramienta, un servicio en la nube."),
    ("Registro", "Constancia de que algo se ha hecho: un acta, un informe, una lista de asistencia, un historial."),
    ("Registro de eventos (logs)", "Lo que un programa apunta automáticamente cada vez que pasa algo, para poder investigar después."),
    ("Revisión por la dirección", "Reunión periódica (normalmente anual) en la que la dirección repasa cómo va el sistema y decide mejoras y cambios."),
    ("Riesgo residual", "El riesgo que queda después de aplicar las medidas. Alguien con autoridad tiene que aceptarlo."),
    ("Sesgo", "Cuando un sistema de IA trata de forma distinta o injusta a unas personas o grupos, normalmente por los datos con que se hizo."),
    ("Sistema de gestión (SGIA)", "La forma organizada en que la empresa gestiona su uso de la IA: responsables, reglas, revisiones periódicas y corrección de fallos. No es un programa: es cómo se trabaja."),
    ("Sistema de IA", "Un programa o función que usa inteligencia artificial, sea desarrollado por la empresa o de un proveedor."),
    ("Supervisión humana", "Que una persona pueda revisar, corregir o anular lo que decide la IA."),
]


def circulos():
    """Grupos de requisitos que dependen unos de otros en círculo a través de «Se apoya en».

    Un requisito depende de otro si alguno de sus puntos se apoya en él. Si hay un círculo,
    ninguno de sus requisitos se podría completar nunca (cada uno espera al otro).
    """
    grafo = {f[0]: set() for f in filas}
    for f in P:
        grafo[f[0]].update(x.strip() for x in f[5].split(",") if x.strip())
    # Componentes fuertemente conexas (Tarjan), en forma iterativa
    indice, bajo, pila, en_pila, grupos, n = {}, {}, [], set(), [], 0
    for raiz in grafo:
        if raiz in indice:
            continue
        trabajo = [(raiz, iter(sorted(grafo[raiz])))]
        indice[raiz] = bajo[raiz] = n; n += 1
        pila.append(raiz); en_pila.add(raiz)
        while trabajo:
            v, hijos = trabajo[-1]
            w = next(hijos, None)
            if w is not None:
                if w not in indice:
                    indice[w] = bajo[w] = n; n += 1
                    pila.append(w); en_pila.add(w)
                    trabajo.append((w, iter(sorted(grafo[w]))))
                elif w in en_pila:
                    bajo[v] = min(bajo[v], indice[w])
                continue
            trabajo.pop()
            if trabajo:
                bajo[trabajo[-1][0]] = min(bajo[trabajo[-1][0]], bajo[v])
            if bajo[v] == indice[v]:
                grupo = []
                while True:
                    w = pila.pop(); en_pila.discard(w); grupo.append(w)
                    if w == v:
                        break
                if len(grupo) > 1 or v in grafo[v]:
                    grupos.append(sorted(grupo))
    return grupos


def comprobar():
    """Comprueba que los datos de la guía son coherentes. Falla con un AssertionError si no."""
    codigos = [f[0] for f in filas]
    assert len(codigos) == len(set(codigos)), "códigos repetidos"
    for f in filas:
        t = f[6].split()
        assert set(t) <= set(TIPOS), f[0]
        assert any(x in t for x in "D R I P S".split()), f"{f[0]} sin eje 2"
        if "S" not in t:
            assert any(x in t for x in "Pe Ev U".split()), f"{f[0]} sin eje 3"
    assert set(CUANDO) == {a[0] for a in A}, "falta o sobra la ayuda de algún control"

    cods_p = [f[1] for f in P]
    assert len(cods_p) == len(set(cods_p)), "puntos repetidos"
    for f in P:
        assert f[0] in codigos, f"{f[1]}: padre inexistente"
        assert f[3] in NOMBRE, f[1]
        for ref in filter(None, (x.strip() for x in f[5].split(","))):
            assert ref in codigos, f"{f[1]}: se apoya en {ref}, que no existe"
    assert len(_TODOS) + len(_PRODUCTO) == len(POR_SISTEMA), "punto en Todos y en Solo producto"
    for c in POR_SISTEMA:
        assert c in cods_p, f"por sistema: {c} no existe"
    assert not circulos(), f"requisitos que dependen unos de otros en círculo: {circulos()}"

    claves = [s[0] for s in SITUACIONES]
    assert len(claves) == len(set(claves)), "situaciones repetidas"
    for clave, _, _, reqs in SITUACIONES + [("alta", "", "", AL_DAR_DE_ALTA)]:
        assert len(reqs) == len(set(reqs)), f"situación {clave}: requisito repetido"
        for r in reqs:
            assert r in codigos, f"situación {clave}: {r} no existe"
    # Todo requisito «por evento» se reabre de alguna forma: con una situación, al dar
    # de alta un sistema, o solo, porque tiene puntos por sistema
    en_alguna = {r for s in SITUACIONES for r in s[3]} | set(AL_DAR_DE_ALTA) | {f[0] for f in P if f[1] in POR_SISTEMA}
    for f in filas:
        assert "Ev" not in f[6].split() or f[0] in en_alguna, f"{f[0]} es por evento y nada lo reabre"

    # Cuestionario: cada control del Anexo A se decide con alguna pregunta o aplica casi siempre
    claves = [q[0] for q in PREGUNTAS]
    assert len(claves) == len(set(claves)), "preguntas repetidas"
    controles = {a[0] for a in A}
    por_pregunta = {c for q in PREGUNTAS for c in q[2]}
    assert por_pregunta <= controles and set(CASI_SIEMPRE) <= controles, "el cuestionario nombra un control que no existe"
    assert not por_pregunta & set(CASI_SIEMPRE), "un control está en una pregunta y en «casi siempre»"
    assert set(LLANO) <= {f[0] for f in filas}, "una explicación en llano de un requisito que no existe"
    assert set(LLANO_PUNTOS) <= {f[1] for f in P}, "una explicación en llano de un punto que no existe"
    assert por_pregunta | set(CASI_SIEMPRE) == controles, f"controles sin pregunta: {controles - por_pregunta - set(CASI_SIEMPRE)}"

    # Las preguntas abiertas: claves sin repetir (ni con las de Sí/No ni los datos), en un bloque que existe y
    # con requisitos que existen
    claves = [q[1] for q in ABIERTAS]
    assert len(claves) == len(set(claves)), "preguntas abiertas repetidas"
    assert not set(claves) & ({q[0] for q in PREGUNTAS} | {d[0] for d in DATOS_EMPRESA}), "clave abierta ya usada"
    bloques = {b for b, _ in BLOQUES}
    for b, clave, _, ejemplo, reqs in ABIERTAS:
        assert b in bloques and ejemplo, f"pregunta abierta {clave}: bloque o ejemplo"
        assert reqs and set(reqs) <= set(codigos), f"pregunta abierta {clave}: requisito que no existe"


def resumen():
    """Las cifras de la guía, en texto, para mostrarlas al generar el Excel."""
    return "\n".join([
        f"cláusulas: {len(C)} | anexo A: {len(A)} | total: {len(filas)} | dudosas: {sum(f[7] for f in filas)}",
        str({x: sum(x in f[6].split() for f in filas) for x in TIPOS}),
        f"puntos: {len(P)} | padres con puntos: {len(set(f[0] for f in P))} | "
        f"por sistema: {len(_TODOS)} todos + {len(_PRODUCTO)} solo producto",
    ])
