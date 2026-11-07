"""Búsqueda top-K mediante producto matricial."""

import numpy as np


def buscar_top_k(consulta, vectores, k: int = 5):
    """Devuelve posiciones y puntuaciones, de mayor a menor.

    Cada fila de vectores representa una asignatura.
    Para interpretar las puntuaciones como cosenos, los vectores
    y la consulta deben llegar normalizados a longitud uno.
    """
    consulta = np.asarray(consulta, dtype=float)
    vectores = np.asarray(vectores, dtype=float)

    if consulta.ndim != 1 or vectores.ndim != 2:
        raise ValueError("Se necesita una consulta y una matriz de vectores.")

    if consulta.size == 0 or vectores.shape[1] != consulta.size:
        raise ValueError("Las dimensiones de los vectores deben coincidir.")

    if not np.isfinite(consulta).all() or not np.isfinite(vectores).all():
        raise ValueError("Los vectores deben contener números finitos.")

    if isinstance(k, (bool, np.bool_)) or not isinstance(k, (int, np.integer)) or k < 1:
        raise ValueError("k debe ser un entero positivo.")

    puntuaciones = vectores @ consulta
    posiciones = np.argsort(-puntuaciones, kind="stable")[:k]

    return posiciones, puntuaciones[posiciones]
