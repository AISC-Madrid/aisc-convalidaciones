"""Tests de la lógica de resultados: agrupar, ordenar, filtrar y selección vacía.

Usan objetos sencillos con los mismos campos que el JSON, así no dependen
de los modelos Pydantic.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import resultados  # noqa: E402

IA = "SUGERENCIA_IA"
PRE = "PRECEDENTE_APROBADO"


def fila(origen, destino, etiqueta, score, grupo=None):
    return SimpleNamespace(
        origen=SimpleNamespace(codigo=origen[0], nombre=origen[1]),
        destino=SimpleNamespace(codigo=destino[0], nombre=destino[1]),
        etiqueta=etiqueta,
        score=score,
        grupo=grupo,
    )


REDES = fila(("18215", "Redes de Ordenadores"), ("CS 3251", "Computer Networking I"), IA, 0.79)
EDA = fila(("18201", "Estructuras de Datos"), ("CS 1332", "Data Structures"), PRE, 0.80)
SO = fila(("18210", "Sistemas Operativos"), ("CS 2200", "Computer Systems"), PRE, 0.90)
CALC_1 = fila(("15526", "Cálculo I"), ("MATH 1552", "Integral Calculus"), PRE, 0.70, grupo=1)
CALC_2 = fila(("15531", "Cálculo II"), ("MATH 1552", "Integral Calculus"), PRE, 0.75, grupo=1)
FILAS = [REDES, CALC_1, EDA, SO, CALC_2]


def test_agrupar_junta_las_filas_del_mismo_grupo():
    bloques = resultados.agrupar(FILAS)
    assert [CALC_1, CALC_2] in bloques
    assert len(bloques) == 4


def test_ordenar_precedentes_primero_y_por_score():
    ordenados = resultados.ordenar(resultados.agrupar(FILAS))
    assert ordenados == [[SO], [EDA], [CALC_1, CALC_2], [REDES]]


def test_filtrar_por_nombre_sin_tildes():
    bloques = resultados.agrupar(FILAS)
    assert resultados.filtrar(bloques, "sistemas operativos") == [[SO]]


def test_filtrar_por_codigo_de_destino_sin_espacio():
    bloques = resultados.agrupar(FILAS)
    assert resultados.filtrar(bloques, "cs3251") == [[REDES]]


def test_filtrar_mantiene_el_grupo_entero():
    bloques = resultados.agrupar(FILAS)
    assert resultados.filtrar(bloques, "calculo ii") == [[CALC_1, CALC_2]]


def test_filtrar_vacio_devuelve_todo_y_sin_coincidencias_nada():
    bloques = resultados.agrupar(FILAS)
    assert resultados.filtrar(bloques, "") == bloques
    assert resultados.filtrar(bloques, "astrofisica") == []


def test_no_descarga_sin_seleccion():
    assert "Selecciona" in resultados.motivo_no_descarga([], "Ana")


def test_no_descarga_sin_nombre():
    assert "nombre" in resultados.motivo_no_descarga([SO], "   ")


def test_descarga_con_seleccion_y_nombre():
    assert resultados.motivo_no_descarga([SO], "Ana") is None