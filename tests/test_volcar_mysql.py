"""SQL del volcado a MySQL, sin abrir una base real."""

import gzip
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from src.db.lectura import ConfiguracionMysqlError
from src.sync.volcar_mysql import (
    exportar_sql,
    literal,
    quote,
    rutas_locales,
    sentencias_tabla,
    subir,
    volcar,
)

ENTORNO = {
    "MYSQL_HOST": "mysql.interno",
    "MYSQL_PORT": "3306",
    "MYSQL_DATABASE": "convalidaciones_db",
    "MYSQL_USER": "convalidaciones_user",
    "MYSQL_PASSWORD": "secreto",
}


class CursorFalso:
    def __init__(self):
        self.sentencias: list[str] = []
        self.lotes: list[list] = []

    def execute(self, sql, args=None):
        self.sentencias.append(sql)

    def executemany(self, sql, filas):
        self.sentencias.append(sql)
        self.lotes.append(list(filas))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ConexionFalsa:
    def __init__(self):
        self.cur = CursorFalso()
        self.committed = False
        self.cerrada = False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True

    def close(self):
        self.cerrada = True


def crear_sqlite(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conexion, conexion:
        conexion.execute(
            """
            CREATE TABLE subjects (
                codigo TEXT NOT NULL,
                nombre TEXT,
                creditos REAL,
                objetivos TEXT,
                programa TEXT,
                idioma TEXT NOT NULL,
                UNIQUE (codigo, idioma)
            )
            """
        )
        conexion.execute("CREATE INDEX idx_nombre ON subjects (nombre)")
        conexion.execute(
            """
            CREATE TABLE dest_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                universidad TEXT NOT NULL,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                ects REAL,
                UNIQUE (universidad, codigo)
            )
            """
        )
        conexion.execute(
            "INSERT INTO subjects VALUES ('15363', 'Álgebra', 6, 'obj', 'prog', 'ES')"
        )
        conexion.execute(
            "INSERT INTO dest_subjects (id, universidad, codigo, nombre, descripcion, ects) "
            "VALUES (7, 'GATECH', 'BMED 2110', 'Intro', 'texto', 3.5)"
        )


def test_sentencias_conservan_claves_y_textos_largos(tmp_path):
    ruta = tmp_path / "uc3m.sqlite"
    crear_sqlite(ruta)
    with closing(sqlite3.connect(ruta)) as conexion:
        subjects = "\n".join(sentencias_tabla(conexion, "subjects"))
        destino = "\n".join(sentencias_tabla(conexion, "dest_subjects"))

    assert "LONGTEXT" in subjects
    assert "`objetivos` LONGTEXT" in subjects
    assert "`programa` LONGTEXT" in subjects
    assert "utf8mb4" in subjects
    assert "UNIQUE KEY" in subjects
    assert "`codigo`, `idioma`" in subjects
    assert "CREATE INDEX `idx_nombre`" in subjects
    assert "`creditos` DOUBLE" in subjects

    assert "PRIMARY KEY (`id`)" in destino
    assert "AUTO_INCREMENT" not in destino
    assert "`id` BIGINT NOT NULL" in destino
    assert "`descripcion` LONGTEXT" in destino
    assert "UNIQUE KEY" in destino
    assert "`ects` DOUBLE" in destino


def test_volcar_copia_el_id_y_no_toca_sqlite_sequence(tmp_path):
    ruta = tmp_path / "uc3m.sqlite"
    crear_sqlite(ruta)
    conexion = ConexionFalsa()

    resumen = volcar(conexion, [ruta])

    sql = "\n".join(conexion.cur.sentencias)
    assert "sqlite_sequence" not in sql
    assert resumen == {"dest_subjects": 1, "subjects": 1}
    assert conexion.committed
    filas_destino = [
        lote for lote in conexion.cur.lotes if lote and lote[0][0] == 7
    ]
    assert filas_destino
    assert filas_destino[0][0][4] == "texto"
    assert any(lote and lote[0][4] == "prog" for lote in conexion.cur.lotes)


def crear_historico(path: Path) -> None:
    with closing(sqlite3.connect(path)) as conexion, conexion:
        conexion.execute(
            "CREATE TABLE historical_matches (id INTEGER PRIMARY KEY, uc3m_codigo TEXT)"
        )
        conexion.execute("INSERT INTO historical_matches VALUES (1, '15363')")


def test_rutas_locales_toma_los_dos_sqlite_y_exige_uc3m(tmp_path):
    with pytest.raises(FileNotFoundError, match="uc3m.sqlite"):
        rutas_locales(tmp_path)
    crear_sqlite(tmp_path / "uc3m.sqlite")
    assert rutas_locales(tmp_path) == [tmp_path / "uc3m.sqlite"]
    crear_historico(tmp_path / "historico.sqlite")
    assert rutas_locales(tmp_path) == [tmp_path / "uc3m.sqlite", tmp_path / "historico.sqlite"]


def test_sin_variables_no_abre_conexion(tmp_path):
    llamado = False

    def abrir(environ):
        nonlocal llamado
        llamado = True

    with pytest.raises(ConfiguracionMysqlError, match="MYSQL_PASSWORD"):
        subir({}, abrir=abrir, carpeta=tmp_path)
    assert not llamado


def test_subir_vuelca_los_locales_y_cierra(tmp_path):
    crear_sqlite(tmp_path / "uc3m.sqlite")
    crear_historico(tmp_path / "historico.sqlite")
    conexiones = []

    def abrir(environ):
        assert environ["MYSQL_DATABASE"] == "convalidaciones_db"
        conexion = ConexionFalsa()
        conexiones.append(conexion)
        return conexion

    resumen = subir(ENTORNO, abrir=abrir, carpeta=tmp_path)

    assert resumen == {"subjects": 1, "dest_subjects": 1, "historical_matches": 1}
    assert conexiones[0].committed
    assert conexiones[0].cerrada


def test_literal_escapa_comillas_y_tipos():
    assert literal(None) == "NULL"
    assert literal(6) == "6"
    assert literal(3.5) == "3.5e0"
    assert literal("O'Neil \\ x") == r"'O\'Neil \\ x'"
    assert literal(b"\x01\xff") == "X'01ff'"


def test_exportar_sql_escribe_tablas_y_filas(tmp_path):
    crear_sqlite(tmp_path / "uc3m.sqlite")
    crear_historico(tmp_path / "historico.sqlite")
    salida = tmp_path / "out" / "volcado.sql.gz"

    resumen, partes = exportar_sql(rutas_locales(tmp_path), salida)

    assert resumen == {"subjects": 1, "dest_subjects": 1, "historical_matches": 1}
    assert partes == [tmp_path / "out" / "volcado-1.sql.gz"]
    texto = gzip.decompress(partes[0].read_bytes()).decode("utf-8")
    assert texto.startswith("SET NAMES utf8mb4;")
    assert "DROP TABLE IF EXISTS `historical_matches`;" in texto
    assert "CREATE TABLE `subjects`" in texto
    assert "CREATE INDEX `idx_nombre` ON `subjects`" in texto
    assert "'Álgebra'" in texto
    assert "(7, 'GATECH', 'BMED 2110', 'Intro', 'texto', 3.5e0)" in texto
    assert texto.rstrip().endswith("SET FOREIGN_KEY_CHECKS=1;")


def test_texto_en_clave_va_en_varchar(tmp_path):
    """MySQL no indexa TEXT sin longitud: las columnas de claves e índices van en VARCHAR."""
    ruta = tmp_path / "uc3m.sqlite"
    crear_sqlite(ruta)
    with closing(sqlite3.connect(ruta)) as conexion, conexion:
        conexion.execute(
            "CREATE TABLE subject_plans (codigo TEXT NOT NULL, plan TEXT NOT NULL, "
            "estudio TEXT, PRIMARY KEY (codigo, plan))"
        )
        conexion.execute("CREATE TABLE old_to_new (old_code TEXT PRIMARY KEY, new_code TEXT)")
        conexion.execute("CREATE TABLE con_default (clave TEXT PRIMARY KEY, nota TEXT DEFAULT 'x')")
    with closing(sqlite3.connect(ruta)) as conexion:
        subjects = "\n".join(sentencias_tabla(conexion, "subjects"))
        planes = "\n".join(sentencias_tabla(conexion, "subject_plans"))
        viejos = "\n".join(sentencias_tabla(conexion, "old_to_new"))
        defaults = "\n".join(sentencias_tabla(conexion, "con_default"))

    assert "`codigo` VARCHAR(255) NOT NULL" in subjects
    assert "`idioma` VARCHAR(255) NOT NULL" in subjects
    assert "`nombre` VARCHAR(255)" in subjects  # idx_nombre
    assert "`objetivos` LONGTEXT" in subjects
    assert "`codigo` VARCHAR(255) NOT NULL" in planes
    assert "`plan` VARCHAR(255) NOT NULL" in planes
    assert "`estudio` TEXT" in planes
    assert "`old_code` VARCHAR(255) NOT NULL" in viejos
    assert "`new_code` TEXT" in viejos
    assert "`nota` TEXT" in defaults
    assert "DEFAULT 'x'" not in defaults


def test_identificador_rechazado():
    with pytest.raises(ValueError):
        quote("subjects; DROP TABLE subjects")


def test_exportar_sql_parte_entre_sentencias_y_borra_partes_viejas(tmp_path):
    crear_sqlite(tmp_path / "uc3m.sqlite")
    crear_historico(tmp_path / "historico.sqlite")
    salida = tmp_path / "out" / "volcado.sql.gz"
    salida.parent.mkdir()
    vieja = tmp_path / "out" / "volcado-99.sql.gz"
    vieja.write_bytes(b"")

    _resumen, partes = exportar_sql(rutas_locales(tmp_path), salida, max_bytes=200)

    assert len(partes) > 1
    assert not vieja.exists()
    textos = [gzip.decompress(parte.read_bytes()).decode("utf-8") for parte in partes]
    for texto in textos:
        assert texto.startswith("SET NAMES utf8mb4;\nSET FOREIGN_KEY_CHECKS=0;\n")
        assert texto.rstrip().endswith("SET FOREIGN_KEY_CHECKS=1;")
        assert texto.rstrip().endswith(";")
    junto = "".join(textos)
    assert junto.count("CREATE TABLE") == 3
    assert junto.index("DROP TABLE IF EXISTS `subjects`") < junto.index("INSERT INTO `subjects`")
