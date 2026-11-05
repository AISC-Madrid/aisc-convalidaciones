"""Tests del cálculo de créditos y de la agrupación del PDF.

Vienen de tests/test_seleccion.py (la web antigua de src/ui), adaptados a web/pdf.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pdf  # noqa: E402


def fila(origen, ects_origen, destino, ects_destino, grupo=None):
    return {
        "origen": {"codigo": origen, "ects": ects_origen},
        "destino": {"codigo": destino, "ects": ects_destino},
        "grupo": grupo,
    }


def test_seleccion_vacia():
    assert pdf.calcular_ects([]) == (0, 0)


def test_una_equivalencia_individual():
    assert pdf.calcular_ects([fila("001", 6, "CS1301", 4.5)]) == (6, 4.5)


def test_no_duplica_creditos_de_origen():
    resultados = [fila("001", 6, "CS1301", 4.5), fila("001", 6, "CS1331", 4.5)]
    assert pdf.calcular_ects(resultados) == (6, 9)


def test_no_duplica_creditos_de_destino():
    resultados = [fila("001", 3, "CS1301", 6), fila("002", 3, "CS1301", 6)]
    assert pdf.calcular_ects(resultados) == (6, 6)


def test_grupo_nm_sin_duplicar_creditos():
    resultados = [
        fila("001", 3, "CS1301", 4.5),
        fila("001", 3, "CS1331", 4.5),
        fila("002", 6, "CS1301", 4.5),
        fila("002", 6, "CS1331", 4.5),
    ]
    assert pdf.calcular_ects(resultados) == (9, 9)


def test_propuestas_individuales_no_se_agrupan():
    a, b = fila("001", 6, "CS1", 6), fila("002", 6, "CS2", 6)
    assert pdf._propuestas_seleccionadas([a, b]) == [[a], [b]]


def test_grupo_es_una_sola_propuesta_aunque_sus_filas_no_vayan_seguidas():
    parte_a = fila("001", 3, "CS1", 6, grupo=1)
    individual = fila("002", 6, "CS2", 6)
    parte_b = fila("003", 3, "CS1", 6, grupo=1)
    assert pdf._propuestas_seleccionadas([parte_a, individual, parte_b]) == [
        [parte_a, parte_b],
        [individual],
    ]