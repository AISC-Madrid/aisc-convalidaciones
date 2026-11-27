"""Guarda y lee los resultados del matching en la base de datos.

Los resultados de cada grado × universidad van en dos tablas de
``data/processed/resultados.sqlite``:

- ``combinaciones``: una fila por grado × universidad, con la fecha, el modelo y el umbral.
- ``resultados``: una fila por propuesta (asignatura UC3M frente a asignatura del destino).

``python -m src.sync.volcar_mysql exportar`` las lleva a la MySQL del servidor junto con el
catálogo, y la web las lee de allí. Es el único sitio del que la web saca los resultados.

Se guardan los nombres y créditos de las asignaturas tal como estaban al calcular, para que
un resultado no cambie si luego se vuelve a scrapear el catálogo. No se guarda ningún temario.
"""

import sqlite3
from pathlib import Path

from src.models.match import Resultados

RAIZ = Path(__file__).resolve().parents[2]
RUTA_RESULTADOS = RAIZ / "data" / "processed" / "resultados.sqlite"

ESQUEMA = """
CREATE TABLE IF NOT EXISTS combinaciones (
    id INTEGER PRIMARY KEY,
    grado TEXT NOT NULL,
    universidad TEXT NOT NULL,
    generado TEXT NOT NULL,
    modelo TEXT NOT NULL,
    umbral REAL NOT NULL,
    UNIQUE (grado, universidad)
);
CREATE TABLE IF NOT EXISTS resultados (
    id INTEGER PRIMARY KEY,
    combinacion_id INTEGER NOT NULL REFERENCES combinaciones (id),
    origen_codigo TEXT NOT NULL,
    origen_nombre TEXT NOT NULL,
    origen_ects REAL NOT NULL,
    origen_tipo TEXT,
    origen_url TEXT,
    destino_codigo TEXT NOT NULL,
    destino_nombre TEXT NOT NULL,
    destino_ects REAL NOT NULL,
    destino_url TEXT,
    score REAL NOT NULL,
    etiqueta TEXT NOT NULL,
    aviso_ects INTEGER NOT NULL,
    grupo INTEGER
);
CREATE INDEX IF NOT EXISTS idx_resultados_combinacion ON resultados (combinacion_id);
"""

# Orden de las columnas de ``resultados`` (sin id ni combinacion_id), el mismo al leer.
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


def crear_tablas(conexion: sqlite3.Connection) -> None:
    conexion.executescript(ESQUEMA)


def guardar(conexion: sqlite3.Connection, resultados: Resultados) -> int:
    """Guarda una combinación entera y devuelve su id.

    Si la combinación ya estaba, sus filas se sustituyen: volver a exportar no duplica nada.
    """
    resultados = Resultados.model_validate(resultados)
    crear_tablas(conexion)
    with conexion:
        conexion.execute(
            """
            INSERT INTO combinaciones (grado, universidad, generado, modelo, umbral)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (grado, universidad) DO UPDATE SET
                generado = excluded.generado,
                modelo = excluded.modelo,
                umbral = excluded.umbral
            """,
            (
                resultados.grado,
                resultados.universidad,
                resultados.generado.isoformat(),
                resultados.modelo,
                resultados.umbral,
            ),
        )
        (combinacion_id,) = conexion.execute(
            "SELECT id FROM combinaciones WHERE grado = ? AND universidad = ?",
            (resultados.grado, resultados.universidad),
        ).fetchone()
        conexion.execute("DELETE FROM resultados WHERE combinacion_id = ?", (combinacion_id,))
        conexion.executemany(
            f"INSERT INTO resultados (combinacion_id, {', '.join(COLUMNAS)}) "
            f"VALUES (?, {', '.join('?' * len(COLUMNAS))})",
            [
                (
                    combinacion_id,
                    m.origen.codigo,
                    m.origen.nombre,
                    m.origen.ects,
                    m.origen.tipo,
                    m.origen.url,
                    m.destino.codigo,
                    m.destino.nombre,
                    m.destino.ects,
                    m.destino.url,
                    m.score,
                    m.etiqueta,
                    int(m.aviso_ects),
                    m.grupo,
                )
                for m in resultados.resultados
            ],
        )
    return combinacion_id


def guardar_en(ruta: Path, resultados: Resultados) -> int:
    """Abre (o crea) el SQLite de ``ruta`` y guarda la combinación."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(ruta)
    try:
        return guardar(conexion, resultados)
    finally:
        conexion.close()


def fila_a_dict(fila) -> dict:
    """Una fila de ``resultados`` (en el orden de ``COLUMNAS``) con la forma de ``Match``."""
    valores = dict(zip(COLUMNAS, fila, strict=True))
    origen = {
        "codigo": valores["origen_codigo"],
        "nombre": valores["origen_nombre"],
        "ects": valores["origen_ects"],
        "tipo": valores["origen_tipo"],
        "url": valores["origen_url"],
    }
    destino = {
        "codigo": valores["destino_codigo"],
        "nombre": valores["destino_nombre"],
        "ects": valores["destino_ects"],
        "url": valores["destino_url"],
    }
    return {
        "origen": origen,
        "destino": destino,
        "score": valores["score"],
        "etiqueta": valores["etiqueta"],
        "aviso_ects": bool(valores["aviso_ects"]),
        "grupo": valores["grupo"],
    }


def leer(conexion: sqlite3.Connection, grado: str, universidad: str) -> Resultados:
    """Lee una combinación del SQLite local. Falla con ``LookupError`` si no está."""
    cabecera = conexion.execute(
        "SELECT id, grado, universidad, generado, modelo, umbral FROM combinaciones "
        "WHERE grado = ? AND universidad = ?",
        (grado, universidad),
    ).fetchone()
    if cabecera is None:
        raise LookupError(f"No hay resultados para {grado} · {universidad}")
    combinacion_id, grado, universidad, generado, modelo, umbral = cabecera
    filas = conexion.execute(
        f"SELECT {', '.join(COLUMNAS)} FROM resultados WHERE combinacion_id = ? ORDER BY id",
        (combinacion_id,),
    ).fetchall()
    return Resultados.model_validate(
        {
            "grado": grado,
            "universidad": universidad,
            "generado": generado,
            "modelo": modelo,
            "umbral": umbral,
            "resultados": [fila_a_dict(fila) for fila in filas],
        }
    )
