from pathlib import Path

import pytest

from src.scrapers.uc3m_parser import normalizar_titulo, parse_ficha

FIXTURES = Path(__file__).parent / "fixtures" / "uc3m"
FICHAS = sorted(FIXTURES.glob("*.html"))

CLAVES = {
    "codigo",
    "nombre",
    "plan",
    "estudio",
    "curso_academico",
    "tipo",
    "creditos",
    "curso",
    "cuatrimestre",
    "coordinador",
    "departamento",
    "rama",
    "requisitos",
    "objetivos",
    "resultados",
    "programa",
    "bibliografia_basica",
    "idioma",
    "fecha_actualizacion",
}


def _ficha(nombre: str) -> dict:
    return parse_ficha((FIXTURES / nombre).read_bytes())


def test_hay_fixtures():
    assert len(FICHAS) == 11


def test_algebra_lineal_es():
    ficha = _ficha("15363_2026_ES.html")

    assert set(ficha) == CLAVES
    assert ficha["codigo"] == "15363"
    assert ficha["nombre"] == "Álgebra Lineal"
    assert ficha["curso_academico"] == "2026/2027"
    assert ficha["tipo"] == "FB"
    assert ficha["creditos"] == 6.0
    assert ficha["curso"] == 1
    assert ficha["cuatrimestre"] == 1
    assert ficha["plan"] == "456"
    assert ficha["estudio"] == "371"
    assert ficha["objetivos"]
    assert ficha["programa"]
    assert ficha["idioma"] == "ES"
    assert ficha["fecha_actualizacion"] == "14/04/2026 14:17:35"
    assert ficha["departamento"] == "Departamento de Matemáticas"
    assert ficha["rama"] == "Ingeniería y Arquitectura"
    assert ficha["requisitos"] is None
    assert "Números complejos" in ficha["programa"]
    assert "\n" in ficha["programa"]


def test_algebra_lineal_en():
    ficha = _ficha("15363_2026_EN.html")

    assert ficha["idioma"] == "EN"
    assert ficha["nombre"] == "Linear Algebra"
    assert ficha["programa"]
    assert ficha["tipo"] == "FB"
    assert ficha["creditos"] == 6.0
    assert ficha["cuatrimestre"] == 1
    assert ficha["fecha_actualizacion"] == "14/04/2026 14:17:35"


@pytest.mark.parametrize("idioma", ["ES", "EN"])
def test_curso_de_humanidades(idioma):
    ficha = _ficha(f"11692_2026_{idioma}.html")

    assert ficha["tipo"] == "HUM"
    assert ficha["idioma"] == idioma
    # La ficha real de 11692 sí trae Objetivos y declara 3 ECTS, pero no cuatrimestre.
    assert ficha["creditos"] == 3.0
    assert ficha["cuatrimestre"] is None
    assert ficha["resultados"] is None
    assert ficha["rama"] is None


@pytest.mark.parametrize("nombre", ["13881_2026_ES.html", "17631_2026_EN.html"])
def test_ficha_sin_objetivos(nombre):
    ficha = _ficha(nombre)

    assert ficha["objetivos"] is None
    assert ficha["tipo"] == "OB"
    assert ficha["requisitos"]


def test_otro_grado_derecho():
    ficha = _ficha("13565_2026_ES.html")

    assert ficha["nombre"] == "Constitución y sistema de fuentes"
    assert ficha["plan"] == "557"
    assert ficha["estudio"] == "206"
    assert ficha["tipo"] == "FB"


@pytest.mark.parametrize("ruta", FICHAS, ids=[f.name for f in FICHAS])
def test_todas_las_fichas_se_parsean(ruta):
    ficha = parse_ficha(ruta.read_bytes())

    assert set(ficha) == CLAVES
    assert ficha["codigo"].isdigit()
    assert ruta.name.startswith(ficha["codigo"])
    assert ficha["nombre"]
    assert ficha["programa"]
    assert ficha["idioma"] == ruta.stem.split("_")[-1]
    assert "\ufffd" not in ficha["nombre"]


def test_ficha_antigua_2024():
    ficha = _ficha("15363_2024_ES.html")

    assert ficha["curso_academico"] == "2024/2025"
    assert ficha["nombre"] == "Álgebra Lineal"
    assert ficha["programa"]


def test_acepta_str_y_bytes_por_igual():
    contenido = (FIXTURES / "15363_2026_ES.html").read_bytes()

    assert parse_ficha(contenido.decode("utf-8")) == parse_ficha(contenido)


def test_bytes_iso_8859_1_declarados():
    html = (
        '<html><head><meta charset="iso-8859-1"></head><body>'
        '<div class="asignatura">Álgebra</div><div class="asignatura">(1)</div>'
        "</body></html>"
    ).encode("iso-8859-1")

    ficha = parse_ficha(html)

    assert ficha["nombre"] == "Álgebra"
    assert ficha["programa"] is None
    assert ficha["tipo"] is None


def test_tipo_desconocido_se_devuelve_tal_cual():
    html = (
        '<div class="asignatura">X</div><div class="asignatura">(7)</div>'
        "<div><strong>Tipo:</strong> Trabajo Fin de Grado</div>"
        "<div><strong>Cuatrimestre:</strong> Anual</div>"
    )

    ficha = parse_ficha(html)

    assert ficha["tipo"] == "Trabajo Fin de Grado"
    assert ficha["cuatrimestre"] is None


def test_html_que_no_es_ficha_lanza_value_error():
    with pytest.raises(ValueError):
        parse_ficha("<html></html>")


def test_normalizar_titulo():
    assert normalizar_titulo("  Descripción de contenidos:\n Programa ") == (
        "descripcion de contenidos: programa"
    )
    assert normalizar_titulo("Última actualización:") == "ultima actualizacion"
