"""Lectura de los ficheros XLS del histórico de convalidaciones."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from src.models import HistoricalMatch

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
        pais=row["country_norm"],
        universidad=row["university_norm"],
        grado=row["degree_norm"],
        uc3m_codigo=row["uc_code_norm"],
        uc3m_nombre=row["uc_subject_norm"],
        ects=_empty_to_none(row["ects"]),
        curso=course,
        tipo=_empty_to_none(row["subject_type"]),
        destino_codigo=_empty_to_none(row["dest_code_norm"]),
        destino_nombre=row["dest_subject_norm"],
    )


def validate_historical_rows(frame: pd.DataFrame) -> HistoricalValidationResult:
    """Valida filas normalizadas y conserva los motivos de las inválidas."""
    normalized = normalize_historical(frame)
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
    ordered_records = sorted(
        enumerate(records),
        key=lambda item: item[1].curso_academico,
        reverse=True,
    )
    unique_records: list[HistoricalMatch] = []
    seen: set[tuple[str, ...]] = set()

    for _, record in ordered_records:
        key = _deduplication_key(record)
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(record)

    return HistoricalDeduplicationResult(
        records=tuple(unique_records),
        duplicates_removed=len(records) - len(unique_records),
    )


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
