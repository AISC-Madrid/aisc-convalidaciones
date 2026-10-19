"""Tests de la tabla dest_subjects: creación y guardado con upsert."""

import sqlite3

import pytest

from src.scrapers.destination import crear_tabla, guardar

CFG = {"university_code": "TEST"}


def asignatura(codigo, nombre="Asignatura inventada", ects=6.0):
    """Crea una asignatura de prueba (datos inventados)."""
    return {
        "codigo": codigo,
        "nombre": nombre,
        "descripcion": "Descripción inventada.",
        "ects": ects,
    }


@pytest.fixture
def con():
    """BD temporal en memoria con la tabla ya creada. Se borra al acabar cada test."""
    conexion = sqlite3.connect(":memory:")
    crear_tabla(conexion)
    yield conexion
    conexion.close()


def test_guardar_inserta_las_asignaturas(con):
    guardar(con, [asignatura("BMED 1000"), asignatura("BMED 2110")], CFG)
    assert con.execute("SELECT COUNT(*) FROM dest_subjects").fetchone()[0] == 2


def test_guardar_dos_veces_no_duplica_ni_cambia_ids(con):
    datos = [asignatura("BMED 1000"), asignatura("BMED 2110")]
    guardar(con, datos, CFG)
    ids_antes = con.execute("SELECT id, codigo FROM dest_subjects ORDER BY codigo").fetchall()
    guardar(con, datos, CFG)
    ids_despues = con.execute("SELECT id, codigo FROM dest_subjects ORDER BY codigo").fetchall()
    assert ids_antes == ids_despues


def test_guardar_actualiza_si_la_asignatura_cambia(con):
    guardar(con, [asignatura("BMED 1000", nombre="Nombre viejo", ects=2.0)], CFG)
    guardar(con, [asignatura("BMED 1000", nombre="Nombre nuevo", ects=4.0)], CFG)
    fila = con.execute(
        "SELECT nombre, ects FROM dest_subjects WHERE codigo = 'BMED 1000'"
    ).fetchone()
    assert fila == ("Nombre nuevo", 4.0)


def test_mismo_codigo_en_dos_universidades_son_filas_distintas(con):
    guardar(con, [asignatura("MATH 1551")], {"university_code": "GATECH"})
    guardar(con, [asignatura("MATH 1551")], {"university_code": "PURDUE"})
    assert con.execute("SELECT COUNT(*) FROM dest_subjects").fetchone()[0] == 2


def test_ects_puede_quedar_vacio(con):
    guardar(con, [asignatura("BMED 2698", ects=None)], CFG)
    ects = con.execute("SELECT ects FROM dest_subjects").fetchone()[0]
    assert ects is None


def test_crear_tabla_no_toca_las_demas_tablas():
    conexion = sqlite3.connect(":memory:")
    conexion.execute("CREATE TABLE subjects (codigo TEXT)")
    conexion.execute("INSERT INTO subjects VALUES ('15363')")
    crear_tabla(conexion)
    crear_tabla(conexion)  # dos veces: tampoco debe fallar
    assert conexion.execute("SELECT COUNT(*) FROM subjects").fetchone()[0] == 1
    conexion.close()
