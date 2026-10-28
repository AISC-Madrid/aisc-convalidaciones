from src.ui.pdf import _propuestas_seleccionadas, generar_pdf
from src.ui.seleccion import calcular_ects


def test_generar_pdf_con_grupo_conjunto():
    seleccion = [
        {
            "origen": {"codigo": "001", "nombre": "Redes", "ects": 6},
            "destino": {"codigo": "CS1", "nombre": "Networks A", "ects": 4.5},
            "etiqueta": "PRECEDENTE_APROBADO",
            "grupo": 1,
        },
        {
            "origen": {"codigo": "001", "nombre": "Redes", "ects": 6},
            "destino": {"codigo": "CS2", "nombre": "Networks B", "ects": 4.5},
            "etiqueta": "PRECEDENTE_APROBADO",
            "grupo": 1,
        },
    ]
    datos_alumno = {
        "nombre": "Alumna de prueba",
        "grado": "Ingeniería Informática",
        "universidad": "Universidad de ejemplo",
    }

    propuestas = _propuestas_seleccionadas(seleccion)
    pdf = generar_pdf(datos_alumno, seleccion)

    assert len(propuestas) == 1
    assert calcular_ects(propuestas[0]) == (6, 9)
    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")
