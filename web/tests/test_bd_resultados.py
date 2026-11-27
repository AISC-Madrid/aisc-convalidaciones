"""Lectura de los resultados desde la MySQL, con una conexión simulada."""

import bd_resultados  # web/ está en sys.path: lo pone conftest.py
import catalogo
import pymysql
import pytest

from src.export import resultados_bd

CABECERA = (7, "Grado en Ingeniería Biomédica", "Georgia Tech", "2026-11-25", "e5", 0.71)
FILAS = [
    # Lo que devuelve pymysql: BIGINT para el aviso, DOUBLE para ECTS y score.
    ("101", "Biomecánica", 6, "OB", None, "BMED 1", "Biomechanics", 4.5, "u1", 0.9,
     "PRECEDENTE_APROBADO", 1, 3),
    ("102", "Cálculo", 6, None, None, "MATH 1", "Calculus", 6, None, 0.8,
     "SUGERENCIA_IA", 0, None),
]


class CursorSimulado:
    def __init__(self, cabecera=CABECERA, error=None):
        self.cabecera = cabecera
        self.error = error
        self.consultas = []
        self.ultima = ""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametros=None):
        if self.error:
            raise self.error
        self.consultas.append((sql, parametros))
        self.ultima = sql

    def fetchone(self):
        return self.cabecera

    def fetchall(self):
        if "FROM combinaciones" in self.ultima:
            return [("Grado en Ingeniería Biomédica", "Georgia Tech")]
        return FILAS


class ConexionSimulada:
    def __init__(self, cursor):
        self.cursor_simulado = cursor
        self.cerrada = False

    def cursor(self):
        return self.cursor_simulado

    def close(self):
        self.cerrada = True


@pytest.fixture
def conexion(monkeypatch):
    def _conexion(**opciones):
        con = ConexionSimulada(CursorSimulado(**opciones))
        monkeypatch.setattr(catalogo, "conectar", lambda ruta=None: con)
        return con

    return _conexion


def test_columnas_iguales_que_las_del_export():
    # La web no lleva src/: si el export cambia sus columnas, esto avisa.
    assert bd_resultados.COLUMNAS == resultados_bd.COLUMNAS


def test_lee_combinaciones_y_cierra(conexion):
    con = conexion()
    assert bd_resultados.leer_combinaciones() == [
        {"grado": "Grado en Ingeniería Biomédica", "universidad": "Georgia Tech"}
    ]
    assert con.cerrada


def test_lee_resultados_con_la_forma_de_la_pantalla(conexion):
    con = conexion()
    datos = bd_resultados.leer_resultados("Grado en Ingeniería Biomédica", "Georgia Tech")

    assert datos["generado"] == "2026-11-25"
    assert datos["umbral"] == 0.71
    primera, segunda = datos["resultados"]
    assert primera["origen"] == {
        "codigo": "101", "nombre": "Biomecánica", "ects": 6.0, "tipo": "OB", "url": None
    }
    assert primera["destino"]["ects"] == 4.5
    assert primera["aviso_ects"] is True
    assert primera["grupo"] == 3
    assert segunda["aviso_ects"] is False
    assert segunda["grupo"] is None
    # Las filas se piden por el id de la combinación, con parámetros (sin SQL a mano).
    assert con.cursor_simulado.consultas[1][1] == (7,)
    assert con.cerrada


def test_fecha_de_mysql_como_date(conexion):
    from datetime import date

    conexion(cabecera=(*CABECERA[:3], date(2026, 11, 25), *CABECERA[4:]))
    assert bd_resultados.leer_resultados("G", "U")["generado"] == "2026-11-25"


def test_combinacion_que_no_esta(conexion):
    con = conexion(cabecera=None)
    with pytest.raises(bd_resultados.SinResultados):
        bd_resultados.leer_resultados("G", "U")
    assert con.cerrada


def test_error_de_mysql_es_bd_no_disponible(conexion):
    # P. ej., las tablas aún no se han importado en el servidor (error 1146).
    con = conexion(error=pymysql.err.ProgrammingError(1146, "Table doesn't exist"))
    with pytest.raises(catalogo.BDNoDisponible, match="resultados"):
        bd_resultados.leer_combinaciones()
    assert con.cerrada


def test_sin_variables_no_hay_conexion():
    # conftest quita las MYSQL_*: no se intenta conectar a ningún sitio.
    with pytest.raises(catalogo.BDNoDisponible, match="Falta configurar"):
        bd_resultados.leer_combinaciones()


def test_grados_y_universidades():
    combinaciones = [
        {"grado": "B", "universidad": "U2"},
        {"grado": "A", "universidad": "U1"},
        {"grado": "B", "universidad": "U1"},
    ]
    assert bd_resultados.grados(combinaciones) == ["A", "B"]
    assert bd_resultados.universidades(combinaciones, "B") == ["U1", "U2"]
