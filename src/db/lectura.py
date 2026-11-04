"""Conexión y consultas de catálogo contra la MySQL del servidor.

Las consultas piden código, nombre, créditos, url, plan y universidad. No piden
objetivos, programa ni descripción: esos textos están en la base para el
pipeline, y la interfaz no los muestra.
"""

import os
from collections.abc import Mapping

import pymysql
import pymysql.cursors

VARIABLES = (
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_DATABASE",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
)

COLUMNAS_OCULTAS = ("objetivos", "programa", "descripcion")

SQL_CATALOGO_UC3M = """
SELECT s.codigo, s.nombre, s.creditos, s.url, p.plan
FROM subjects AS s
JOIN subject_plans AS p
  ON p.codigo = s.codigo AND p.curso_academico = s.curso_academico
WHERE p.plan = %s AND s.idioma = %s
ORDER BY s.codigo
"""

SQL_CATALOGO_DESTINO = """
SELECT codigo, nombre, ects, universidad
FROM dest_subjects
WHERE universidad = %s
ORDER BY codigo
"""


class ConfiguracionMysqlError(Exception):
    """Faltan variables o el puerto no es un número. No se abre ninguna conexión."""


def configuracion(environ: Mapping[str, str] | None = None) -> dict:
    """Lee la conexión de las variables de entorno. No tiene valores por defecto."""
    env = os.environ if environ is None else environ
    faltan = [nombre for nombre in VARIABLES if not env.get(nombre)]
    if faltan:
        raise ConfiguracionMysqlError("Faltan variables de MySQL: " + ", ".join(faltan))
    try:
        puerto = int(env["MYSQL_PORT"])
    except ValueError as exc:
        raise ConfiguracionMysqlError("MYSQL_PORT no es un número") from exc
    return {
        "host": env["MYSQL_HOST"],
        "port": puerto,
        "user": env["MYSQL_USER"],
        "password": env["MYSQL_PASSWORD"],
        "database": env["MYSQL_DATABASE"],
    }


def conectar(environ: Mapping[str, str] | None = None, *, dict_cursor: bool = True):
    """Abre la base indicada por las variables. `utf8mb4` para los textos largos."""
    cfg = configuracion(environ)
    kwargs = {"charset": "utf8mb4", **cfg}
    if dict_cursor:
        kwargs["cursorclass"] = pymysql.cursors.DictCursor
    return pymysql.connect(**kwargs)


def comprobar(conexion) -> None:
    """Falla si la base no responde. No lee ninguna tabla."""
    with conexion.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()


def catalogo_uc3m(conexion, plan: str, idioma: str = "ES") -> list[dict]:
    """Asignaturas de un plan UC3M: código, nombre, créditos, url y plan."""
    with conexion.cursor() as cur:
        cur.execute(SQL_CATALOGO_UC3M, (plan, idioma))
        return list(cur.fetchall())


def catalogo_destino(conexion, universidad: str) -> list[dict]:
    """Asignaturas de una universidad de destino, sin la descripción del catálogo."""
    with conexion.cursor() as cur:
        cur.execute(SQL_CATALOGO_DESTINO, (universidad,))
        return list(cur.fetchall())
