"""Tests del catálogo con conexión MySQL simulada."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogo  # noqa: E402


class CursorSimulado:
    def __init__(self):
        self.filas = []
        self.consultas = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametros):
        self.consultas.append((sql, parametros))
        self.filas = (
            [
                ("19903", "Biomecánica", 6, "ficha-buena"),
                ("15526", "Cálculo I", 6, "ficha-calculo"),
                ("14528", "Habilidades Profesionales", 6, "ficha-compartida"),
            ]
            if "subject_plans" in sql
            else [("BMED 2110", "Conservation Principles in Biomedical Engineering", 6)]
        )

    def fetchall(self):
        return self.filas


class ConexionSimulada:
    def __init__(self):
        self.cursor_simulado = CursorSimulado()
        self.cerrada = False

    def cursor(self):
        return self.cursor_simulado

    def close(self):
        self.cerrada = True


@pytest.fixture
def conexion(monkeypatch):
    con = ConexionSimulada()
    monkeypatch.setattr(catalogo, "conectar", lambda ruta=None: con)
    return con


def test_catalogo_consulta_uc3m_y_gatech_y_cierra_conexion(conexion):
    cat = catalogo.cargar_catalogo()

    assert {a["codigo"] for a in cat} == {"19903", "15526", "14528", "BMED 2110"}
    consulta_uc3m, consulta_gatech = conexion.cursor_simulado.consultas
    assert consulta_uc3m[1] == {"estudio": "257", "curso": "2026/2027"}
    assert "%(estudio)s" in consulta_uc3m[0]
    assert "%(curso)s" in consulta_uc3m[0]
    assert ":curso" not in consulta_uc3m[0]
    assert consulta_gatech[1] == ("GATECH",)
    assert "%s" in consulta_gatech[0]
    assert conexion.cerrada


def test_no_expone_temarios(conexion):
    for asignatura in catalogo.cargar_catalogo():
        assert set(asignatura) == {"universidad", "codigo", "nombre", "ects", "url"}


def test_busqueda_y_filtro(conexion):
    cat = catalogo.cargar_catalogo()
    assert [a["codigo"] for a in catalogo.buscar(cat, "BIOMECANICA")] == ["19903"]
    resultado = catalogo.buscar(cat, "bmed2110", catalogo.GATECH)
    assert resultado[0]["url"] == "https://catalog.gatech.edu/search/?P=BMED%202110"


def test_conectar_requiere_configuracion(monkeypatch):
    for nombre in ("MYSQL_HOST", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_PORT"):
        monkeypatch.delenv(nombre, raising=False)
    with pytest.raises(catalogo.BDNoDisponible, match="MYSQL_HOST"):
        catalogo.conectar()
