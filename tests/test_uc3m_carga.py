"""Carga de principio a fin con las fixtures sintéticas, sin red (corre también en la CI)."""

import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from src.scrapers.uc3m import cargar_curso, estado_plan
from src.scrapers.uc3m_client import AsignaturaPlan, ClienteUC3M, Plan

SINTETICAS = Path(__file__).parent / "fixtures" / "uc3m" / "sinteticas"
SIN_FICHA = Path(__file__).parent / "fixtures" / "uc3m" / "respuestas" / "sin_ficha.html"


class ClienteFalso:
    """Dos grados que comparten la asignatura 10003; las fichas salen de las fixtures sintéticas.

    ``fallan``: códigos de asignatura cuya descarga lanza una excepción (``None``: todas).
    """

    def __init__(self, fallan: set[int] | None = frozenset()) -> None:
        self.fallan = fallan
        self.descargas: list[tuple[int, int, str]] = []

    def listar_planes(self, solo_grados_activos: bool = True) -> list[Plan]:
        return [
            Plan(900, "Grado de prueba", 90, True, True),
            Plan(901, "Otro grado de prueba", 91, True, True),
        ]

    def listar_asignaturas(self, plan: int, ano: int) -> list[AsignaturaPlan]:
        if plan == 900:
            return [
                AsignaturaPlan(10001, "Matemáticas Inventadas", None, 900, 90),
                AsignaturaPlan(10003, "Humanidades", None, 900, 90),
            ]
        return [
            AsignaturaPlan(10002, "Invented Databases", None, 901, 91),
            AsignaturaPlan(10003, "Humanidades", None, 901, 91),
        ]

    def descargar_ficha(self, est: int, plan: int, asig: int, anio: int, idioma: str) -> bytes:
        self.descargas.append((asig, anio, idioma))
        if self.fallan is None or asig in self.fallan:
            raise ConnectionError("la web no responde")
        ruta = SINTETICAS / f"{asig}_{anio}_{idioma}.html"
        return (ruta if ruta.exists() else SIN_FICHA).read_bytes()


class Respuesta:
    def __init__(self, content: bytes) -> None:
        self.status_code = 200
        self.content = content

    def raise_for_status(self) -> None:
        pass


class SesionPorAsignatura:
    """Sesión HTTP falsa: sirve las fixtures sintéticas salvo para las asignaturas de ``caidas``,
    a las que responde 200 con una página de mantenimiento (ni ficha ni "sin ficha")."""

    def __init__(self, caidas: set[int]) -> None:
        self.caidas = caidas
        self.urls: list[str] = []

    def get(self, url: str, **kwargs) -> Respuesta:
        self.urls.append(url)
        params = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
        if int(params["asig"]) in self.caidas:
            return Respuesta(b"<html><body>Estamos en mantenimiento</body></html>")
        idioma = {"1": "ES", "2": "EN"}[params["idioma"]]
        ruta = SINTETICAS / f"{params['asig']}_{params['anio']}_{idioma}.html"
        return Respuesta((ruta if ruta.exists() else SIN_FICHA).read_bytes())


class ClienteConSesionFalsa(ClienteUC3M):
    """El cliente real (clasificación y caché incluidas) con los listados de ``ClienteFalso``."""

    listar_planes = ClienteFalso.listar_planes
    listar_asignaturas = ClienteFalso.listar_asignaturas


def _filas(db: Path, sql: str) -> list[tuple]:
    with sqlite3.connect(db) as connection:
        return connection.execute(sql).fetchall()


def _estados(db: Path) -> dict[str, str]:
    return dict(_filas(db, "SELECT plan, estado FROM descargas"))


def test_carga_un_curso_y_deduplica_las_asignaturas(tmp_path):
    db = tmp_path / "uc3m.sqlite"
    cliente = ClienteFalso()

    stats = cargar_curso(2026, cliente, db)

    # 10001 tiene ES y EN; 10002 solo EN; 10003 solo ES. Las que faltan cuentan como sin ficha.
    assert stats["asignaturas"] == 3
    assert stats["fichas"] == 4
    assert stats["sin_ficha"] == 2
    assert _filas(db, "SELECT COUNT(*) FROM subjects") == [(4,)]
    nombre = _filas(db, "SELECT nombre FROM subjects WHERE codigo='10001' AND idioma='ES'")
    assert nombre == [("Matemáticas Inventadas",)]
    planes = _filas(db, "SELECT plan FROM subject_plans WHERE codigo='10003' ORDER BY plan")
    assert planes == [("900",), ("901",)]
    assert len(cliente.descargas) == 6
    assert _estados(db) == {"900": "completo", "901": "completo"}
    assert stats["planes_completo"] == 2


def test_cargar_dos_veces_no_duplica(tmp_path):
    db = tmp_path / "uc3m.sqlite"
    cargar_curso(2026, ClienteFalso(), db)
    cargar_curso(2026, ClienteFalso(), db)

    assert _filas(db, "SELECT COUNT(*) FROM subjects") == [(4,)]
    assert _filas(db, "SELECT COUNT(*) FROM descargas WHERE estado='completo'") == [(2,)]


def test_curso_anterior_solo_en_y_sin_ficha(tmp_path):
    db = tmp_path / "uc3m.sqlite"
    cliente = ClienteFalso()

    stats = cargar_curso(2024, cliente, db, planes=[900], solo_en=True)

    # Solo existe la fixture 10001_2024_ES: la EN no es ficha, así que pide la ES.
    assert ("10001", "2024/2025", "ES") in _filas(
        db, "SELECT codigo, curso_academico, idioma FROM subjects"
    )
    assert stats["sin_ficha"] >= 1
    assert (10001, 2024, "EN") in cliente.descargas
    assert _filas(db, "SELECT idioma FROM descargas") == [("EN",)]


def test_si_fallan_todas_las_descargas_el_plan_queda_fallido(tmp_path):
    db = tmp_path / "uc3m.sqlite"

    stats = cargar_curso(2026, ClienteFalso(fallan=None), db)

    assert stats["fichas"] == 0
    assert stats["errores"] == 6
    assert _estados(db) == {"900": "fallido", "901": "fallido"}
    assert stats["planes_fallido"] == 2


def test_con_errores_sueltos_el_plan_queda_parcial_y_se_completa_al_relanzar(tmp_path):
    db = tmp_path / "uc3m.sqlite"

    cargar_curso(2026, ClienteFalso(fallan={10003}), db)
    assert _estados(db) == {"900": "parcial", "901": "parcial"}

    cargar_curso(2026, ClienteFalso(), db)
    assert _estados(db) == {"900": "completo", "901": "completo"}


def test_con_limite_los_planes_quedan_parciales(tmp_path):
    db = tmp_path / "uc3m.sqlite"

    stats = cargar_curso(2026, ClienteFalso(), db, limite=1)

    assert stats["asignaturas"] == 1
    assert _estados(db) == {"900": "parcial", "901": "parcial"}


def test_una_pagina_inesperada_no_da_un_completo_falso_y_se_reintenta(tmp_path):
    db, cache = tmp_path / "uc3m.sqlite", tmp_path / "cache"

    def cliente(sesion: SesionPorAsignatura) -> ClienteConSesionFalsa:
        return ClienteConSesionFalsa(cache, pausa=0, reintentos=1, session=sesion)

    stats = cargar_curso(2026, cliente(SesionPorAsignatura(caidas={10001, 10002, 10003})), db)

    assert stats["fichas"] == 0
    assert stats["errores"] == 6
    assert _estados(db) == {"900": "fallido", "901": "fallido"}
    assert not list(cache.rglob("*.html"))  # nada inesperado se queda en la caché

    sana = SesionPorAsignatura(caidas=set())
    stats = cargar_curso(2026, cliente(sana), db)

    assert len(sana.urls) == 6  # al relanzar se vuelven a pedir todas
    assert stats["fichas"] == 4
    assert stats["sin_ficha"] == 2
    assert _estados(db) == {"900": "completo", "901": "completo"}


@pytest.mark.parametrize(
    ("asignaturas", "procesadas", "con_ficha", "con_error", "esperado"),
    [
        ({1, 2}, {1, 2}, {1, 2}, set(), "completo"),
        ({1, 2}, {1, 2}, set(), set(), "completo"),  # sin ficha publicada no es un error
        (set(), set(), set(), set(), "completo"),  # plan sin asignaturas ese curso
        ({1, 2}, {1, 2}, {1}, {2}, "parcial"),
        ({1, 2}, {1}, {1}, set(), "parcial"),
        ({1, 2}, set(), set(), set(), "parcial"),
        ({1, 2}, {1, 2}, set(), {1, 2}, "fallido"),
        ({1, 2}, {1}, set(), {1}, "fallido"),
    ],
)
def test_estado_plan(asignaturas, procesadas, con_ficha, con_error, esperado):
    assert estado_plan(asignaturas, procesadas, con_ficha, con_error) == esperado
