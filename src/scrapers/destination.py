"""Scraper del catálogo de la universidad de destino -> tabla dest_subjects."""

import argparse
import re
import sqlite3
import time
from functools import cache
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests
import yaml
from bs4 import BeautifulSoup

CONFIG_DIR = Path("config/scrapers")
RAW_DIR = Path("data/raw")
DB_POR_DEFECTO = Path("data/processed/uc3m.sqlite")


def cargar_config(uni: str) -> dict:
    """Lee config/scrapers/<uni>.yaml y lo devuelve como diccionario."""
    with open(CONFIG_DIR / f"{uni}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@cache
def _robots(raiz: str, user_agent: str) -> RobotFileParser:
    """Descarga y lee el robots.txt de una web una sola vez por ejecución."""
    robots = RobotFileParser()
    respuesta = requests.get(f"{raiz}/robots.txt", headers={"User-Agent": user_agent}, timeout=30)
    robots.parse(respuesta.text.splitlines() if respuesta.ok else [])  # sin robots.txt: todo vale
    return robots


def permitido_por_robots(url: str, user_agent: str) -> bool:
    """True si el robots.txt de la web deja descargar esa URL."""
    partes = urlsplit(url)
    return _robots(f"{partes.scheme}://{partes.netloc}", user_agent).can_fetch(user_agent, url)


def descargar(url: str, ruta_cache: Path, cfg: dict) -> str:
    """Devuelve el HTML de la URL. Si ya está en la caché, no vuelve a pedirlo."""
    if ruta_cache.exists():
        return ruta_cache.read_text(encoding="utf-8")
    if not permitido_por_robots(url, cfg["user_agent"]):
        raise PermissionError(f"robots.txt no permite descargar {url}")
    time.sleep(cfg["rate_limit_seconds"])
    respuesta = requests.get(url, headers={"User-Agent": cfg["user_agent"]}, timeout=30)
    respuesta.raise_for_status()
    ruta_cache.parent.mkdir(parents=True, exist_ok=True)
    ruta_cache.write_text(respuesta.text, encoding="utf-8")
    return respuesta.text


def descargar_departamento(prefijo: str, cfg: dict) -> str:
    """Descarga la página de un departamento (p. ej. 'BMED') usando la caché."""
    url = cfg["catalog_url"].format(prefix=prefijo.lower())
    ruta = (
        RAW_DIR
        / cfg["university_code"].lower()
        / cfg["catalog_edition"]
        / f"{prefijo.lower()}.html"
    )
    return descargar(url, ruta, cfg)


def limpiar(texto: str) -> str:
    """Quita espacios raros (incluido &nbsp;) y deja un solo espacio entre palabras."""
    return " ".join(texto.split())


def parse_catalog(html: str, cfg: dict) -> tuple[list[dict], list[str]]:
    """Saca las asignaturas de una página del catálogo.

    Devuelve (asignaturas, fallos): las que se han podido leer y los títulos que no.
    No se conecta a internet: recibe el HTML ya descargado (así se puede testear).
    """
    soup = BeautifulSoup(html, "html.parser")
    sel = cfg["selectors"]
    patron = re.compile(cfg["title_pattern"])
    asignaturas, fallos = [], []

    for bloque in soup.select(sel["course_list"]):
        elem_titulo = bloque.select_one(sel["course_title"])
        titulo = limpiar(elem_titulo.get_text(" ")) if elem_titulo else ""
        partes = titulo.split(".")[0].split()  # "MATH 1X51. Transfer..." -> ["MATH", "1X51"]
        if len(partes) == 2 and "X" in partes[1]:  # comodines y "Transfer" (1XXX, 1X51...)
            continue
        m = patron.match(titulo)
        if not m:
            fallos.append(titulo)
            continue

        codigo = m["code"]  # "BMED 2110"
        prefijo, numero = codigo.split()  # "BMED", "2110"

        nivel = re.match(r"\d+", numero)
        if nivel and int(nivel[0]) > cfg["max_course_level"]:  # 8000+: investigación/tesis
            continue

        cmin = float(m["cmin"])
        cmax = float(m["cmax"] or m["cmin"])  # si no es rango, max = min
        if cmax == 0:  # recitations de 0 créditos
            continue

        elem_desc = bloque.select_one(sel["description"])
        asignaturas.append(
            {
                "codigo": codigo,
                "nombre": m["name"].strip(),
                "descripcion": limpiar(elem_desc.get_text(" ")) if elem_desc else None,
                "departamento": prefijo,
                "creditos": cmin,
                "creditos_max": cmax,
                "ects": cmin * cfg["credits_to_ects"] if cmin == cmax else None,
            }
        )

    return asignaturas, fallos


ESQUEMA_DEST_SUBJECTS = """
CREATE TABLE IF NOT EXISTS dest_subjects (
    id           INTEGER PRIMARY KEY,
    universidad  TEXT NOT NULL,
    codigo       TEXT NOT NULL,
    codigo_norm  TEXT,
    nombre       TEXT NOT NULL,
    descripcion  TEXT,
    ects         REAL,
    UNIQUE (universidad, codigo)
)
"""

SQL_UPSERT = """
INSERT INTO dest_subjects (universidad, codigo, codigo_norm, nombre, descripcion, ects)
VALUES (:universidad, :codigo, :codigo_norm, :nombre, :descripcion, :ects)
ON CONFLICT (universidad, codigo) DO UPDATE SET
    codigo_norm = excluded.codigo_norm,
    nombre      = excluded.nombre,
    descripcion = excluded.descripcion,
    ects        = excluded.ects
"""


def normalizar_codigo(codigo: str) -> str:
    """'BMED 2110' -> 'BMED2110': sin espacios y en mayúsculas, igual que en el histórico."""
    return "".join(codigo.split()).upper()


def crear_tabla(con: sqlite3.Connection) -> None:
    """Crea dest_subjects si no existe. No toca las demás tablas de la BD."""
    con.execute(ESQUEMA_DEST_SUBJECTS)
    columnas = {fila[1] for fila in con.execute("PRAGMA table_info(dest_subjects)")}
    if "codigo_norm" not in columnas:  # tablas creadas antes de añadir la columna
        con.execute("ALTER TABLE dest_subjects ADD COLUMN codigo_norm TEXT")
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_dest_subjects_codigo_norm "
        "ON dest_subjects (universidad, codigo_norm)"
    )


def guardar(con: sqlite3.Connection, asignaturas: list[dict], cfg: dict) -> None:
    """Inserta o actualiza las asignaturas en dest_subjects (upsert)."""
    filas = [
        {**a, "codigo_norm": normalizar_codigo(a["codigo"]), "universidad": cfg["university_code"]}
        for a in asignaturas
    ]
    with con:
        con.executemany(SQL_UPSERT, filas)


def ejecutar(uni: str, db_path: Path) -> None:
    """Descarga, lee y guarda todos los departamentos del YAML de <uni>."""
    cfg = cargar_config(uni)
    if not db_path.exists():
        raise SystemExit(
            f"No existe {db_path}. Descárgala primero con: python -m src.sync.datos descargar"
        )
    con = sqlite3.connect(db_path)
    try:
        crear_tabla(con)
        total = 0
        for prefijo in cfg["departments"]:
            html = descargar_departamento(prefijo, cfg)
            asignaturas, fallos = parse_catalog(html, cfg)
            guardar(con, asignaturas, cfg)
            total += len(asignaturas)
            print(f"{prefijo}: {len(asignaturas)} asignaturas, {len(fallos)} títulos sin leer")
            for f in fallos:
                print("    no se pudo leer:", f)
        print(f"Total: {total} asignaturas guardadas en {db_path}")
    finally:
        con.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scraper del catálogo de una universidad de destino"
    )
    parser.add_argument(
        "--uni", required=True, help="nombre del YAML en config/scrapers (p. ej. gatech)"
    )
    parser.add_argument("--db", type=Path, default=DB_POR_DEFECTO, help="ruta de la BD SQLite")
    args = parser.parse_args()
    ejecutar(args.uni, args.db)


if __name__ == "__main__":
    main()
