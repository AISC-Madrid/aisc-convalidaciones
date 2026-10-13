import sqlite3
from contextlib import closing

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


ESQUEMA_14 = """
CREATE TABLE subjects (
    "código" TEXT, nombre TEXT, plan TEXT, curso_academico TEXT, tipo TEXT, creditos REAL,
    curso INTEGER, cuatrimestre TEXT, objetivos TEXT, programa TEXT, idioma TEXT, url TEXT,
    fecha_actualizacion TEXT
)
"""


def _tablas(connection: sqlite3.Connection) -> set[str]:
    return {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_migra_la_bd_del_esquema_de_la_pr_14(tmp_path):
    database_path = tmp_path / "uc3m.sqlite"
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(ESQUEMA_14)
        connection.execute(
            'INSERT INTO subjects ("código", nombre, curso_academico, idioma, programa) '
            "VALUES ('15363', 'Álgebra Lineal', '2026/2027', 'ES', 'Tema 1')"
        )
        connection.execute(
            'INSERT INTO subjects ("código", nombre) VALUES (?, ?)', ("99999", "Sin curso")
        )

    create_database(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        columnas = tuple(r[1] for r in connection.execute("PRAGMA table_info(subjects)"))
        filas = connection.execute("SELECT codigo, nombre, programa FROM subjects").fetchall()
        antiguas = [t for t in _tablas(connection) if t.startswith("subjects_antigua_")]
        copia = connection.execute(f'SELECT COUNT(*) FROM "{antiguas[0]}"').fetchone()[0]
        connection.execute(
            "INSERT INTO subjects (codigo, curso_academico, idioma) VALUES ('1', '2026/2027', 'EN')"
        )

    assert columnas == SUBJECT_COLUMNS
    assert filas == [("15363", "Álgebra Lineal", "Tema 1")]
    assert len(antiguas) == 1
    assert copia == 2  # la tabla vieja se conserva entera


def test_migra_un_esquema_al_que_le_faltan_columnas(tmp_path):
    database_path = tmp_path / "uc3m.sqlite"
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute("CREATE TABLE subjects (codigo TEXT, curso_academico TEXT, idioma TEXT)")
        connection.execute("INSERT INTO subjects VALUES ('15363', '2026/2027', 'EN')")

    create_database(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        columnas = tuple(r[1] for r in connection.execute("PRAGMA table_info(subjects)"))
        filas = connection.execute("SELECT codigo, idioma, hash_texto FROM subjects").fetchall()

    assert columnas == SUBJECT_COLUMNS
    assert filas == [("15363", "EN", None)]


def test_con_el_esquema_actual_no_migra_nada(tmp_path):
    database_path = create_database(tmp_path / "uc3m.sqlite")

    create_database(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        assert not any(t.startswith("subjects_antigua_") for t in _tablas(connection))


def test_no_se_puede_duplicar_codigo_curso_e_idioma(tmp_path):
    database_path = create_database(tmp_path / "uc3m.sqlite")

    with sqlite3.connect(database_path) as connection:
        insert = "INSERT INTO subjects (codigo, curso_academico, idioma) VALUES (?, ?, ?)"
        connection.execute(insert, ("15363", "2026/2027", "ES"))
        connection.execute(insert, ("15363", "2026/2027", "EN"))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(insert, ("15363", "2026/2027", "ES"))
