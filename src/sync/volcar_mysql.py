"""Copia el SQLite del release privado a la MySQL del servidor.

El pipeline de los portátiles sigue escribiendo SQLite. Este comando solo se
ejecuta donde la MySQL es alcanzable (el mismo servidor que phpMyAdmin): baja
el último ``uc3m.sqlite`` y ``historico.sqlite`` a un directorio temporal y recrea
sus tablas. Si el release no trae el histórico, falla en vez de dejar la MySQL sin
los pares aprobados. La caché HTML no entra.

Uso, con las variables MYSQL_* ya definidas:

    python -m src.sync.volcar_mysql
"""

import argparse
import gzip
import logging
import re
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import closing
from pathlib import Path

from pymysql.converters import escape_item

from src.db.lectura import ConfiguracionMysqlError, conectar, configuracion

RAIZ = Path(__file__).resolve().parents[2]
PROCESADOS = RAIZ / "data" / "processed"
SQLITE_LOCALES = ("uc3m.sqlite", "historico.sqlite")
SALIDA_SQL = PROCESADOS / "convalidaciones.sql.gz"
LOTE_SQL = 100  # filas por INSERT del fichero: los temarios son largos
# phpMyAdmin admite 8 MB por fichero; 20 MB de SQL comprimen a ~5 MB.
MAX_BYTES_PARTE = 20 * 2**20

logger = logging.getLogger(__name__)

LOTE = 500
PAQUETES_SERVIDOR = ("bd", "historico")
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


def rutas_locales(carpeta: Path = PROCESADOS) -> list[Path]:
    """Los SQLite del pipeline que existan en ``carpeta``. Sin ``uc3m.sqlite`` no hay volcado."""
    rutas = [carpeta / nombre for nombre in SQLITE_LOCALES if (carpeta / nombre).is_file()]
    if not rutas or rutas[0].name != SQLITE_LOCALES[0]:
        raise FileNotFoundError(f"No está {carpeta / SQLITE_LOCALES[0]}")
    faltan = [nombre for nombre in SQLITE_LOCALES if not (carpeta / nombre).is_file()]
    for nombre in faltan:
        logger.warning("No está %s: sus tablas no se vuelcan", carpeta / nombre)
    return rutas


def literal(valor) -> str:
    """Valor de SQLite como literal de MySQL (``NULL``, número, cadena o ``X'..'``)."""
    if isinstance(valor, bytes):
        return f"X'{valor.hex()}'"
    return escape_item(valor, "utf8mb4")


def sentencias_sql(rutas: Sequence[Path], resumen: dict[str, int]) -> Iterator[str]:
    """DROP, CREATE e INSERT de cada tabla, una sentencia completa cada vez."""
    for ruta in rutas:
        with closing(sqlite3.connect(ruta)) as origen:
            for tabla in tablas_usuario(origen):
                columnas = [
                    exigir_identificador(fila[1])
                    for fila in origen.execute(f"PRAGMA table_info({tabla})")
                ]
                yield f"\nDROP TABLE IF EXISTS {quote(tabla)};\n"
                for sentencia in sentencias_tabla(origen, tabla):
                    yield sentencia + ";\n"
                lista = ", ".join(quote(columna) for columna in columnas)
                seleccion = ", ".join(f'"{columna}"' for columna in columnas)
                filas = origen.execute(f'SELECT {seleccion} FROM "{tabla}"')
                total = 0
                while lote := filas.fetchmany(LOTE_SQL):
                    valores = ",\n".join(
                        "(" + ", ".join(literal(v) for v in fila) + ")" for fila in lote
                    )
                    yield f"INSERT INTO {quote(tabla)} ({lista}) VALUES\n{valores};\n"
                    total += len(lote)
                resumen[tabla] = total
                logger.info("%s: %d filas desde %s", tabla, total, ruta.name)


def nombre_parte(destino: Path, numero: int) -> Path:
    base = destino.name.removesuffix(".gz").removesuffix(".sql")
    return destino.with_name(f"{base}-{numero}.sql.gz")


def exportar_sql(
    rutas: Sequence[Path], destino: Path, max_bytes: int = MAX_BYTES_PARTE
) -> tuple[dict[str, int], list[Path]]:
    """Escribe ``<destino>-1.sql.gz``, ``-2``… para importarlos en phpMyAdmin en orden.

    Se corta entre sentencias cuando una parte pasa de ``max_bytes`` sin comprimir, para que
    cada fichero quepa en el límite de subida de phpMyAdmin. Cada parte empieza con
    ``SET NAMES utf8mb4`` y desactiva las claves foráneas mientras se importa.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    for viejo in destino.parent.glob(nombre_parte(destino, 0).name.replace("-0.", "-*.")):
        viejo.unlink()
    resumen: dict[str, int] = {}
    partes: list[Path] = []
    salida = None
    escritos = 0
    try:
        for sentencia in sentencias_sql(rutas, resumen):
            if salida is None or (escritos > 0 and escritos + len(sentencia) > max_bytes):
                if salida is not None:
                    salida.write("\nSET FOREIGN_KEY_CHECKS=1;\n")
                    salida.close()
                partes.append(nombre_parte(destino, len(partes) + 1))
                salida = gzip.open(partes[-1], "wt", encoding="utf-8", newline="\n")
                salida.write("SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n")
                escritos = 0
            salida.write(sentencia)
            escritos += len(sentencia.encode("utf-8"))
        if salida is not None:
            salida.write("\nSET FOREIGN_KEY_CHECKS=1;\n")
    finally:
        if salida is not None:
            salida.close()
    return resumen, partes


def abrir_escritura(environ: Mapping[str, str] | None = None):
    """Conexión de carga. Las filas se insertan como tuplas, sin cursor de diccionarios."""
    return conectar(environ, dict_cursor=False)


def subir(
    environ: Mapping[str, str] | None = None,
    abrir=abrir_escritura,
    carpeta: Path = PROCESADOS,
) -> dict[str, int]:
    """Comprueba las variables MYSQL_* y vuelca los SQLite locales por conexión directa."""
    configuracion(environ)
    rutas = rutas_locales(carpeta)
    conexion = abrir(environ)
    try:
        return volcar(conexion, rutas)
    finally:
        conexion.close()


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pasa los SQLite locales a la MySQL.")
    sub = parser.add_subparsers(dest="accion", required=True)
    exp = sub.add_parser("exportar", help="Escribe .sql.gz por partes para phpMyAdmin")
    exp.add_argument("--salida", type=Path, default=SALIDA_SQL)
    sub.add_parser("subir", help="Vuelca directamente con las variables MYSQL_*")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.accion == "exportar":
        resumen, partes = exportar_sql(rutas_locales(), args.salida)
        for parte in partes:
            logger.info("Escrito %s (%.1f MB)", parte, parte.stat().st_size / 2**20)
    else:
        try:
            resumen = subir()
        except ConfiguracionMysqlError as exc:
            raise SystemExit(str(exc)) from exc
    for tabla, filas in sorted(resumen.items()):
        logger.info("%s: %d filas", tabla, filas)


if __name__ == "__main__":
    main()
