"""Parser sobre fichas sintéticas (texto inventado, misma estructura HTML que las reales).

A diferencia de ``test_uc3m_parser.py``, estas fixtures se suben al repo y corren en la CI.
"""

from pathlib import Path

import pytest

from src.scrapers.uc3m_parser import parse_ficha

SINTETICAS = Path(__file__).parent / "fixtures" / "uc3m" / "sinteticas"
FICHAS = sorted(SINTETICAS.glob("*.html"))


def _ficha(nombre: str) -> dict:
    return parse_ficha((SINTETICAS / nombre).read_bytes())


def test_hay_fixtures_sinteticas():
    assert len(FICHAS) == 5


def test_ficha_completa_es():
    ficha = _ficha("10001_2026_ES.html")

    assert ficha["codigo"] == "10001"
    assert ficha["nombre"] == "Matemáticas Inventadas"
    assert (ficha["plan"], ficha["estudio"]) == ("900", "90")
    assert ficha["curso_academico"] == "2026/2027"
    assert ficha["tipo"] == "FB"
    assert ficha["creditos"] == 6.0
    assert (ficha["curso"], ficha["cuatrimestre"]) == (1, 2)
    assert ficha["coordinador"] == "PRUEBA , PERSONA"
    assert ficha["departamento"] == "Departamento de Matemáticas"
    assert ficha["rama"] == "Ingeniería y Arquitectura"
    assert ficha["objetivos"].startswith("El estudiante aprenderá a:\n\n1- Sumar")
    assert ficha["resultados"] == "R1: Capacidad para resolver problemas de prueba."
    assert ficha["programa"] == (
        "1. Números inventados\n- Definición\n- Operaciones básicas\n2. Ecuaciones de prueba"
    )
    assert ficha["bibliografia_basica"].count("\n") == 1
    assert ficha["requisitos"] is None
    assert ficha["idioma"] == "ES"
    assert ficha["fecha_actualizacion"] == "01/02/2026 10:00:00"


def test_ficha_completa_en():
    ficha = _ficha("10001_2026_EN.html")

    assert ficha["nombre"] == "Invented Mathematics"
    assert ficha["idioma"] == "EN"
    assert ficha["tipo"] == "FB"
    assert (ficha["curso"], ficha["cuatrimestre"]) == (1, 2)
    assert ficha["rama"] == "Engineering and Architecture"
    assert ficha["programa"] == "1. Invented numbers\n2. Test equations"


def test_ficha_sin_objetivos_con_requisitos():
    ficha = _ficha("10002_2026_EN.html")

    assert ficha["objetivos"] is None
    assert ficha["resultados"] is None
    assert ficha["requisitos"] == "- Invented Programming (1st year)"
    assert ficha["tipo"] == "OB"
    assert (ficha["plan"], ficha["estudio"]) == ("901", "91")


def test_ficha_de_humanidades_sin_curso_ni_cuatrimestre():
    ficha = _ficha("10003_2026_ES.html")

    assert ficha["tipo"] == "HUM"
    assert ficha["creditos"] == 3.0
    assert ficha["curso"] is None
    assert ficha["cuatrimestre"] is None
    assert ficha["rama"] is None
    assert ficha["nombre"].startswith("¿Qué es una prueba?")


def test_ficha_de_un_curso_anterior_con_seccion_vacia():
    ficha = _ficha("10001_2024_ES.html")

    assert ficha["curso_academico"] == "2024/2025"
    assert ficha["creditos"] == 6.0
    assert ficha["resultados"] is None
    assert ficha["coordinador"] is None
    assert ficha["programa"]


@pytest.mark.parametrize("ruta", FICHAS, ids=[f.name for f in FICHAS])
def test_codigo_curso_e_idioma_coinciden_con_el_nombre_del_fichero(ruta):
    codigo, anio, idioma = ruta.stem.split("_")
    ficha = parse_ficha(ruta.read_bytes())

    assert ficha["codigo"] == codigo
    assert ficha["curso_academico"].startswith(anio)
    assert ficha["idioma"] == idioma
    assert ficha["programa"]
