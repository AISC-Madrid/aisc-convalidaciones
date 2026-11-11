"""Copia el SQLite del release privado a la MySQL del servidor.

El pipeline de los portátiles sigue escribiendo SQLite. Este comando solo se
ejecuta donde la MySQL es alcanzable (el mismo servidor que phpMyAdmin): baja
el último ``uc3m.sqlite`` a un directorio temporal y recrea allí sus tablas.
Si ``historico.sqlite`` está al lado de esa copia, o en ``data/processed/``,
también se vuelca. La caché HTML no entra.

Uso, con las variables MYSQL_* ya definidas:

    python -m src.sync.volcar_mysql
"""

import logging
import re
import sqlite3
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import closing
from pathlib import Path

from src.db.lectura import ConfiguracionMysqlError, conectar, configuracion
from src.sync.datos import RAIZ, descargar

logger = logging.getLogger(__name__)

LOTE = 500
LONGITUD_CLAVE = 255
TEXTOS_LARGOS = {"objetivos", "programa", "descripcion"}
_IDENTIFICADOR = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DEFAULT_SEGURO = re.compile(r"^(-?\d+(?:\.\d+)?|NULL|'(?:[^']|'')*')$")


def exigir_identificador(nombre: str) -> str:
    """Rechaza nombres que no salgan de ``sqlite_master`` con forma de identificador."""
    if not _IDENTIFICADOR.match(nombre):
        raise ValueError(f"Identificador no válido: {nombre}")
    return nombre


def quote(nombre: str) -> str:
    return f"`{exigir_identificador(nombre)}`"


def tipo_mysql(columna: str, tipo_sqlite: str, en_clave: bool = False) -> str:
    """Pasa el tipo declarado en SQLite al de MySQL. Los temarios van en LONGTEXT.

    MySQL no indexa TEXT sin longitud (error 1170), así que el texto que forma parte de
    una clave o un índice va en ``VARCHAR(255)``: tres columnas en utf8mb4 caben en los
    3072 bytes de una clave InnoDB.
    """
    if columna in TEXTOS_LARGOS:
        return "LONGTEXT"
    base = tipo_sqlite.upper().split("(", 1)[0].strip()
    if base in {"INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "MEDIUMINT"}:
        return "BIGINT"
    if base in {"REAL", "FLOAT", "DOUBLE", "NUMERIC", "DECIMAL"}:
        return "DOUBLE"
    if base == "BLOB":
        return "LONGBLOB"
    return f"VARCHAR({LONGITUD_CLAVE})" if en_clave else "TEXT"


def _definicion_columna(
    nombre: str, tipo: str, notnull: int, default, pk: int, en_clave: bool = False
) -> str:
    tipo_sql = tipo_mysql(nombre, tipo, en_clave)
    partes = [f"{quote(nombre)} {tipo_sql}"]
    if notnull or pk:
        partes.append("NOT NULL")
    # MySQL no admite DEFAULT literal en TEXT ni BLOB.
    sin_default = tipo_sql in {"TEXT", "LONGTEXT", "LONGBLOB"}
    if not sin_default and isinstance(default, str) and _DEFAULT_SEGURO.match(default):
        partes.append(f"DEFAULT {default}")
    return " ".join(partes)


def tablas_usuario(conexion: sqlite3.Connection) -> list[str]:
    """Tablas creadas por el pipeline. Se deja fuera ``sqlite_sequence`` y el resto interno."""
    filas = conexion.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )
    return [exigir_identificador(fila[0]) for fila in filas]


def _indices(conexion: sqlite3.Connection, tabla: str) -> list[tuple[bool, list[str], str]]:
    indices = []
    for fila in conexion.execute(f"PRAGMA index_list({tabla})"):
        nombre, unico, origen = fila[1], fila[2], fila[3]
        if origen == "pk":
            continue
        nombre_sql = exigir_identificador(nombre)
        columnas = [
            exigir_identificador(info[2])
            for info in conexion.execute(f"PRAGMA index_info('{nombre_sql}')")
        ]
        if columnas:
            indices.append((bool(unico), columnas, nombre_sql[:64]))
    return indices


def sentencias_tabla(conexion: sqlite3.Connection, tabla: str) -> list[str]:
    """CREATE TABLE (claves, UNIQUE, utf8mb4) y los índices que no son únicos."""
    columnas = list(conexion.execute(f"PRAGMA table_info({tabla})"))
    indices = _indices(conexion, tabla)
    en_clave = {col for _unico, cols, _nombre in indices for col in cols}
    en_clave |= {fila[1] for fila in columnas if fila[5]}
    defs = []
    pk = []
    for _cid, nombre, tipo, notnull, default, orden_pk in columnas:
        exigir_identificador(nombre)
        defs.append(
            _definicion_columna(nombre, tipo, notnull, default, orden_pk, nombre in en_clave)
        )
        if orden_pk:
            pk.append((orden_pk, nombre))
    pk_nombres = [nombre for _orden, nombre in sorted(pk)]
    if pk_nombres:
        defs.append(f"PRIMARY KEY ({', '.join(quote(nombre) for nombre in pk_nombres)})")
    for unico, cols, nombre in indices:
        if unico and cols == pk_nombres:
            continue
        if unico:
            defs.append(f"UNIQUE KEY {quote(nombre)} ({', '.join(quote(col) for col in cols)})")
    create = (
        f"CREATE TABLE {quote(tabla)} (\n  "
        + ",\n  ".join(defs)
        + "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    )
    extras = [
        f"CREATE INDEX {quote(nombre)} ON {quote(tabla)} ({', '.join(quote(col) for col in cols)})"
        for unico, cols, nombre in indices
        if not unico
    ]
    return [create, *extras]


def _copiar_tabla(cursor, origen: sqlite3.Connection, tabla: str) -> int:
    info = origen.execute(f"PRAGMA table_info({tabla})")
    columnas = [exigir_identificador(fila[1]) for fila in info]
    lista = ", ".join(quote(columna) for columna in columnas)
    cursor.execute(f"DROP TABLE IF EXISTS {quote(tabla)}")
    for sentencia in sentencias_tabla(origen, tabla):
        cursor.execute(sentencia)
    seleccion = ", ".join(f'"{columna}"' for columna in columnas)
    filas = origen.execute(f'SELECT {seleccion} FROM "{tabla}"')
    insertar = f"INSERT INTO {quote(tabla)} ({lista}) VALUES ({', '.join(['%s'] * len(columnas))})"
    total = 0
    while lote := filas.fetchmany(LOTE):
        cursor.executemany(insertar, lote)
        total += len(lote)
    return total


def volcar(conexion, rutas: Sequence[Path]) -> dict[str, int]:
    """Recrea en MySQL cada tabla de usuario de los SQLite. El release pisa lo anterior."""
    resumen: dict[str, int] = {}
    with conexion.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        for ruta in rutas:
            with closing(sqlite3.connect(ruta)) as origen:
                for tabla in tablas_usuario(origen):
                    resumen[tabla] = _copiar_tabla(cur, origen, tabla)
                    logger.info("%s: %d filas desde %s", tabla, resumen[tabla], ruta.name)
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
    conexion.commit()
    return resumen


def historico_junto(sqlite_principal: Path, alternativo: Path) -> Path | None:
    """``historico.sqlite`` al lado del release, o el de ``data/processed`` si no está ahí."""
    al_lado = sqlite_principal.parent / "historico.sqlite"
    if al_lado.is_file():
        return al_lado
    if alternativo.is_file():
        return alternativo
    return None


def reunir_rutas(extraidos: Sequence[Path], historico_local: Path) -> list[Path]:
    rutas = [ruta for ruta in extraidos if ruta.suffix == ".sqlite"]
    if not rutas:
        raise FileNotFoundError("El release no trae ningún SQLite")
    historico = historico_junto(rutas[0], historico_local)
    if historico is not None and historico.resolve() not in {ruta.resolve() for ruta in rutas}:
        rutas.append(historico)
    return rutas


def abrir_escritura(environ: Mapping[str, str] | None = None):
    """Conexión de carga. Las filas se insertan como tuplas, sin cursor de diccionarios."""
    return conectar(environ, dict_cursor=False)


def ejecutar(
    environ: Mapping[str, str] | None = None,
    descargar_release=descargar,
    abrir=abrir_escritura,
    historico_local: Path | None = None,
) -> dict[str, int]:
    """Comprueba las variables, baja el release a un temporal y vuelca. No escribe en el repo."""
    configuracion(environ)
    destino_historico = (
        RAIZ / "data/processed/historico.sqlite" if historico_local is None else historico_local
    )
    with tempfile.TemporaryDirectory() as tmp:
        extraidos = descargar_release(paquetes=("bd",), raiz=Path(tmp), forzar=True)
        rutas = reunir_rutas(extraidos, destino_historico)
        conexion = abrir(environ)
        try:
            return volcar(conexion, rutas)
        finally:
            conexion.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        resumen = ejecutar()
    except ConfiguracionMysqlError as exc:
        raise SystemExit(str(exc)) from exc
    for tabla, filas in sorted(resumen.items()):
        logger.info("%s: %d filas", tabla, filas)


if __name__ == "__main__":
    main()
