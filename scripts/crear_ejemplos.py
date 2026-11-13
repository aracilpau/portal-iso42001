# Desarrollado en Movired. Licencia PolyForm Internal Use 1.0.0 (solo uso interno; ver LICENSE).
"""Crea los archivos de ejemplo del revisor en tests/archivos/. Empresa inventada (regla 2 de datos).

    .venv\\Scripts\\python scripts\\crear_ejemplos.py

- politica-ia-ejemplo.docx: una política de IA que debería valer para la 5.2 (habla de los sistemas reales de la
  empresa, tiene los compromisos por escrito, marca de dónde salen los objetivos y está aprobada).
- politica-ia-generica.pdf: una política de manual, que valdría para cualquier empresa: no debería valer para la 5.2.a.
"""
from pathlib import Path

from docx import Document
from fpdf import FPDF

DESTINO = Path(__file__).resolve().parent.parent / "tests" / "archivos"

BUENA = [
    ("titulo", "Política de inteligencia artificial de Ejemplo, S.L."),
    ("p", "Versión 1.0 · Aprobada el 12/01/2026 por el director general, Juan Ejemplo Pérez."),
    ("h", "1. Para qué existe esta política"),
    ("p", "Ejemplo, S.L. desarrolla software de reservas para hoteles. Usamos la inteligencia artificial de dos "
          "formas: el Asistente de reservas, integrado en nuestro producto, que responde a los huéspedes en la web "
          "del hotel y les propone habitaciones; y ChatGPT, que la plantilla usa para redactar correos y resúmenes "
          "internos. Esta política dice cómo usamos y desarrollamos esa IA de forma responsable."),
    ("h", "2. Alcance"),
    ("p", "Se aplica al Asistente de reservas en todo su ciclo de vida (diseño, desarrollo, pruebas, puesta en marcha "
          "y funcionamiento) y al uso de ChatGPT por cualquier persona de la empresa. Afecta a las 30 personas de la "
          "plantilla y a los proveedores que intervienen en el Asistente."),
    ("h", "3. Principios"),
    ("li", "Las respuestas del Asistente a los huéspedes se pueden revisar y corregir por una persona del hotel."),
    ("li", "No se introducen en ChatGPT datos personales de huéspedes ni datos confidenciales de los hoteles clientes."),
    ("li", "Antes de poner en marcha un cambio del Asistente se evalúa su impacto en los huéspedes."),
    ("li", "Los datos de reservas que usa el Asistente se tratan según nuestra política de privacidad."),
    ("h", "4. Compromisos"),
    ("p", "La dirección se compromete a cumplir los requisitos aplicables a nuestra IA: las leyes (entre ellas el "
          "Reglamento europeo de IA y la normativa de protección de datos), los contratos con los hoteles clientes y "
          "los requisitos de la norma ISO/IEC 42001."),
    ("p", "La dirección se compromete también a la mejora continua del sistema de gestión de la IA: cada año revisa "
          "cómo funciona y decide qué mejorar."),
    ("h", "5. Objetivos"),
    ("p", "Los objetivos de IA de cada año salen de esta política. Para 2026: que el 100 % de las respuestas del "
          "Asistente que un hotel marca como incorrectas se revisen en menos de 48 horas, y que toda la plantilla "
          "reciba la formación de uso responsable de ChatGPT."),
    ("h", "6. Responsables y revisión"),
    ("p", "La responsable del sistema de gestión de la IA es la directora de producto. La política se revisa cada año "
          "en la revisión por la dirección, o antes si cambia la IA que usamos."),
    ("h", "7. Comunicación"),
    ("p", "La política está publicada en la intranet (sección «Calidad») y se envió a toda la plantilla por correo el "
          "15/01/2026."),
    ("p", "Firmado: Juan Ejemplo Pérez, director general. 12/01/2026."),
]

GENERICA = [
    ("titulo", "Política de Inteligencia Artificial"),
    ("p", "La organización reconoce la importancia de la inteligencia artificial en el mundo actual y apuesta por "
          "un uso ético, responsable y transparente de estas tecnologías."),
    ("h", "Principios"),
    ("li", "Transparencia: se procurará que el uso de la IA sea comprensible."),
    ("li", "Equidad: se intentará evitar los sesgos."),
    ("li", "Seguridad: se tendrán en cuenta los riesgos."),
    ("li", "Privacidad: se respetarán los datos personales."),
    ("h", "Ámbito"),
    ("p", "Esta política es aplicable a todas las actividades de la organización relacionadas con la inteligencia "
          "artificial."),
    ("h", "Responsabilidades"),
    ("p", "Todas las personas de la organización deberán tener en cuenta esta política en su trabajo diario."),
]


def crear_docx(ruta: Path, partes):
    doc = Document()
    for tipo, texto in partes:
        if tipo == "titulo":
            doc.add_heading(texto, level=0)
        elif tipo == "h":
            doc.add_heading(texto, level=1)
        elif tipo == "li":
            doc.add_paragraph(texto, style="List Bullet")
        else:
            doc.add_paragraph(texto)
    doc.save(ruta)


def crear_pdf(ruta: Path, partes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    for tipo, texto in partes:
        if tipo == "titulo":
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 9, texto, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
        elif tipo == "h":
            pdf.set_font("Helvetica", "B", 12)
            pdf.ln(2)
            pdf.multi_cell(0, 7, texto, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, ("- " if tipo == "li" else "") + texto, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(ruta))


if __name__ == "__main__":
    DESTINO.mkdir(parents=True, exist_ok=True)
    crear_docx(DESTINO / "politica-ia-ejemplo.docx", BUENA)
    crear_pdf(DESTINO / "politica-ia-generica.pdf", GENERICA)
    print("Creados en", DESTINO)
