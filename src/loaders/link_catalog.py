"""Enlace de las filas del histórico con el catálogo de la universidad de destino."""

import re
import sqlite3
from collections import Counter
from collections.abc import Iterable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz, process

from src.loaders.historical_xls import DATABASE_PATH as HISTORICO_PATH
from src.loaders.historical_xls import normalize_text
from src.scrapers.destination import DB_POR_DEFECTO as UC3M_PATH
from src.scrapers.destination import cargar_config, normalizar_codigo

PENDIENTES_PATH = Path("docs/enlace_pendiente.md")
UMBRAL_NOMBRE = 90
# Erratas vistas en el histórico. Solo se prueban si el código tal cual no está en el catálogo,
# porque BIOS también existe como prefijo propio de Georgia Tech.
ALIAS = ((re.compile(r"ROM$"), ""), (re.compile(r"^BIOS(?=\d)"), "BIOL"))
_ORDINAL_FINAL = re.compile(r"\b([IVX]+|\d+)$")
_ROMANOS = {"I": 1, "V": 5, "X": 10}

MOTIVOS = {
    "fuera_de_catalogo": "El código no está en el catálogo y ningún nombre se parece",
    "sin_codigo": "La fila no trae código y ningún nombre se parece",
    "nombre_ambiguo": "El nombre encaja con varias asignaturas",
}


@dataclass(frozen=True)
class AsignaturaDestino:
    """Lo que hace falta de una fila de `dest_subjects`."""

    id: int
    codigo_norm: str
    nombre: str


@dataclass(frozen=True)
class Catalogo:
    """Asignaturas de una universidad, por código y por nombre normalizado."""

    por_codigo: dict[str, AsignaturaDestino]
    por_nombre: dict[str, tuple[AsignaturaDestino, ...]]


@dataclass(frozen=True)
class Enlace:
    """Resultado de una fila. `motivo` y `candidatos` solo se usan si es `unlinked`."""

    dest_subject_id: int | None
    link_method: str
    motivo: str | None = None
    candidatos: tuple[str, ...] = ()


@dataclass(frozen=True)
class FilaHistorico:
    """Lo que hace falta de una fila de `historical_matches`."""

    id: int
    destino_codigo: str | None
    destino_nombre: str


def crear_catalogo(asignaturas: Iterable[AsignaturaDestino]) -> Catalogo:
    """Agrupa las asignaturas. Un nombre puede repetirse: cursos de grado y máster, por ejemplo."""
    asignaturas = tuple(asignaturas)
    por_nombre: dict[str, list[AsignaturaDestino]] = {}
    for asignatura in asignaturas:
        por_nombre.setdefault(normalize_text(asignatura.nombre), []).append(asignatura)
    return Catalogo(
        por_codigo={asignatura.codigo_norm: asignatura for asignatura in asignaturas},
        por_nombre={nombre: tuple(grupo) for nombre, grupo in por_nombre.items()},
    )


def _ordinal(nombre: str) -> int | None:
    """Número final del nombre ya normalizado. `ELECTRONICS 1` y `ELECTRONICS I` dan 1."""
    coincidencia = _ORDINAL_FINAL.search(nombre)
    if coincidencia is None:
        return None
    ordinal = coincidencia.group(1)
    if ordinal.isdigit():
        return int(ordinal)
    valores = [_ROMANOS[letra] for letra in ordinal]
    # Resta si una letra va delante de otra mayor: IV = 4, IX = 9.
    return sum(
        -valor if siguiente > valor else valor
        for valor, siguiente in zip(valores, valores[1:] + [0], strict=True)
    )


def _candidatos_por_nombre(nombre: str, catalogo: Catalogo) -> tuple[AsignaturaDestino, ...]:
    """Asignaturas con nombre parecido. Si alguna coincide exacto, solo cuentan las exactas."""
    buscado = normalize_text(nombre)
    nombres = list(catalogo.por_nombre)
    parecidos = process.extract(
        buscado, nombres, scorer=fuzz.ratio, score_cutoff=UMBRAL_NOMBRE, limit=None
    )
    # PHYSICS I y PHYSICS II sacan un 95, pero son asignaturas distintas.
    # ponytail: solo mira el final del nombre; PHYSICS I LAB y PHYSICS II LAB aún pasarían.
    validos = [fila for fila in parecidos if _ordinal(fila[0]) == _ordinal(buscado)]
    elegidos = [fila for fila in validos if fila[1] == 100] or validos
    return tuple(asignatura for fila in elegidos for asignatura in catalogo.por_nombre[fila[0]])


def enlazar(codigo: str | None, nombre: str, catalogo: Catalogo) -> Enlace:
    """Busca por código, luego por alias y luego por nombre; si nada encaja, `unlinked`."""
    codigo_norm = normalizar_codigo(codigo or "")
    if codigo_norm in catalogo.por_codigo:
        return Enlace(catalogo.por_codigo[codigo_norm].id, "code")

    alias = codigo_norm
    for patron, sustituto in ALIAS:
        alias = patron.sub(sustituto, alias)
        if alias in catalogo.por_codigo:
            return Enlace(catalogo.por_codigo[alias].id, "alias")

    candidatos = _candidatos_por_nombre(nombre, catalogo)
    if len(candidatos) == 1:
        return Enlace(candidatos[0].id, "name")
    if candidatos:
        codigos = tuple(sorted(asignatura.codigo_norm for asignatura in candidatos))
        return Enlace(None, "unlinked", "nombre_ambiguo", codigos)
    return Enlace(None, "unlinked", "fuera_de_catalogo" if codigo_norm else "sin_codigo")


def cargar_catalogo(uc3m_path: str | Path, universidad: str) -> Catalogo:
    """Lee `dest_subjects`. Sin filas se para: marcaría todo el histórico como `unlinked`."""
    uri = f"{Path(uc3m_path).resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        filas = connection.execute(
            "SELECT id, codigo_norm, nombre FROM dest_subjects WHERE universidad = ?",
            (universidad,),
        ).fetchall()
    if not filas:
        raise ValueError(f"dest_subjects no tiene asignaturas de {universidad}")
    return crear_catalogo(AsignaturaDestino(*fila) for fila in filas)


def cargar_filas(connection: sqlite3.Connection, universidad: str) -> tuple[FilaHistorico, ...]:
    """Filas del histórico de una universidad, sin distinguir mayúsculas ni tildes."""
    buscada = normalize_text(universidad)
    filas = connection.execute(
        "SELECT id, universidad, destino_codigo, destino_nombre FROM historical_matches"
    ).fetchall()
    return tuple(
        FilaHistorico(fila[0], fila[2], fila[3])
        for fila in filas
        if normalize_text(fila[1]) == buscada
    )


def guardar_enlaces(
    connection: sqlite3.Connection, resultados: Iterable[tuple[FilaHistorico, Enlace]]
) -> None:
    """Rellena `dest_subject_id` y `link_method`, creando las columnas si faltan.

    `save_historical` rehace la tabla, así que tras recargar el histórico hay que volver a enlazar.
    """
    columnas = {fila[1] for fila in connection.execute("PRAGMA table_info(historical_matches)")}
    for columna, tipo in (("dest_subject_id", "INTEGER"), ("link_method", "TEXT")):
        if columna not in columnas:
            connection.execute(f"ALTER TABLE historical_matches ADD COLUMN {columna} {tipo}")
    connection.executemany(
        "UPDATE historical_matches SET dest_subject_id = ?, link_method = ? WHERE id = ?",
        [(enlace.dest_subject_id, enlace.link_method, fila.id) for fila, enlace in resultados],
    )


def escribir_pendientes(
    resultados: Iterable[tuple[FilaHistorico, Enlace]], path: str | Path
) -> None:
    """Escribe el listado humano de lo no enlazado, una fila por código y nombre distintos."""
    claves = Counter(
        (fila.destino_codigo or "—", fila.destino_nombre, enlace.motivo, enlace.candidatos)
        for fila, enlace in resultados
        if enlace.link_method == "unlinked"
    )
    lineas = [
        "# Enlace pendiente",
        "",
        "Filas del histórico sin asignatura en el catálogo de destino. Quedan con",
        "`link_method = unlinked`: cuentan en la tasa de enlace, pero no calibran ni etiquetan.",
        "",
        "| Código | Nombre en el histórico | Filas | Motivo | Candidatos |",
        "|---|---|---|---|---|",
    ]
    for (codigo, nombre, motivo, candidatos), filas in sorted(claves.items()):
        celdas = (codigo, nombre, str(filas), MOTIVOS[motivo], ", ".join(candidatos) or "—")
        lineas.append("| " + " | ".join(celda.replace("|", "\\|") for celda in celdas) + " |")
    lineas.append("")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lineas), encoding="utf-8")


def ejecutar(
    historico_path: str | Path = HISTORICO_PATH,
    uc3m_path: str | Path = UC3M_PATH,
    pendientes_path: str | Path = PENDIENTES_PATH,
    uni: str = "gatech",
) -> tuple[tuple[FilaHistorico, Enlace], ...]:
    """Enlaza las filas de la universidad, guarda el resultado y el markdown de pendientes."""
    config = cargar_config(uni)
    catalogo = cargar_catalogo(uc3m_path, config["university_code"])
    with closing(sqlite3.connect(historico_path)) as connection, connection:
        filas = cargar_filas(connection, config["university_name"])
        if not filas:
            raise ValueError(f"El histórico no tiene filas de {config['university_name']}")
        resultados = tuple(
            (fila, enlazar(fila.destino_codigo, fila.destino_nombre, catalogo)) for fila in filas
        )
        guardar_enlaces(connection, resultados)
    escribir_pendientes(resultados, pendientes_path)
    return resultados


def resumen(resultados: Iterable[tuple[FilaHistorico, Enlace]]) -> str:
    """Cuenta filas por `link_method`, calculado sobre el resultado."""
    cuentas = Counter(enlace.link_method for _, enlace in resultados)
    total = cuentas.total()
    enlazadas = total - cuentas["unlinked"]
    metodos = ", ".join(f"{cuentas[metodo]} {metodo}" for metodo in ("code", "alias", "name"))
    return (
        f"{enlazadas}/{total} filas enlazadas ({enlazadas / total:.1%}): {metodos}, "
        f"{cuentas['unlinked']} unlinked"
    )


def main() -> None:
    print(resumen(ejecutar()))


if __name__ == "__main__":
    main()
