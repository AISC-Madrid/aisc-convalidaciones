import json
import sqlite3
from contextlib import closing

import pytest

from src.embeddings.generar_corpus_destino import generar_corpus


def crear_base(ruta, filas):
    """Crea una base de prueba con las columnas que utiliza el generador."""
    with closing(sqlite3.connect(ruta)) as conexion:
        conexion.execute(
            """
            CREATE TABLE dest_subjects (
                id INTEGER PRIMARY KEY,
                universidad TEXT,
                codigo TEXT,
                nombre TEXT,
                descripcion TEXT
            )
            """
        )
        conexion.executemany(
            "INSERT INTO dest_subjects VALUES (?, ?, ?, ?, ?)",
            filas,
        )
        conexion.commit()


def test_genera_corpus_filtra_universidad_y_limpia_textos(tmp_path):
    ruta_bd = tmp_path / "prueba.sqlite"
    ruta_salida = tmp_path / "salida" / "corpus.jsonl"

    crear_base(
        ruta_bd,
        [
            (1, "GATECH", "ME 2000", "Mechanics", None),
            (
                2,
                "GATECH",
                "AE 1000",
                "Elasticity",
                "Stress and strain. Crosslisted with ME 1000.",
            ),
            (3, "OTRA", "XX 1000", "Other course", "Other content."),
        ],
    )

    resultado = generar_corpus(ruta_bd, ruta_salida)

    registros = [
        json.loads(linea) for linea in ruta_salida.read_text(encoding="utf-8").splitlines()
    ]

    assert resultado == ruta_salida
    assert [registro["codigo"] for registro in registros] == ["AE 1000", "ME 2000"]
    assert registros[0]["texto"] == "query: Elasticity. Stress and strain."
    assert registros[0]["descripcion_vacia"] is False
    assert registros[1]["descripcion_vacia"] is True
    assert registros[1]["nombre"] == "Mechanics"
    assert all(registro["universidad"] == "GATECH" for registro in registros)


def test_rechaza_base_inexistente(tmp_path):
    ruta_bd = tmp_path / "no_existe.sqlite"
    ruta_salida = tmp_path / "corpus.jsonl"

    with pytest.raises(FileNotFoundError):
        generar_corpus(ruta_bd, ruta_salida)

    assert not ruta_bd.exists()
    assert not ruta_salida.exists()


def test_rechaza_catalogo_sin_gatech(tmp_path):
    ruta_bd = tmp_path / "prueba.sqlite"
    ruta_salida = tmp_path / "corpus.jsonl"
    crear_base(
        ruta_bd,
        [(1, "OTRA", "XX 1000", "Other course", "Other content.")],
    )

    with pytest.raises(ValueError, match="No hay asignaturas"):
        generar_corpus(ruta_bd, ruta_salida)

    assert not ruta_salida.exists()
