import sqlite3

import pytest

from src.scrapers.uc3m import SUBJECT_COLUMNS, create_database


def test_crea_la_base_de_datos_y_la_tabla_subjects(tmp_path):
    database_path = tmp_path / "processed" / "uc3m.sqlite"

    create_database(database_path)

    with sqlite3.connect(database_path) as connection:
        columns = connection.execute("PRAGMA table_info(subjects)").fetchall()

    assert tuple(column[1] for column in columns) == SUBJECT_COLUMNS


def test_crea_las_tablas_auxiliares(tmp_path):
    database_path = create_database(tmp_path / "uc3m.sqlite")

    with sqlite3.connect(database_path) as connection:
        tablas = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert {"subjects", "subject_plans", "descargas"} <= tablas


def test_crear_la_base_de_datos_mas_de_una_vez_no_falla(tmp_path):
    database_path = tmp_path / "uc3m.sqlite"

    create_database(database_path)
    create_database(database_path)

    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'subjects'"
        ).fetchone()[0]

    assert count == 1


def test_no_se_puede_duplicar_codigo_curso_e_idioma(tmp_path):
    database_path = create_database(tmp_path / "uc3m.sqlite")

    with sqlite3.connect(database_path) as connection:
        insert = "INSERT INTO subjects (codigo, curso_academico, idioma) VALUES (?, ?, ?)"
        connection.execute(insert, ("15363", "2026/2027", "ES"))
        connection.execute(insert, ("15363", "2026/2027", "EN"))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(insert, ("15363", "2026/2027", "ES"))
