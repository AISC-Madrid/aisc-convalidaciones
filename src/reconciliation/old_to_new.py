"""Reconciliación de códigos UC3M antiguos con el plan vigente (niveles 1 y 2)."""

import sqlite3
from collections.abc import Callable, Iterable
from contextlib import closing
from dataclasses import dataclass, field, replace
from pathlib import Path

from src.loaders.historical_xls import normalize_text

CURSO_VIGENTE = "2026/2027"
HISTORICO_PATH = Path("data/processed/historico.sqlite")
UC3M_PATH = Path("data/processed/uc3m.sqlite")
PENDIENTES_PATH = Path("docs/reconciliacion_pendiente.md")

# Decididos a mano con las fichas de la UC3M (#57). Solo se aplican si los niveles 1 y 2
# no resuelven el código; el código vigente tiene que existir en el plan vigente.
MANUALES = {
    # Estadística (plan 433) → Inferencia Estadística (plan 567): mismo temario, curso y ECTS.
    "18274": "20563",
    # Ampliación de cálculo numérico (plan 433) → Métodos numéricos para ecuaciones
    # diferenciales (plan 567): la parte de EDO y problemas rígidos es la mayor del temario;
    # los autovalores están en 20561. Revisar si el tutor lo ve de otra forma.
    "18276": "20567",
}

_TABLA = """
CREATE TABLE IF NOT EXISTS old_to_new (
    old_code TEXT PRIMARY KEY,
    new_code TEXT,
    method TEXT CHECK (method IN ('code', 'exact', 'embedding', 'manual'))
)
"""


@dataclass(frozen=True)
class AsignaturaVigente:
    """Asignatura del plan vigente, todavía sin deduplicar."""

    codigo: str
    nombre: str
    idioma: str


@dataclass(frozen=True)
class CodigoAntiguo:
    """Un código del histórico con todos sus nombres distintos."""

    old_code: str
    nombres: tuple[str, ...]
    estudios: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Reconciliacion:
    """Una fila de `old_to_new`. `method` vacío significa que no se resolvió."""

    old_code: str
    new_code: str | None
    method: str | None


@dataclass(frozen=True)
class IndiceVigente:
    """Códigos vigentes y nombres españoles normalizados que apuntan a ellos."""

    codigos: frozenset[str]
    por_nombre: dict[str, frozenset[str]]
    estudios: dict[str, frozenset[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Pendiente:
    """Código antiguo que no resuelven ni el nivel 1 ni el nivel 2."""

    old_code: str
    nombres: tuple[str, ...]
    motivo: str
    candidatos: tuple[str, ...]


def indice_vigente(
    asignaturas: Iterable[AsignaturaVigente],
    estudios: dict[str, frozenset[str]] | None = None,
) -> IndiceVigente:
    """Deduplica por código. El índice de nombres usa solo el español no vacío.

    `estudios` dice en qué estudios se imparte cada código vigente (de `subject_plans`).
    """
    codigos: set[str] = set()
    por_nombre: dict[str, set[str]] = {}
    for asignatura in asignaturas:
        codigos.add(asignatura.codigo)
        if asignatura.idioma != "ES":
            continue
        clave = normalize_text(asignatura.nombre)
        if not clave:
            continue
        por_nombre.setdefault(clave, set()).add(asignatura.codigo)
    return IndiceVigente(
        codigos=frozenset(codigos),
        por_nombre={nombre: frozenset(codes) for nombre, codes in por_nombre.items()},
        estudios=dict(estudios or {}),
    )


def nivel_1(old_code: str, indice: IndiceVigente) -> str | None:
    """Devuelve el mismo código si sigue en el plan vigente."""
    if old_code in indice.codigos:
        return old_code
    return None


def reconciliar(
    antiguos: Iterable[CodigoAntiguo],
    indice: IndiceVigente,
    nivel_2: Callable[[CodigoAntiguo, IndiceVigente], Reconciliacion | None],
    manuales: dict[str, str] | None = None,
) -> tuple[Reconciliacion, ...]:
    """Una fila por código. Nivel 1, luego un `exact` con código nuevo y luego `manuales`."""
    manuales = MANUALES if manuales is None else manuales
    vistos: set[str] = set()
    salida: list[Reconciliacion] = []
    for antiguo in antiguos:
        if antiguo.old_code in vistos:
            continue
        vistos.add(antiguo.old_code)
        if nivel_1(antiguo.old_code, indice) is not None:
            salida.append(Reconciliacion(antiguo.old_code, antiguo.old_code, "code"))
            continue
        resultado = nivel_2(antiguo, indice)
        if resultado is not None and resultado.method == "exact" and resultado.new_code:
            salida.append(Reconciliacion(antiguo.old_code, resultado.new_code, "exact"))
        elif antiguo.old_code in manuales:
            nuevo = manuales[antiguo.old_code]
            if nuevo not in indice.codigos:
                raise ValueError(
                    f"El manual {antiguo.old_code} → {nuevo} apunta a un código que no está "
                    "en el plan vigente: revisa MANUALES."
                )
            salida.append(Reconciliacion(antiguo.old_code, nuevo, "manual"))
        else:
            salida.append(Reconciliacion(antiguo.old_code, None, None))
    return tuple(salida)


def cargar_plan_vigente(
    database_path: str | Path,
    curso_academico: str = CURSO_VIGENTE,
) -> tuple[AsignaturaVigente, ...]:
    """Lee `subjects` de un curso. No une con `subject_plans`."""
    consulta = """
        SELECT codigo, COALESCE(nombre, ''), idioma
        FROM subjects
        WHERE curso_academico = ?
          AND codigo IS NOT NULL
          AND codigo != ''
        ORDER BY codigo, idioma
    """
    with closing(_conectar_lectura(database_path)) as connection:
        filas = connection.execute(consulta, (curso_academico,)).fetchall()
    return tuple(
        AsignaturaVigente(str(codigo), str(nombre), str(idioma)) for codigo, nombre, idioma in filas
    )


def cargar_estudios(
    database_path: str | Path, curso_academico: str | None = None
) -> dict[str, frozenset[str]]:
    """Estudios de cada código según `subject_plans`, de un curso o de todos.

    Sin la tabla o sin la columna `estudio` devuelve `{}` y no se filtra por estudio.
    """
    consulta = "SELECT codigo, estudio FROM subject_plans WHERE estudio IS NOT NULL"
    parametros: tuple[str, ...] = ()
    if curso_academico is not None:
        consulta += " AND curso_academico = ?"
        parametros = (curso_academico,)
    with closing(_conectar_lectura(database_path)) as connection:
        try:
            filas = connection.execute(consulta, parametros).fetchall()
        except sqlite3.OperationalError:
            return {}
    estudios: dict[str, set[str]] = {}
    for codigo, estudio in filas:
        estudios.setdefault(str(codigo), set()).add(str(estudio))
    return {codigo: frozenset(valores) for codigo, valores in estudios.items()}


def guardar_reconciliacion(
    filas: Iterable[Reconciliacion],
    database_path: str | Path,
) -> None:
    """Sustituye solo las filas de `old_to_new`. No borra el resto de tablas."""
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(_TABLA)
        connection.execute("DELETE FROM old_to_new")
        connection.executemany(
            "INSERT INTO old_to_new (old_code, new_code, method) VALUES (?, ?, ?)",
            [(fila.old_code, fila.new_code, fila.method) for fila in filas],
        )


def codigos_antiguos(filas: Iterable[tuple[str, str]]) -> tuple[CodigoAntiguo, ...]:
    """Agrupa `(codigo, nombre)` y conserva cada nombre distinto, en orden de aparición."""
    orden: list[str] = []
    nombres: dict[str, list[str]] = {}
    vistos: dict[str, set[str]] = {}
    for codigo, nombre in filas:
        if codigo is None or str(codigo) == "":
            continue
        codigo = str(codigo)
        nombre = "" if nombre is None else str(nombre)
        if codigo not in nombres:
            orden.append(codigo)
            nombres[codigo] = []
            vistos[codigo] = set()
        if nombre not in vistos[codigo]:
            vistos[codigo].add(nombre)
            nombres[codigo].append(nombre)
    return tuple(CodigoAntiguo(codigo, tuple(nombres[codigo])) for codigo in orden)


def cargar_codigos_historico(database_path: str | Path) -> tuple[CodigoAntiguo, ...]:
    """Lee códigos y nombres del histórico. No escribe en la base."""
    consulta = """
        SELECT uc3m_codigo, uc3m_nombre
        FROM historical_matches
        WHERE uc3m_codigo IS NOT NULL AND uc3m_codigo != ''
        ORDER BY uc3m_codigo, uc3m_nombre
    """
    with closing(_conectar_lectura(database_path)) as connection:
        filas = connection.execute(consulta).fetchall()
    return codigos_antiguos(filas)


def _coincidencias(
    antiguo: CodigoAntiguo, indice: IndiceVigente
) -> tuple[frozenset[str], ...]:
    """Códigos vigentes a los que apunta cada nombre, ya normalizado.

    Si se conocen los estudios del código antiguo, solo cuentan los vigentes del mismo estudio:
    «Estadística» existe en muchos grados y no vale la de otro.
    """
    coincidencias = tuple(
        indice.por_nombre.get(normalize_text(nombre), frozenset()) for nombre in antiguo.nombres
    )
    if not antiguo.estudios:
        return coincidencias
    return tuple(
        frozenset(
            codigo
            for codigo in conjunto
            if indice.estudios.get(codigo, frozenset()) & antiguo.estudios
        )
        for conjunto in coincidencias
    )


def _codigo_exacto(coincidencias: Iterable[frozenset[str]]) -> str | None:
    """Un código si todos los nombres que coinciden apuntan a él y ninguno es ambiguo."""
    conjuntos = tuple(coincidencias)
    if any(len(conjunto) > 1 for conjunto in conjuntos):
        return None
    no_vacios = [conjunto for conjunto in conjuntos if conjunto]
    if not no_vacios:
        return None
    union = set().union(*no_vacios)
    if len(union) == 1:
        return next(iter(union))
    return None


def nivel_2(antiguo: CodigoAntiguo, indice: IndiceVigente) -> Reconciliacion | None:
    """Match por nombre normalizado exacto. None si no hay un único código compatible."""
    codigo = _codigo_exacto(_coincidencias(antiguo, indice))
    if codigo is None:
        return None
    return Reconciliacion(antiguo.old_code, codigo, "exact")


def motivo_pendiente(antiguo: CodigoAntiguo, indice: IndiceVigente) -> Pendiente:
    """Por qué no hay `exact`, y los candidatos vigentes (del mismo estudio si se sabe)."""
    coincidencias = _coincidencias(antiguo, indice)
    candidatos = tuple(sorted(set().union(*coincidencias)))
    if any(len(conjunto) > 1 for conjunto in coincidencias):
        motivo = "ambiguo"
    elif len({next(iter(conjunto)) for conjunto in coincidencias if conjunto}) > 1:
        motivo = "nombres_incompatibles"
    else:
        motivo = "sin_coincidencia"
    return Pendiente(antiguo.old_code, antiguo.nombres, motivo, candidatos)


def escribir_pendientes(pendientes: Iterable[Pendiente], path: str | Path) -> None:
    """Escribe el listado humano de códigos sin resolver."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        "# Reconciliación pendiente",
        "",
        "Códigos UC3M del histórico sin match en el plan vigente por código ni por nombre",
        "normalizado exacto ni decisión manual (`MANUALES`). Quedan con `new_code` y",
        "`method` vacíos. Los candidatos son del mismo estudio cuando se conoce. El nivel 3,",
        "por contenido, queda para la semana 6.",
        "",
        "| Código antiguo | Nombres en el histórico | Motivo | Candidatos |",
        "|---|---|---|---|",
    ]
    for pendiente in sorted(pendientes, key=lambda item: item.old_code):
        nombres = "; ".join(pendiente.nombres) or "—"
        candidatos = ", ".join(pendiente.candidatos) or "—"
        celdas = (pendiente.old_code, nombres, pendiente.motivo, candidatos)
        lineas.append("| " + " | ".join(_celda(celda) for celda in celdas) + " |")
    lineas.append("")
    path.write_text("\n".join(lineas), encoding="utf-8")


def ejecutar(
    historico_path: str | Path = HISTORICO_PATH,
    uc3m_path: str | Path = UC3M_PATH,
    pendientes_path: str | Path = PENDIENTES_PATH,
    curso_academico: str = CURSO_VIGENTE,
) -> tuple[Reconciliacion, ...]:
    """Carga las dos bases, reconcilia, guarda `old_to_new` y el markdown de pendientes."""
    estudios_antiguos = cargar_estudios(uc3m_path)
    antiguos = tuple(
        replace(antiguo, estudios=estudios_antiguos.get(antiguo.old_code, frozenset()))
        for antiguo in cargar_codigos_historico(historico_path)
    )
    indice = indice_vigente(
        cargar_plan_vigente(uc3m_path, curso_academico),
        cargar_estudios(uc3m_path, curso_academico),
    )
    por_codigo = {antiguo.old_code: antiguo for antiguo in antiguos}
    filas = reconciliar(antiguos, indice, nivel_2)
    guardar_reconciliacion(filas, uc3m_path)
    escribir_pendientes(
        (
            motivo_pendiente(por_codigo[fila.old_code], indice)
            for fila in filas
            if fila.method is None
        ),
        pendientes_path,
    )
    return filas


def resumen(filas: Iterable[Reconciliacion]) -> str:
    """Cuenta filas por `method`, calculado sobre el resultado, no con cifras fijas."""
    filas = tuple(filas)
    code = sum(fila.method == "code" for fila in filas)
    exact = sum(fila.method == "exact" for fila in filas)
    manual = sum(fila.method == "manual" for fila in filas)
    sin_resolver = sum(fila.method is None for fila in filas)
    return (
        f"{code} con method=code, {exact} con exact, {manual} con manual, "
        f"{sin_resolver} con NULL"
    )


def _conectar_lectura(database_path: str | Path) -> sqlite3.Connection:
    uri = f"{Path(database_path).resolve().as_uri()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _celda(valor: str) -> str:
    return valor.replace("|", "\\|").replace("\n", " ")


def main() -> None:
    print(resumen(ejecutar()))


if __name__ == "__main__":
    main()
