"""Guardar y leer los resultados en las tablas combinaciones y resultados."""

import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.export import resultados_bd
from src.models import Resultados

EJEMPLO = Path(__file__).parent / "fixtures" / "resultados" / "ejemplo.json"


def _ejemplo() -> Resultados:
    return Resultados.model_validate_json(EJEMPLO.read_text(encoding="utf-8"))


@pytest.fixture
def conexion():
    con = sqlite3.connect(":memory:")
    yield con
    con.close()


def test_lo_que_se_guarda_se_lee_igual(conexion):
    original = _ejemplo()
    resultados_bd.guardar(conexion, original)

    leido = resultados_bd.leer(conexion, original.grado, original.universidad)

    assert leido == original


def test_grupos_n_m_y_aviso_ects_sobreviven(conexion):
    original = _ejemplo()
    resultados_bd.guardar(conexion, original)
    leido = resultados_bd.leer(conexion, original.grado, original.universidad)

    assert [m.grupo for m in leido.resultados] == [m.grupo for m in original.resultados]
    assert [m.aviso_ects for m in leido.resultados] == [m.aviso_ects for m in original.resultados]
    assert any(m.aviso_ects for m in leido.resultados)
    assert any(m.grupo is not None for m in leido.resultados)


def test_volver_a_guardar_sustituye_sin_duplicar(conexion):
    original = _ejemplo()
    primero = resultados_bd.guardar(conexion, original)
    nuevo = original.model_copy(update={"umbral": 0.8, "resultados": original.resultados[:1]})

    segundo = resultados_bd.guardar(conexion, nuevo)

    assert primero == segundo
    assert conexion.execute("SELECT COUNT(*) FROM combinaciones").fetchone() == (1,)
    assert conexion.execute("SELECT COUNT(*) FROM resultados").fetchone() == (1,)
    leido = resultados_bd.leer(conexion, original.grado, original.universidad)
    assert leido.umbral == 0.8


def test_cada_combinacion_tiene_sus_filas(conexion):
    original = _ejemplo()
    otra = original.model_copy(update={"grado": "Otro grado", "resultados": []})
    resultados_bd.guardar(conexion, original)
    resultados_bd.guardar(conexion, otra)

    assert resultados_bd.leer(conexion, "Otro grado", original.universidad).resultados == []
    leido = resultados_bd.leer(conexion, original.grado, original.universidad)
    assert len(leido.resultados) == len(original.resultados)


def test_combinacion_que_no_esta(conexion):
    resultados_bd.crear_tablas(conexion)
    with pytest.raises(LookupError, match="No hay resultados"):
        resultados_bd.leer(conexion, "G", "U")


def test_no_guarda_resultados_incoherentes(conexion):
    datos = json.loads(EJEMPLO.read_text(encoding="utf-8"))
    datos["resultados"][0]["aviso_ects"] = not datos["resultados"][0]["aviso_ects"]
    with pytest.raises(ValidationError):
        resultados_bd.guardar(conexion, datos)
    resultados_bd.crear_tablas(conexion)
    assert conexion.execute("SELECT COUNT(*) FROM resultados").fetchone() == (0,)


def test_guardar_en_crea_la_carpeta(tmp_path):
    ruta = tmp_path / "processed" / "resultados.sqlite"
    resultados_bd.guardar_en(ruta, _ejemplo())
    assert ruta.is_file()


def test_no_guarda_temarios():
    columnas = set(resultados_bd.COLUMNAS)
    assert not columnas & {"objetivos", "programa", "descripcion"}
