"""Carga de principio a fin desde las fixtures, sin red."""

import sqlite3
from pathlib import Path

import pytest

from src.scrapers.uc3m import cargar_curso
from src.scrapers.uc3m_client import AsignaturaPlan, Plan

FIXTURES = Path(__file__).parent / "fixtures" / "uc3m"

pytestmark = pytest.mark.skipif(
    not any(FIXTURES.glob("*.html")),
    reason="Fichas HTML no descargadas: python tests/fixtures/uc3m/descargar.py",
)


class ClienteFalso:
    """Dos grados que comparten una asignatura; las fichas salen de las fixtures."""

    def __init__(self) -> None:
        self.descargas: list[tuple[int, int, str]] = []

    def listar_planes(self, solo_grados_activos: bool = True) -> list[Plan]:
        return [
            Plan(456, "Doble Datos y Teleco", 371, True, True),
            Plan(557, "Derecho", 206, True, True),
        ]

    def listar_asignaturas(self, plan: int, ano: int) -> list[AsignaturaPlan]:
        if plan == 456:
            return [
                AsignaturaPlan(15363, "Álgebra Lineal", None, 456, 371),
                AsignaturaPlan(11692, "Humanidades", None, 456, 371),
            ]
        return [
            AsignaturaPlan(13565, "Constitución", None, 557, 206),
            AsignaturaPlan(11692, "Humanidades", None, 557, 206),
        ]

    def descargar_ficha(self, est: int, plan: int, asig: int, anio: int, idioma: str) -> bytes:
        self.descargas.append((asig, anio, idioma))
        ruta = FIXTURES / f"{asig}_{anio}_{idioma}.html"
        return ruta.read_bytes() if ruta.exists() else b"<html><body>Sin ficha</body></html>"


def _filas(db: Path, sql: str) -> list[tuple]:
    with sqlite3.connect(db) as connection:
        return connection.execute(sql).fetchall()


def test_carga_un_curso_y_deduplica_las_asignaturas(tmp_path):
    db = tmp_path / "uc3m.sqlite"
    cliente = ClienteFalso()

    stats = cargar_curso(2026, cliente, db)

    assert stats["asignaturas"] == 3
    assert stats["fichas"] == 6
    assert _filas(db, "SELECT COUNT(*) FROM subjects") == [(6,)]
    nombre = _filas(db, "SELECT nombre FROM subjects WHERE codigo='15363' AND idioma='ES'")
    assert nombre == [("Álgebra Lineal",)]
    planes = _filas(db, "SELECT plan FROM subject_plans WHERE codigo='11692' ORDER BY plan")
    assert planes == [("456",), ("557",)]
    assert len(cliente.descargas) == 6


def test_cargar_dos_veces_no_duplica(tmp_path):
    db = tmp_path / "uc3m.sqlite"
    cargar_curso(2026, ClienteFalso(), db)
    cargar_curso(2026, ClienteFalso(), db)

    assert _filas(db, "SELECT COUNT(*) FROM subjects") == [(6,)]
    assert _filas(db, "SELECT COUNT(*) FROM descargas WHERE estado='completo'") == [(2,)]


def test_curso_anterior_solo_en_y_sin_ficha(tmp_path):
    db = tmp_path / "uc3m.sqlite"
    cliente = ClienteFalso()

    stats = cargar_curso(2024, cliente, db, planes=[456], solo_en=True)

    # Solo existe la fixture 15363_2024_ES: la EN no es ficha, así que pide la ES.
    assert ("15363", "2024/2025", "ES") in _filas(
        db, "SELECT codigo, curso_academico, idioma FROM subjects"
    )
    assert stats["sin_ficha"] >= 1
    assert (15363, 2024, "EN") in cliente.descargas
