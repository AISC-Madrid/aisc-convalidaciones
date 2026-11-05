"""Generación de propuestas de convalidación en PDF para la aplicación web."""

from collections.abc import Sequence
from datetime import date
from html import escape
from io import BytesIO
from typing import TypedDict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

class DatosAlumno(TypedDict):
    nombre: str
    grado: str
    universidad: str


def calcular_ects(resultados):
    """Suma créditos sin duplicar asignaturas dentro de una propuesta."""
    origen = {}
    destino = {}
    for resultado in resultados:
        origen[resultado["origen"]["codigo"]] = resultado["origen"]["ects"]
        destino[resultado["destino"]["codigo"]] = resultado["destino"]["ects"]
    return sum(origen.values()), sum(destino.values())


def _texto_asignaturas(propuesta: Sequence[dict], lado: str) -> Paragraph:
    asignaturas = {}
    for resultado in propuesta:
        asignatura = resultado[lado]
        asignaturas[asignatura["codigo"]] = asignatura
    lineas = [
        f"{escape(asignatura['nombre'])} ({escape(asignatura['codigo'])})"
        for asignatura in asignaturas.values()
    ]
    return Paragraph("<br/>".join(lineas), getSampleStyleSheet()["BodyText"])


def _etiqueta(propuesta: Sequence[dict]) -> str:
    nombres = {
        "PRECEDENTE_APROBADO": "Precedente aprobado",
        "SUGERENCIA_IA": "Sugerencia IA",
    }
    etiquetas = dict.fromkeys(resultado["etiqueta"] for resultado in propuesta)
    return ", ".join(nombres[etiqueta] for etiqueta in etiquetas)


def _propuestas_seleccionadas(convalidaciones: Sequence[dict]) -> list[list[dict]]:
    propuestas = []
    grupos_vistos = set()
    for resultado in convalidaciones:
        grupo = resultado.get("grupo")
        if grupo is None:
            propuestas.append([resultado])
        elif grupo not in grupos_vistos:
            propuestas.append(
                [
                    fila
                    for fila in convalidaciones
                    if fila.get("grupo") == grupo
                ]
            )
            grupos_vistos.add(grupo)
    return propuestas


def generar_pdf(
    datos_alumno: DatosAlumno,
    convalidaciones_seleccionadas: Sequence[dict],
) -> bytes:
    """Genera un PDF a partir del alumno y las propuestas seleccionadas."""
    buffer = BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title="Propuesta de convalidación",
    )
    estilos = getSampleStyleSheet()
    estilo_cabecera = ParagraphStyle(
        "Cabecera", parent=estilos["BodyText"], textColor=colors.white
    )
    contenido = [
        Paragraph("Propuesta de convalidación", estilos["Title"]),
        Paragraph(f"<b>Alumno:</b> {escape(datos_alumno['nombre'])}", estilos["BodyText"]),
        Paragraph(f"<b>Grado:</b> {escape(datos_alumno['grado'])}", estilos["BodyText"]),
        Paragraph(
            f"<b>Universidad de destino:</b> {escape(datos_alumno['universidad'])}",
            estilos["BodyText"],
        ),
        Paragraph(f"<b>Fecha:</b> {date.today():%d/%m/%Y}", estilos["BodyText"]),
    ]
    encabezado = [
        Paragraph("<b>Asignaturas UC3M</b>", estilo_cabecera),
        Paragraph("<b>ECTS UC3M</b>", estilo_cabecera),
        Paragraph("<b>Asignaturas destino</b>", estilo_cabecera),
        Paragraph("<b>ECTS destino</b>", estilo_cabecera),
        Paragraph("<b>Etiqueta</b>", estilo_cabecera),
    ]
    filas = [encabezado]
    propuestas = _propuestas_seleccionadas(convalidaciones_seleccionadas)
    for propuesta in propuestas:
        ects_origen, ects_destino = calcular_ects(propuesta)
        filas.append(
            [
                _texto_asignaturas(propuesta, "origen"),
                f"{ects_origen:g}",
                _texto_asignaturas(propuesta, "destino"),
                f"{ects_destino:g}",
                Paragraph(escape(_etiqueta(propuesta)), estilos["BodyText"]),
            ]
        )

    tabla = Table(
        filas,
        colWidths=[7.5 * cm, 2.2 * cm, 8.2 * cm, 2.2 * cm, 6.8 * cm],
        repeatRows=1,
        hAlign="LEFT",
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7C9D6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("ALIGN", (3, 1), (3, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6FA")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    contenido.append(tabla)

    ects_origen, ects_destino = calcular_ects(convalidaciones_seleccionadas)
    contenido.extend(
        [
            Paragraph(
                f"<b>Totales seleccionados:</b> {ects_origen:g} ECTS UC3M · "
                f"{ects_destino:g} ECTS destino",
                estilos["BodyText"],
            ),
            Paragraph(
                "Documento orientativo. La propuesta debe ser revisada y aprobada por el tutor.",
                estilos["Italic"],
            ),
        ]
    )
    documento.build(contenido)
    return buffer.getvalue()
