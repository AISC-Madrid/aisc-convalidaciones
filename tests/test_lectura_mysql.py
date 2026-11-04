"""Consultas de catálogo: no piden temario y fallan sin variables."""

import pytest

from src.db.lectura import (
    COLUMNAS_OCULTAS,
    SQL_CATALOGO_DESTINO,
    SQL_CATALOGO_UC3M,
    ConfiguracionMysqlError,
    catalogo_destino,
    catalogo_uc3m,
    comprobar,
    configuracion,
)


class CursorFalso:
    def __init__(self, filas):
        self.filas = filas
        self.sql = None
        self.args = None

    def execute(self, sql, args=None):
        self.sql = sql
        self.args = args

    def fetchall(self):
        return self.filas

    def fetchone(self):
        return (1,)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ConexionFalsa:
    def __init__(self, filas):
        self.cur = CursorFalso(filas)

    def cursor(self):
        return self.cur


def test_faltan_variables():
    with pytest.raises(ConfiguracionMysqlError, match="MYSQL_HOST"):
        configuracion({})


def test_puerto_no_numerico():
    entorno = {
        "MYSQL_HOST": "mysql.interno",
        "MYSQL_PORT": "abc",
        "MYSQL_DATABASE": "convalidaciones_db",
        "MYSQL_USER": "convalidaciones_user",
        "MYSQL_PASSWORD": "secreto",
    }
    with pytest.raises(ConfiguracionMysqlError, match="número"):
        configuracion(entorno)


def test_catalogo_no_pide_temario():
    for sql in (SQL_CATALOGO_UC3M, SQL_CATALOGO_DESTINO):
        for columna in COLUMNAS_OCULTAS:
            assert columna not in sql


def test_catalogo_uc3m_pasa_plan_e_idioma():
    conexion = ConexionFalsa(
        [{"codigo": "15363", "nombre": "Álgebra", "creditos": 6, "url": None, "plan": "456"}]
    )
    filas = catalogo_uc3m(conexion, "456", "EN")
    assert conexion.cur.args == ("456", "EN")
    assert filas[0]["codigo"] == "15363"
    assert "objetivos" not in conexion.cur.sql


def test_catalogo_destino_pasa_la_universidad():
    conexion = ConexionFalsa(
        [{"codigo": "BMED 2110", "nombre": "Intro", "ects": 3.5, "universidad": "GATECH"}]
    )
    filas = catalogo_destino(conexion, "GATECH")
    assert conexion.cur.args == ("GATECH",)
    assert "descripcion" not in conexion.cur.sql
    assert filas[0]["ects"] == 3.5


def test_comprobar_solo_pregunta_si_responde():
    conexion = ConexionFalsa([])
    comprobar(conexion)
    assert conexion.cur.sql == "SELECT 1"
