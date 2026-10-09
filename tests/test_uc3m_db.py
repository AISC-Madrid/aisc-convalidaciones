import sqlite3

from src.scrapers.uc3m import create_database


def test_crea_la_base_de_datos_y_la_tabla_subjects(tmp_path):
    database_path = tmp_path / "processed" / "uc3m.sqlite"

    create_database(database_path)

    with sqlite3.connect(database_path) as connection:
        columns = connection.execute("PRAGMA table_info(subjects)").fetchall()

    assert [column[1] for column in columns] == [
        "código",
        "nombre",
        "plan",
        "curso_academico",
        "tipo",
        "creditos",
        "curso",
        "cuatrimestre",
        "objetivos",
        "programa",
        "idioma",
        "url",
        "fecha_actualizacion",
    ]


def test_crear_la_base_de_datos_mas_de_una_vez_no_falla(tmp_path):
    database_path = tmp_path / "uc3m.sqlite"

    create_database(database_path)
    create_database(database_path)

    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'subjects'"
        ).fetchone()[0]

    assert count == 1
