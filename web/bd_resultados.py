"""Resultados de convalidación leídos de la MySQL del servidor.

Las tablas ``combinaciones`` y ``resultados`` las escribe ``src/export/resultados_bd.py`` y
llegan a la MySQL con ``python -m src.sync.volcar_mysql``. Es la única fuente de
resultados de la web: no hay JSON de respaldo.

La imagen de la web no lleva ``src/``, por eso la lista de columnas se repite aquí; un test
comprueba que coincide con la del export.
"""

from datetime import date

import catalogo
import pymysql
import streamlit as st

COLUMNAS = (
    "origen_codigo",
    "origen_nombre",
    "origen_ects",
    "origen_tipo",
    "origen_url",
    "destino_codigo",
    "destino_nombre",
    "destino_ects",
    "destino_url",
    "score",
    "etiqueta",
    "aviso_ects",
    "grupo",
)

SQL_COMBINACIONES = "SELECT grado, universidad FROM combinaciones ORDER BY grado, universidad"

SQL_CABECERA = """
SELECT id, grado, universidad, generado, modelo, umbral
FROM combinaciones
WHERE grado = %s AND universidad = %s
"""

SQL_FILAS = f"""
SELECT {", ".join(COLUMNAS)}
FROM resultados
WHERE combinacion_id = %s
ORDER BY id
"""


class SinResultados(Exception):
    """La combinación elegida no tiene resultados en la base de datos."""


def _consultar(consultas):
    """Ejecuta ``consultas(cursor)`` con una conexión nueva y la cierra siempre."""
    con = catalogo.conectar()
    try:
        with con.cursor() as cursor:
            return consultas(cursor)
    except pymysql.MySQLError as e:
        raise catalogo.BDNoDisponible(f"No se pueden leer los resultados: {e}") from e
    finally:
        con.close()


def leer_combinaciones():
    """Grado y universidad de cada combinación que tiene resultados."""

    def consultas(cursor):
        cursor.execute(SQL_COMBINACIONES)
        return [{"grado": g, "universidad": u} for g, u in cursor.fetchall()]

    return _consultar(consultas)


def _fila(valores):
    v = dict(zip(COLUMNAS, valores, strict=True))
    return {
        "origen": {
            "codigo": v["origen_codigo"],
            "nombre": v["origen_nombre"],
            "ects": float(v["origen_ects"]),
            "tipo": v["origen_tipo"],
            "url": v["origen_url"],
        },
        "destino": {
            "codigo": v["destino_codigo"],
            "nombre": v["destino_nombre"],
            "ects": float(v["destino_ects"]),
            "url": v["destino_url"],
        },
        "score": float(v["score"]),
        "etiqueta": v["etiqueta"],
        "aviso_ects": bool(v["aviso_ects"]),
        "grupo": None if v["grupo"] is None else int(v["grupo"]),
    }


def leer_resultados(grado, universidad):
    """Cabecera y propuestas de una combinación, con la forma que usa la pantalla y el PDF."""

    def consultas(cursor):
        cursor.execute(SQL_CABECERA, (grado, universidad))
        cabecera = cursor.fetchone()
        if cabecera is None:
            raise SinResultados(f"No hay resultados para {grado} · {universidad}.")
        combinacion_id, grado_bd, universidad_bd, generado, modelo, umbral = cabecera
        cursor.execute(SQL_FILAS, (combinacion_id,))
        filas = cursor.fetchall()
        if isinstance(generado, date):
            generado = generado.isoformat()
        return {
            "grado": grado_bd,
            "universidad": universidad_bd,
            "generado": generado,
            "modelo": modelo,
            "umbral": float(umbral),
            "resultados": [_fila(f) for f in filas],
        }

    return _consultar(consultas)


# --- Con caché: lo que llama la pantalla ----------------------------------------
# Los resultados solo cambian cuando se importa un volcado nuevo; diez minutos bastan.


@st.cache_data(ttl=600, show_spinner=False)
def _combinaciones_cacheadas():
    return leer_combinaciones()


@st.cache_data(ttl=600, show_spinner=False)
def _resultados_cacheados(grado, universidad):
    return leer_resultados(grado, universidad)


def combinaciones():
    return _combinaciones_cacheadas()


def cargar(grado, universidad):
    return _resultados_cacheados(grado, universidad)


def grados(combinaciones):
    """Grados disponibles, en orden alfabético y sin repetir."""
    return sorted({c["grado"] for c in combinaciones})


def universidades(combinaciones, grado):
    """Universidades que tienen resultados para ese grado."""
    return sorted(c["universidad"] for c in combinaciones if c["grado"] == grado)
