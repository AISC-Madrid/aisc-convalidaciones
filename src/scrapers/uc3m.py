"""Base de datos local de asignaturas de la UC3M y carga desde las fichas.

Ejecutar desde la raíz del repositorio:

    python -m src.scrapers.uc3m                      # crea la BD y descarga el curso actual
    python -m src.scrapers.uc3m --anio 2026 --plan 456
    python -m src.scrapers.uc3m --anio 2025 2024 2023 --solo-en
"""

import argparse
import hashlib
import logging
import sqlite3
import time
from collections.abc import Iterable, Sequence
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Protocol

from src.scrapers.uc3m_client import AsignaturaPlan, ClienteUC3M, Plan, url_ficha
from src.scrapers.uc3m_parser import parse_ficha

logger = logging.getLogger(__name__)

ANIO_ACTUAL = 2026

DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "uc3m.sqlite"

SUBJECT_COLUMNS = (
    "codigo",
    "nombre",
    "plan",
    "estudio",
    "curso_academico",
    "tipo",
    "creditos",
    "curso",
    "cuatrimestre",
    "coordinador",
    "departamento",
    "rama",
    "objetivos",
    "programa",
    "idioma",
    "url",
    "fecha_actualizacion",
    "hash_texto",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS subjects (
    codigo TEXT NOT NULL,
    nombre TEXT,
    plan TEXT,
    estudio TEXT,
    curso_academico TEXT NOT NULL,
    tipo TEXT,
    creditos REAL,
    curso INTEGER,
    cuatrimestre INTEGER,
    coordinador TEXT,
    departamento TEXT,
    rama TEXT,
    objetivos TEXT,
    programa TEXT,
    idioma TEXT NOT NULL,
    url TEXT,
    fecha_actualizacion TEXT,
    hash_texto TEXT,
    UNIQUE (codigo, curso_academico, idioma)
);

CREATE TABLE IF NOT EXISTS subject_plans (
    codigo TEXT NOT NULL,
    plan TEXT NOT NULL,
    estudio TEXT,
    curso_academico TEXT NOT NULL,
    PRIMARY KEY (codigo, plan, curso_academico)
);

CREATE TABLE IF NOT EXISTS descargas (
    curso_academico TEXT NOT NULL,
    plan TEXT NOT NULL,
    idioma TEXT NOT NULL,
    estado TEXT NOT NULL,
    fecha TEXT NOT NULL,
    PRIMARY KEY (curso_academico, plan, idioma)
);
"""


def create_database(database_path: str | Path = DATABASE_PATH) -> Path:
    """Crea la base de datos y sus tablas si todavía no existen."""
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.executescript(SCHEMA)

    return database_path


class Cliente(Protocol):
    """Lo que necesita la carga del cliente (permite usar uno falso en los tests)."""

    def listar_planes(self, solo_grados_activos: bool = True) -> list[Plan]: ...

    def listar_asignaturas(self, plan: int, ano: int) -> list[AsignaturaPlan]: ...

    def descargar_ficha(self, est: int, plan: int, asig: int, anio: int, idioma: str) -> bytes: ...


def curso_academico(anio: int) -> str:
    return f"{anio}/{anio + 1}"


def _hash_texto(ficha: dict) -> str | None:
    texto = "\n".join(t for t in (ficha.get("objetivos"), ficha.get("programa")) if t)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest() if texto else None


def _fila(ficha: dict, asig: AsignaturaPlan, anio: int, idioma: str) -> dict:
    fila = {columna: ficha.get(columna) for columna in SUBJECT_COLUMNS}
    fila.update(
        codigo=str(asig.codigo),
        plan=ficha.get("plan") or str(asig.plan),
        estudio=ficha.get("estudio") or str(asig.estudio),
        curso_academico=ficha.get("curso_academico") or curso_academico(anio),
        idioma=idioma,
        url=url_ficha(asig.estudio, asig.plan, asig.codigo, anio, idioma),
        hash_texto=_hash_texto(ficha),
    )
    if not fila["nombre"]:
        fila["nombre"] = asig.nombre_en if idioma == "EN" and asig.nombre_en else asig.nombre
    return fila


def _guardar(connection: sqlite3.Connection, fila: dict) -> None:
    columnas = ", ".join(SUBJECT_COLUMNS)
    marcas = ", ".join(f":{c}" for c in SUBJECT_COLUMNS)
    connection.execute(f"INSERT OR REPLACE INTO subjects ({columnas}) VALUES ({marcas})", fila)


def cargar_curso(
    anio: int,
    cliente: Cliente,
    database_path: str | Path = DATABASE_PATH,
    planes: Iterable[int] | None = None,
    idiomas: Sequence[str] = ("ES", "EN"),
    solo_en: bool = False,
    limite: int | None = None,
) -> dict[str, int]:
    """Descarga y guarda en la BD las fichas de un curso académico.

    - Recorre los grados activos (o solo ``planes``) y sus asignaturas de ese curso.
    - Cada asignatura se descarga una vez por idioma aunque esté en varios grados; la relación
      asignatura-grado queda en ``subject_plans``.
    - ``solo_en``: descarga la ficha en inglés y solo pide la española si la inglesa no tiene
      programa (para los cursos anteriores).
    - Reanudable: la caché del cliente evita repetir descargas.
    """
    database_path = create_database(database_path)
    curso = curso_academico(anio)
    todos = cliente.listar_planes()
    filtro = {int(p) for p in planes} if planes else None
    seleccion = [p for p in todos if filtro is None or p.codigo in filtro]
    if filtro and len(seleccion) < len(filtro):
        logger.warning("Planes no encontrados entre los grados activos: %s",
                       sorted(filtro - {p.codigo for p in seleccion}))

    stats = {"planes": 0, "asignaturas": 0, "fichas": 0, "sin_ficha": 0, "errores": 0}
    unicas: dict[int, AsignaturaPlan] = {}
    with closing(sqlite3.connect(database_path)) as connection:
        for plan in seleccion:
            asignaturas = cliente.listar_asignaturas(plan.codigo, anio)
            with connection:
                connection.executemany(
                    "INSERT OR REPLACE INTO subject_plans VALUES (?, ?, ?, ?)",
                    [(str(a.codigo), str(plan.codigo), str(a.estudio), curso) for a in asignaturas],
                )
            for a in asignaturas:
                unicas.setdefault(a.codigo, a)
            stats["planes"] += 1
        pendientes = list(unicas.values())[:limite] if limite else list(unicas.values())
        stats["asignaturas"] = len(pendientes)
        logger.info("Curso %s: %d grados, %d asignaturas distintas", curso,
                    stats["planes"], len(pendientes))

        inicio = time.monotonic()
        for i, asig in enumerate(pendientes, 1):
            for idioma in (("EN",) if solo_en else idiomas):
                guardada = _cargar_ficha(connection, cliente, asig, anio, idioma, stats)
                if solo_en and (guardada is None or not guardada.get("programa")):
                    _cargar_ficha(connection, cliente, asig, anio, "ES", stats)
            if i % 50 == 0 or i == len(pendientes):
                connection.commit()
                ritmo = (time.monotonic() - inicio) / i
                logger.info("%s: %d/%d asignaturas (%.0f min restantes)", curso, i,
                            len(pendientes), ritmo * (len(pendientes) - i) / 60)

        ahora = datetime.now().isoformat(timespec="seconds")
        with connection:
            connection.executemany(
                "INSERT OR REPLACE INTO descargas VALUES (?, ?, ?, ?, ?)",
                [(curso, str(p.codigo), "EN" if solo_en else "+".join(idiomas), "completo", ahora)
                 for p in seleccion],
            )
    logger.info("Curso %s terminado: %s", curso, stats)
    return stats


def _cargar_ficha(
    connection: sqlite3.Connection,
    cliente: Cliente,
    asig: AsignaturaPlan,
    anio: int,
    idioma: str,
    stats: dict[str, int],
) -> dict | None:
    try:
        html = cliente.descargar_ficha(asig.estudio, asig.plan, asig.codigo, anio, idioma)
        ficha = parse_ficha(html)
    except ValueError:
        stats["sin_ficha"] += 1
        logger.debug("Sin ficha: %s %s %s", asig.codigo, anio, idioma)
        return None
    except Exception:  # noqa: BLE001 - una ficha rota no debe parar una descarga de horas
        stats["errores"] += 1
        logger.exception("Error con la ficha %s %s %s", asig.codigo, anio, idioma)
        return None
    _guardar(connection, _fila(ficha, asig, anio, idioma))
    stats["fichas"] += 1
    return ficha


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Descarga las fichas de la UC3M a SQLite.")
    parser.add_argument("--anio", type=int, nargs="+", default=[ANIO_ACTUAL],
                        help="Cursos (año de inicio). Ej.: --anio 2026 2025")
    parser.add_argument("--plan", type=int, nargs="+", help="Solo estos planes (ej. 456)")
    parser.add_argument("--solo-en", action="store_true",
                        help="Solo la ficha en inglés (y la española si la inglesa está vacía)")
    parser.add_argument("--limite", type=int, help="Máximo de asignaturas por curso (pruebas)")
    parser.add_argument("--pausa", type=float, default=None, help="Segundos entre peticiones")
    parser.add_argument("--db", type=Path, default=DATABASE_PATH)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cliente = ClienteUC3M() if args.pausa is None else ClienteUC3M(pausa=args.pausa)
    for anio in args.anio:
        stats = cargar_curso(anio, cliente, args.db, planes=args.plan,
                             solo_en=args.solo_en, limite=args.limite)
        logger.info("Peticiones reales hasta ahora: %d | %s", cliente.peticiones, stats)


if __name__ == "__main__":
    main()
