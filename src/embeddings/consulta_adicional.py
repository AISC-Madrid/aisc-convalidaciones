"""Consulta adicional de una ficha UC3M contra embeddings existentes de Georgia Tech."""

import argparse
import sqlite3
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

import numpy as np

from src.embeddings.generar_embeddings import DIMENSION, cargar_embeddings
from src.embeddings.index import buscar_top_k
from src.embeddings.texts import construir_texto_uc3m

DATABASE_PATH = Path("data/processed/uc3m.sqlite")
EMBEDDINGS_PATH = Path("data/processed")
CODIGO_UC3M = "20605"
CURSO_ACADEMICO = "2026/2027"
IDIOMA = "EN"

Encoder = Callable[[list[str]], np.ndarray]


def _seleccionar_ficha(ruta_bd: str | Path) -> dict[str, Any]:
    """Obtiene exactamente la ficha solicitada desde SQLite en modo de solo lectura."""
    ruta_bd = Path(ruta_bd).resolve()
    uri = f"{ruta_bd.as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conexion:
        conexion.row_factory = sqlite3.Row
        filas = conexion.execute(
            """
            SELECT codigo, nombre, curso_academico, idioma, objetivos, programa
            FROM subjects
            WHERE codigo = ? AND curso_academico = ? AND idioma = ?
            """,
            (CODIGO_UC3M, CURSO_ACADEMICO, IDIOMA),
        ).fetchall()

    if not filas:
        raise LookupError(
            f"No existe la ficha UC3M {CODIGO_UC3M}, "
            f"{CURSO_ACADEMICO}, {IDIOMA} en {ruta_bd}."
        )
    if len(filas) != 1:
        raise ValueError(
            f"La consulta UC3M {CODIGO_UC3M}, {CURSO_ACADEMICO}, {IDIOMA} "
            f"es ambigua: se encontraron {len(filas)} fichas."
        )
    return dict(filas[0])


def consultar_ficha_uc3m(
    ruta_bd: str | Path = DATABASE_PATH,
    directorio_embeddings: str | Path = EMBEDDINGS_PATH,
    *,
    encoder: Encoder | None = None,
) -> tuple[dict[str, Any], list[tuple[str, str, float]]]:
    """Codifica la ficha exacta y busca su top-5 en los embeddings existentes de Georgia Tech."""
    ficha = _seleccionar_ficha(ruta_bd)
    texto = construir_texto_uc3m(
        ficha["nombre"],
        ficha["objetivos"],
        ficha["programa"],
    )

    if encoder is None:
        from src.embeddings.encoder import encode_textos

        encoder = encode_textos
    consulta = np.asarray(encoder([texto]), dtype=np.float32)
    if consulta.shape != (1, DIMENSION):
        raise ValueError(
            f"El encoder debe devolver una matriz de forma (1, {DIMENSION}); "
            f"se recibió {consulta.shape}."
        )
    if not np.isfinite(consulta).all():
        raise ValueError("El embedding de consulta debe contener valores finitos.")
    if not np.isclose(np.linalg.norm(consulta[0]), 1.0, rtol=0.0, atol=1e-4):
        raise ValueError("El embedding de consulta debe estar normalizado con L2.")

    directorio_embeddings = Path(directorio_embeddings)
    gatech, metadatos_gatech = cargar_embeddings(
        directorio_embeddings / "embeddings_gatech.npy",
        directorio_embeddings / "embeddings_gatech.json",
    )
    if metadatos_gatech.get("simulado"):
        raise ValueError("Los vectores simulados no permiten valorar similitudes reales.")

    posiciones, puntuaciones = buscar_top_k(consulta[0], gatech, k=5)
    resultados = [
        (
            metadatos_gatech["asignaturas"][int(posicion)]["codigo"],
            metadatos_gatech["asignaturas"][int(posicion)]["nombre"],
            float(puntuacion),
        )
        for posicion, puntuacion in zip(posiciones, puntuaciones, strict=True)
    ]

    print(
        "Consulta adicional UC3M: "
        f"{ficha['codigo']} — {ficha['nombre']} "
        f"({ficha['curso_academico']}, {ficha['idioma']})"
    )
    print("Top-5 Georgia Tech:")
    for codigo, nombre, puntuacion in resultados:
        print(f"  {codigo}: {nombre} — {puntuacion:.6f}")
    return ficha, resultados


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bd", type=Path, default=DATABASE_PATH)
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS_PATH)
    argumentos = parser.parse_args()
    consultar_ficha_uc3m(argumentos.bd, argumentos.embeddings)


if __name__ == "__main__":
    main()
