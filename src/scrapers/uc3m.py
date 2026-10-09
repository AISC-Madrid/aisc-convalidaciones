"""Inicialización de la base de datos local de asignaturas de la UC3M."""

import sqlite3
from contextlib import closing
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "uc3m.sqlite"

CREATE_SUBJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS subjects (
    "código" TEXT,
    nombre TEXT,
    plan TEXT,
    curso_academico TEXT,
    tipo TEXT,
    creditos REAL,
    curso INTEGER,
    cuatrimestre TEXT,
    objetivos TEXT,
    programa TEXT,
    idioma TEXT,
    url TEXT,
    fecha_actualizacion TEXT
)
"""


def create_database(database_path: str | Path = DATABASE_PATH) -> Path:
    """Crea la base de datos y la tabla subjects si todavía no existen."""
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            connection.execute(CREATE_SUBJECTS_TABLE)

    return database_path


def main() -> None:
    database_path = create_database()
    print(f"Base de datos lista: {database_path}")


if __name__ == "__main__":
    main()
