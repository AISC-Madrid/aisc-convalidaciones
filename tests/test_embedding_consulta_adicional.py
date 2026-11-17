import json
import sqlite3

import numpy as np
import pytest

from src.embeddings.consulta_adicional import consultar_ficha_uc3m
from src.embeddings.texts import construir_texto_uc3m


def _crear_bd(ruta, filas):
    with sqlite3.connect(ruta) as conexion:
        conexion.execute(
            """
            CREATE TABLE subjects (
                codigo TEXT,
                nombre TEXT,
                curso_academico TEXT,
                idioma TEXT,
                objetivos TEXT,
                programa TEXT
            )
            """
        )
        conexion.executemany(
            "INSERT INTO subjects VALUES (?, ?, ?, ?, ?, ?)",
            filas,
        )


def _guardar_embeddings_gatech(directorio):
    directorio.mkdir(parents=True, exist_ok=True)
    vectores = np.zeros((6, 384), dtype=np.float32)
    vectores[0, 1] = 1.0
    vectores[1, 0] = 1.0
    vectores[2, :2] = [0.8, 0.6]
    vectores[3, :2] = [0.6, 0.8]
    vectores[4, 0] = -1.0
    vectores[5, 2] = 1.0
    np.save(directorio / "embeddings_gatech.npy", vectores, allow_pickle=False)
    (directorio / "embeddings_gatech.json").write_text(
        json.dumps(
            {
                "dimension": 384,
                "simulado": False,
                "asignaturas": [
                    {"codigo": f"GT{indice}", "nombre": f"Curso {indice}"}
                    for indice in range(6)
                ],
            }
        ),
        encoding="utf-8",
    )


def test_consulta_usa_la_ficha_exacta_y_ordena_top5(tmp_path, capsys):
    ruta_bd = tmp_path / "uc3m.sqlite"
    _crear_bd(
        ruta_bd,
        [
            ("20605", "Data structures", "2026/2027", "EN", "Objectives.", "Program."),
            ("20605", "Estructura de Datos", "2026/2027", "ES", "Objetivos.", "Programa."),
            ("20605", "Old title", "2025/2026", "EN", "Old objectives.", "Old program."),
            ("13873", "Other subject", "2026/2027", "EN", "Other.", "Other."),
        ],
    )
    directorio_embeddings = tmp_path / "embeddings"
    _guardar_embeddings_gatech(directorio_embeddings)
    textos_codificados = []

    def encoder(textos):
        textos_codificados.extend(textos)
        vector = np.zeros((1, 384), dtype=np.float32)
        vector[0, 0] = 1.0
        return vector

    ficha, resultados = consultar_ficha_uc3m(
        ruta_bd,
        directorio_embeddings,
        encoder=encoder,
    )

    assert ficha == {
        "codigo": "20605",
        "nombre": "Data structures",
        "curso_academico": "2026/2027",
        "idioma": "EN",
        "objetivos": "Objectives.",
        "programa": "Program.",
    }
    assert textos_codificados == [
        construir_texto_uc3m("Data structures", "Objectives.", "Program.")
    ]
    assert [resultado[:2] for resultado in resultados] == [
        ("GT1", "Curso 1"),
        ("GT2", "Curso 2"),
        ("GT3", "Curso 3"),
        ("GT0", "Curso 0"),
        ("GT5", "Curso 5"),
    ]
    assert [resultado[2] for resultado in resultados] == pytest.approx(
        [1.0, 0.8, 0.6, 0.0, 0.0]
    )
    salida = capsys.readouterr().out
    assert "20605 — Data structures (2026/2027, EN)" in salida
    assert "GT1: Curso 1 — 1.000000" in salida


def test_consulta_falla_si_no_existe_la_ficha_exacta(tmp_path):
    ruta_bd = tmp_path / "uc3m.sqlite"
    _crear_bd(
        ruta_bd,
        [("20605", "Data structures", "2025/2026", "EN", "Objectives.", "Program.")],
    )

    with pytest.raises(LookupError, match="No existe la ficha UC3M 20605"):
        consultar_ficha_uc3m(ruta_bd, tmp_path / "embeddings", encoder=lambda _: None)


def test_consulta_falla_si_la_ficha_exacta_es_ambigua(tmp_path):
    ruta_bd = tmp_path / "uc3m.sqlite"
    _crear_bd(
        ruta_bd,
        [
            ("20605", "Data structures", "2026/2027", "EN", "Objectives.", "Program."),
            ("20605", "Duplicate", "2026/2027", "EN", "Other.", "Other."),
        ],
    )

    with pytest.raises(ValueError, match="es ambigua: se encontraron 2 fichas"):
        consultar_ficha_uc3m(ruta_bd, tmp_path / "embeddings", encoder=lambda _: None)
