"""Lectura de los ficheros XLS del histórico de convalidaciones."""

import re
import sqlite3
import unicodedata
from collections import Counter
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from src.models import HistoricalMatch

RAW_DIR = Path("data/raw")
DATABASE_PATH = Path("data/processed/historico.sqlite")
HISTORICAL_COLUMNS = [
    "country",
    "university",
    "degree",
    "uc_code",
    "uc_subject",
    "ects",
    "course",
    "subject_type",
    "dest_code",
    "dest_subject",
]
NORMALIZABLE_COLUMNS = [
    "country",
    "university",
    "degree",
    "uc_code",
    "uc_subject",
    "dest_code",
    "dest_subject",
]


def normalize_text(value: Any) -> str:
    """Normaliza texto conservando un único espacio entre palabras."""
    if pd.isna(value):
        return ""
    text = str(value).replace("\xa0", " ")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", text).strip().upper()


def clean_text(value: Any) -> str:
    """Quita espacios sobrantes pero conserva tildes y mayúsculas (lo que se muestra)."""
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def normalize_code(value: Any) -> str:
    """Normaliza un código eliminando todos sus espacios."""
    return normalize_text(value).replace(" ", "")


def normalize_historical(frame: pd.DataFrame) -> pd.DataFrame:
    """Añade las columnas normalizadas al DataFrame leído del histórico."""
    normalized = frame.copy()
    for column in NORMALIZABLE_COLUMNS:
        normalizer = normalize_code if column in {"uc_code", "dest_code"} else normalize_text
        normalized[f"{column}_norm"] = normalized[column].map(normalizer)
    return normalized


@dataclass(frozen=True)
class InvalidHistoricalRow:
    """Una fila que no cumple el contrato de HistoricalMatch."""

    index: Any
    errors: tuple[str, ...]


@dataclass(frozen=True)
class HistoricalValidationResult:
    """Resultado de validar un conjunto de filas del histórico."""

    valid_rows: tuple[HistoricalMatch, ...]
    invalid_rows: tuple[InvalidHistoricalRow, ...]

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_rows)


@dataclass(frozen=True)
class HistoricalDeduplicationResult:
    """Resultado de deduplicar registros históricos validados."""

    records: tuple[HistoricalMatch, ...]
    duplicates_removed: int


def _empty_to_none(value: Any) -> Any:
    return None if pd.isna(value) or value == "" else value


def _historical_identity(code: str | None, name: str) -> str:
    normalized_code = normalize_code(code)
    if normalized_code:
        return normalized_code
    return f"NAME:{normalize_text(name)}"


def _deduplication_key(record: HistoricalMatch) -> tuple[str, ...]:
    return (
        normalize_text(record.universidad),
        normalize_text(record.grado),
        _historical_identity(record.uc3m_codigo, record.uc3m_nombre),
        _historical_identity(record.destino_codigo, record.destino_nombre),
    )


def _row_to_historical_match(row: pd.Series) -> HistoricalMatch:
    """Convierte una fila normalizada al esquema del modelo Pydantic."""
    course = _empty_to_none(row["course"])
    if course is not None and isinstance(course, float) and course.is_integer():
        course = int(course)

    return HistoricalMatch(
        curso_academico=row["academic_year"],
        pais=clean_text(row["country"]),
        universidad=clean_text(row["university"]),
        grado=clean_text(row["degree"]),
        uc3m_codigo=row["uc_code_norm"],
        uc3m_nombre=clean_text(row["uc_subject"]),
        ects=_empty_to_none(row["ects"]),
        curso=course,
        tipo=_empty_to_none(row["subject_type"]),
        destino_codigo=_empty_to_none(row["dest_code_norm"]),
        destino_nombre=clean_text(row["dest_subject"]),
    )


def validate_historical_rows(frame: pd.DataFrame) -> HistoricalValidationResult:
    """Valida filas normalizadas y conserva los motivos de las inválidas."""
    normalized = frame if "uc_code_norm" in frame.columns else normalize_historical(frame)
    valid_rows: list[HistoricalMatch] = []
    invalid_rows: list[InvalidHistoricalRow] = []

    for index, row in normalized.iterrows():
        try:
            valid_rows.append(_row_to_historical_match(row))
        except ValidationError as error:
            messages = tuple(
                f"{'.'.join(str(part) for part in detail['loc'])}: {detail['msg']}"
                for detail in error.errors()
            )
            invalid_rows.append(InvalidHistoricalRow(index=index, errors=messages))

    return HistoricalValidationResult(
        valid_rows=tuple(valid_rows),
        invalid_rows=tuple(invalid_rows),
    )


def deduplicate_historical_matches(
    records: list[HistoricalMatch] | tuple[HistoricalMatch, ...],
) -> HistoricalDeduplicationResult:
    """Elimina equivalencias repetidas entre cursos académicos.

    Se conserva la primera aparición al ordenar por curso académico descendente
    y, en caso de empate, por el orden original de los registros.
    """
    ordered_records = sorted(records, key=lambda record: record.curso_academico, reverse=True)
    unique_records: list[HistoricalMatch] = []
    seen: set[tuple[str, ...]] = set()

    for record in ordered_records:
        key = _deduplication_key(record)
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(record)

    # Un grupo al que la deduplicación deja una sola fila ya no es una n:m.
    miembros = Counter(record.grupo for record in unique_records if record.grupo is not None)
    unique_records = [
        record.model_copy(update={"grupo": None}) if miembros.get(record.grupo) == 1 else record
        for record in unique_records
    ]

    return HistoricalDeduplicationResult(
        records=tuple(unique_records),
        duplicates_removed=len(records) - len(unique_records),
    )


def assign_groups(
    records: list[HistoricalMatch] | tuple[HistoricalMatch, ...],
) -> list[HistoricalMatch]:
    """Asigna `grupo` a las convalidaciones n:m. Llamar ANTES de deduplicar.

    Una n:m son las filas de un mismo curso académico, universidad y grado que
    comparten asignatura UC3M o asignatura de destino y suman al menos dos
    equivalencias distintas. Entre cursos distintos no se agrupa: pueden ser
    alternativas aprobadas en años diferentes, no asignaturas que se cursan juntas.
    """
    parent = list(range(len(records)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first_seen: dict[tuple, int] = {}
    for i, record in enumerate(records):
        *scope, uc_id, dest_id = _deduplication_key(record)
        scope = (record.curso_academico, *scope)
        for side in (("uc", uc_id), ("dest", dest_id)):
            j = first_seen.setdefault((*scope, *side), i)
            parent[find(i)] = find(j)

    components: dict[int, list[int]] = {}
    for i in range(len(records)):
        components.setdefault(find(i), []).append(i)

    result = list(records)
    number = 0
    for members in components.values():  # el orden de inserción es el de aparición
        if len({_deduplication_key(records[i]) for i in members}) < 2:
            continue
        number += 1
        for i in members:
            result[i] = records[i].model_copy(update={"grupo": number})
    return result


COLUMNS = (
    "curso_academico", "pais", "universidad", "grado", "uc3m_codigo", "uc3m_nombre",
    "ects", "curso", "tipo", "destino_codigo", "destino_nombre", "grupo",
)  # fmt: skip


def save_historical(
    records: list[HistoricalMatch] | tuple[HistoricalMatch, ...],
    database_path: str | Path = DATABASE_PATH,
) -> Path:
    """Guarda la tabla `historical_matches` desde cero (se puede relanzar)."""
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute("DROP TABLE IF EXISTS historical_matches")
        connection.execute(
            f"CREATE TABLE historical_matches (id INTEGER PRIMARY KEY, {', '.join(COLUMNS)})"
        )
        connection.executemany(
            f"INSERT INTO historical_matches ({', '.join(COLUMNS)}) "
            f"VALUES ({', '.join('?' * len(COLUMNS))})",
            [tuple(getattr(record, column) for column in COLUMNS) for record in records],
        )
    return database_path


def load_historical(raw_dir: str | Path = RAW_DIR, database_path: str | Path = DATABASE_PATH):
    """Lee los XLS de `raw_dir`, valida, agrupa las n:m, deduplica y guarda en SQLite."""
    files = sorted(Path(raw_dir).glob("*.xls"))
    frames = [read_historical_xls(path) for path in files]
    validation = validate_historical_rows(pd.concat(frames, ignore_index=True))
    deduplicated = deduplicate_historical_matches(assign_groups(validation.valid_rows))
    save_historical(deduplicated.records, database_path)
    groups = {record.grupo for record in deduplicated.records} - {None}
    print(
        f"{len(files)} ficheros: {len(validation.valid_rows)} válidas, "
        f"{validation.invalid_count} inválidas, {deduplicated.duplicates_removed} duplicadas, "
        f"{len(deduplicated.records)} guardadas en {database_path} ({len(groups)} grupos n:m)"
    )
    return deduplicated


def read_historical_xls(path: str | Path) -> pd.DataFrame:
    """Lee las hojas de datos de un XLS histórico y las combina en un DataFrame.

    La hoja informativa, que está vacía, se omite. Los encabezados se asignan
    por posición porque los XLS oficiales pueden traerlos mal decodificados.
    """
    path = Path(path)
    frames: list[pd.DataFrame] = []

    workbook = pd.ExcelFile(path, engine="xlrd")
    for sheet_name in workbook.sheet_names:
        frame = pd.read_excel(path, sheet_name=sheet_name, engine="xlrd", dtype=object)
        if frame.empty:
            continue
        if len(frame.columns) != len(HISTORICAL_COLUMNS):
            raise ValueError(
                f"La hoja {sheet_name!r} tiene {len(frame.columns)} columnas; "
                f"se esperaban {len(HISTORICAL_COLUMNS)}"
            )
        frame.columns = HISTORICAL_COLUMNS
        frame["academic_year"] = sheet_name
        frames.append(frame)

    if not frames:
        return pd.DataFrame(columns=[*HISTORICAL_COLUMNS, "academic_year"])

    return normalize_historical(pd.concat(frames, ignore_index=True))


if __name__ == "__main__":
    load_historical()
