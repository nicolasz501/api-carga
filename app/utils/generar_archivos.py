from io import BytesIO
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


def convertir_valor(valor):
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")

    if valor is None:
        return ""

    return str(valor)


def generar_pdf(datos, titulo, columnas):
    archivo = BytesIO()

    documento = SimpleDocTemplate(
        archivo,
        pagesize=landscape(letter),
        rightMargin=30,
        leftMargin=30,
        topMargin=35,
        bottomMargin=35
    )

    estilos = getSampleStyleSheet()

    encabezado = ParagraphStyle(
        "Encabezado",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#237A45"),
        fontSize=18,
        spaceAfter=10
    )

    elementos = []

    elementos.append(
        Paragraph("CARGA DOCENTE Y EVALUACIÓN DE DESEMPEÑO", encabezado)
    )

    elementos.append(
        Paragraph(titulo, estilos["Heading2"])
    )

    elementos.append(
        Paragraph(
            f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            estilos["Normal"]
        )
    )

    elementos.append(Spacer(1, 20))

    tabla_datos = [columnas]

    for registro in datos:
        fila = [
            convertir_valor(registro.get(columna))
            for columna in columnas
        ]
        tabla_datos.append(fila)

    tabla = Table(
        tabla_datos,
        repeatRows=1,
        hAlign="LEFT"
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#237A45")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            colors.HexColor("#F0F5F1")
        ]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7)
    ]))

    elementos.append(tabla)

    elementos.append(Spacer(1, 15))

    elementos.append(
        Paragraph(
            f"Total de registros: {len(datos)}",
            estilos["Normal"]
        )
    )

    documento.build(elementos)

    archivo.seek(0)
    return archivo


def generar_excel(datos, titulo, columnas):
    archivo = BytesIO()

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Reporte"

    hoja.merge_cells(
        start_row=1,
        start_column=1,
        end_row=1,
        end_column=len(columnas)
    )

    titulo_celda = hoja.cell(row=1, column=1)
    titulo_celda.value = titulo
    titulo_celda.font = Font(
        bold=True,
        size=16,
        color="FFFFFF"
    )
    titulo_celda.fill = PatternFill(
        "solid",
        fgColor="237A45"
    )
    titulo_celda.alignment = Alignment(horizontal="center")

    hoja.merge_cells(
        start_row=2,
        start_column=1,
        end_row=2,
        end_column=len(columnas)
    )

    hoja.cell(
        row=2,
        column=1
    ).value = (
        "Fecha de generación: "
        + datetime.now().strftime("%d/%m/%Y %H:%M")
    )

    for numero, columna in enumerate(columnas, start=1):
        celda = hoja.cell(row=4, column=numero)
        celda.value = columna.replace("_", " ").title()
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = PatternFill("solid", fgColor="237A45")
        celda.alignment = Alignment(horizontal="center")

    for fila_numero, registro in enumerate(datos, start=5):
        for columna_numero, columna in enumerate(columnas, start=1):
            celda = hoja.cell(row=fila_numero, column=columna_numero)
            celda.value = convertir_valor(registro.get(columna))
            celda.alignment = Alignment(vertical="center")

    ultima_fila = 4 + len(datos)

    if datos:
        hoja.auto_filter.ref = (
            f"A4:{get_column_letter(len(columnas))}{ultima_fila}"
        )

    hoja.freeze_panes = "A5"

    for numero, columna in enumerate(columnas, start=1):
        valores = [
            str(hoja.cell(row=fila, column=numero).value or "")
            for fila in range(4, ultima_fila + 1)
        ]

        ancho = max([len(valor) for valor in valores] + [12])
        hoja.column_dimensions[get_column_letter(numero)].width = min(
            ancho + 3, 40
        )

    hoja.cell(
        row=ultima_fila + 2,
        column=1
    ).value = f"Total de registros: {len(datos)}"

    libro.save(archivo)

    archivo.seek(0)
    return archivo