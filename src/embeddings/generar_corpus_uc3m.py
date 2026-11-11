"""Generación del corpus UC3M del plan piloto."""

import json
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from statistics import median
from typing import Any

from src.embeddings.texts import construir_texto_uc3m

DATABASE_PATH = Path("data/processed/uc3m.sqlite")
OUTPUT_PATH = Path("data/processed/corpus_uc3m.jsonl")
ESTUDIO_PILOTO = "257"
PLANES_PILOTO = ("522", "419")
CURSO_ACADEMICO = "2026/2027"
IDIOMA = "EN"

FilaUC3M = tuple[str, str, str | None, str | None, str, str, str | None, str | None]


def _consultar_filas(
    database_path: Path,
    estudio: str,
    planes: Sequence[str],
    curso_academico: str,
    idioma: str,
) -> list[FilaUC3M]:
    """Lee las fichas del estudio, planes, curso e idioma solicitados."""
    if not database_path.exists():
        raise FileNotFoundError(f"No existe la base de datos UC3M: {database_path}")

    placeholders = ", ".join("?" for _ in planes)
    consulta = f"""
        SELECT DISTINCT
            s.codigo,
            COALESCE(s.nombre, ''),
            s.objetivos,
            s.programa,
            s.plan,
            s.curso_academico,
            s.tipo,
            s.url
        FROM subjects AS s
        INNER JOIN subject_plans AS sp
            ON sp.codigo = s.codigo
            AND sp.curso_academico = s.curso_academico
        WHERE sp.estudio = ?
          AND sp.plan IN ({placeholders})
          AND s.curso_academico = ?
          AND s.idioma = ?
        ORDER BY s.codigo
    """

    uri = f"{database_path.resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        return connection.execute(
            consulta,
            (estudio, *planes, curso_academico, idioma),
        ).fetchall()


def _longitudes(filas: Sequence[dict[str, Any]]) -> list[int]:
    return [len(fila["texto"].split()) - len(fila["nombre"].split()) - 1 for fila in filas]


def calcular_estadisticas(filas: Sequence[dict[str, Any]]) -> dict[str, int | float]:
    """Calcula longitudes y campos vacíos del corpus UC3M."""
    if not filas:
        raise ValueError("No hay asignaturas UC3M para calcular estadísticas.")

    longitudes_objetivos = [len((fila["objetivos"] or "").split()) for fila in filas]
    longitudes_programa = [len((fila["programa"] or "").split()) for fila in filas]
    longitudes_texto = _longitudes(filas)

    return {
        "asignaturas": len(filas),
        "objetivos_vacios": sum(not (fila["objetivos"] or "").strip() for fila in filas),
        "programas_vacios": sum(not (fila["programa"] or "").strip() for fila in filas),
        "ambos_vacios": sum(
            not (fila["objetivos"] or "").strip() and not (fila["programa"] or "").strip()
            for fila in filas
        ),
        "objetivos_min": min(longitudes_objetivos),
        "objetivos_mediana": median(longitudes_objetivos),
        "objetivos_max": max(longitudes_objetivos),
        "programa_min": min(longitudes_programa),
        "programa_mediana": median(longitudes_programa),
        "programa_max": max(longitudes_programa),
        "texto_min": min(longitudes_texto),
        "texto_mediana": median(longitudes_texto),
        "texto_max": max(longitudes_texto),
        "textos_cortos": sum(0 < longitud < 10 for longitud in longitudes_texto),
    }


def generar_corpus(
    database_path: str | Path = DATABASE_PATH,
    output_path: str | Path = OUTPUT_PATH,
    estudio: str = ESTUDIO_PILOTO,
    planes: Sequence[str] = PLANES_PILOTO,
    curso_academico: str = CURSO_ACADEMICO,
    idioma: str = IDIOMA,
) -> tuple[Path, dict[str, int | float]]:
    """Genera el JSONL UC3M y devuelve su ruta junto con sus estadísticas."""
    database_path = Path(database_path)
    output_path = Path(output_path)
    filas = _consultar_filas(database_path, estudio, planes, curso_academico, idioma)

    registros: list[dict[str, Any]] = []
    for codigo, nombre, objetivos, programa, plan_ficha, curso, tipo, url in filas:
        registros.append(
            {
                "codigo": codigo,
                "nombre": nombre,
                "plan": plan_ficha,
                "curso_academico": curso,
                "idioma": idioma,
                "tipo": tipo,
                "url": url,
                "objetivos": objetivos,
                "programa": programa,
                "texto": construir_texto_uc3m(nombre, objetivos, programa),
                "objetivos_vacios": not (objetivos or "").strip(),
                "programa_vacio": not (programa or "").strip(),
            }
        )

    estadisticas = calcular_estadisticas(registros)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as archivo:
        for registro in registros:
            archivo.write(json.dumps(registro, ensure_ascii=False) + "\n")

    return output_path, estadisticas


def main() -> None:
    ruta, estadisticas = generar_corpus()
    print(f"Archivo generado: {ruta}")
    for clave, valor in estadisticas.items():
        print(f"{clave}: {valor}")


if __name__ == "__main__":
    main()
