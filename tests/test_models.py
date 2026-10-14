from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models import HistoricalMatch, Match, Resultados, Subject

EJEMPLO = Path(__file__).parents[1] / "public" / "data" / "ejemplo.json"


def _match(**cambios):
    datos = {
        "origen": {"codigo": "18210", "nombre": "Sistemas Operativos", "ects": 6, "tipo": "OB"},
        "destino": {"codigo": "CS 2200", "nombre": "Computer Systems", "ects": 6.0},
        "score": 0.83,
        "etiqueta": "SUGERENCIA_IA",
        "aviso_ects": False,
    }
    return Match.model_validate(datos | cambios)


def test_subject_valida_y_rechaza_ects_no_positivos():
    assert Subject(codigo="CS 1332", nombre="Data Structures", ects=6).tipo is None
    with pytest.raises(ValidationError):
        Subject(codigo="CS 1332", nombre="Data Structures", ects=0)


def test_historical_match_admite_fila_sin_codigo_destino():
    fila = HistoricalMatch(
        curso_academico="2025-2026",
        pais="ESTADOS UNIDOS",
        universidad="UNIVERSITY OF CALIFORNIA",
        grado="GRADO EN INGENIERIA INFORMATICA",
        uc3m_codigo="18201",
        uc3m_nombre="Estructuras de Datos",
        ects=6,
        destino_nombre="Data Structures",
    )
    assert fila.destino_codigo is None
    with pytest.raises(ValidationError):
        HistoricalMatch.model_validate(fila.model_dump() | {"curso_academico": "2025"})


def test_match_aviso_ects_coherente_con_la_regla_del_25():
    assert _match().grupo is None
    destino_8 = {"codigo": "CS 2200", "nombre": "Computer Systems", "ects": 8.0}
    assert _match(destino=destino_8, aviso_ects=True).aviso_ects
    with pytest.raises(ValidationError):
        _match(destino=destino_8, aviso_ects=False)
    with pytest.raises(ValidationError):
        _match(etiqueta="OTRA")


def test_ejemplo_json_cumple_el_contrato():
    resultados = Resultados.model_validate_json(EJEMPLO.read_text(encoding="utf-8"))
    etiquetas = {m.etiqueta for m in resultados.resultados}
    assert etiquetas == {"PRECEDENTE_APROBADO", "SUGERENCIA_IA"}
    assert any(m.aviso_ects for m in resultados.resultados)
    assert any(m.grupo is not None for m in resultados.resultados)
