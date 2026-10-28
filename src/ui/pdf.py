"""Generación de propuestas de convalidación en PDF."""

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

from src.ui.seleccion import calcular_ects, obtener_propuesta


class DatosAlumno(TypedDict):
    nombre: str
    grado: str
    universidad: str


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

    for indice, resultado in enumerate(convalidaciones):
        grupo = resultado.get("grupo")
        if grupo is None:
            propuestas.append([resultado])
        elif grupo not in grupos_vistos:
            propuestas.append(obtener_propuesta(convalidaciones, indice))
            grupos_vistos.add(grupo)

    return propuestas


def generar_pdf(
    datos_alumno: DatosAlumno,
    convalidaciones_seleccionadas: Sequence[dict],
) -> bytes:
    """Genera una propuesta en PDF a partir de los datos del alumno y filas seleccionadas."""
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
        Paragraph("<b>Asignaturas UC3M</b>", estilos["BodyText"]),
        Paragraph("<b>ECTS UC3M</b>", estilos["BodyText"]),
        Paragraph("<b>Asignaturas destino</b>", estilos["BodyText"]),
        Paragraph("<b>ECTS destino</b>", estilos["BodyText"]),
        Paragraph("<b>Etiqueta</b>", estilos["BodyText"]),
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

    if not propuestas:
        contenido.append(
            Paragraph("No hay asignaturas seleccionadas.", estilos["BodyText"])
        )

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
