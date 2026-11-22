"""Tasas de enlace y tabla de calibración sobre el histórico ya enlazado."""

import sqlite3
from collections.abc import Iterable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from src.loaders.historical_xls import DATABASE_PATH as HISTORICO_PATH
from src.loaders.historical_xls import normalize_text
from src.scrapers.destination import DB_POR_DEFECTO as UC3M_PATH

INFORME_PATH = Path("docs/tasas_enlace.md")
METODOS_ENLAZADOS = frozenset({"code", "alias", "name"})
GRADO_PILOTO = "BIOMEDICA"
MINIMO_UMBRAL_PROPIO = 20
# Asignaturas transversales de la UC3M (#56). La UC3M las reconoce a cambio de cualquier
# asignatura del destino, así que el par no es una equivalencia de contenido: no calibra
# ni debe etiquetarse como precedente.
TRANSVERSALES = frozenset(
    {
        "14155",  # Técnicas de búsqueda y uso de la información
        "14528",  # Habilidades profesionales (y «… movilidad»)
        "17597",  # Hojas de cálculo. Nivel intermedio
        "17639",  # Hojas de cálculo. Nivel avanzado (3 ECTS)
        "17881",  # Hojas de cálculo. Nivel avanzado (1,5 ECTS)
    }
)

_CONSULTA = """
SELECT
    h.id,
    h.grado,
    h.uc3m_codigo,
    h.uc3m_nombre,
    COALESCE(h.destino_codigo, ''),
    h.destino_nombre,
    h.grupo,
    h.dest_subject_id,
    h.link_method,
    o.new_code,
    o.method,
    d.codigo,
    d.nombre
FROM historical_matches AS h
LEFT JOIN uc3m.old_to_new AS o ON o.old_code = h.uc3m_codigo
LEFT JOIN uc3m.dest_subjects AS d ON d.id = h.dest_subject_id
WHERE h.link_method IS NOT NULL
ORDER BY h.id
"""


@dataclass(frozen=True)
class FilaEnlace:
    """Una fila de Georgia Tech con su enlace y, si existe, su reconciliación."""

    id: int
    grado: str
    uc3m_codigo: str
    uc3m_nombre: str
    destino_codigo: str
    destino_nombre: str
    grupo: int | None
    dest_subject_id: int | None
    link_method: str
    new_code: str | None
    reconciliation_method: str | None
    catalogo_codigo: str | None
    catalogo_nombre: str | None


@dataclass(frozen=True)
class Tasa:
    """Enlazadas sobre el total. `unlinked` cuenta en el total."""

    ambito: str
    enlazadas: int
    total: int

    @property
    def ratio(self) -> float:
        if self.total == 0:
            return 0.0
        return self.enlazadas / self.total


@dataclass(frozen=True)
class TasaGrado:
    """Enlazadas de un grado. El umbral propio de la fase 2 pide al menos 20."""

    grado: str
    enlazadas: int
    total: int

    @property
    def ratio(self) -> float:
        if self.total == 0:
            return 0.0
        return self.enlazadas / self.total

    @property
    def umbral_propio(self) -> bool:
        return self.enlazadas >= MINIMO_UMBRAL_PROPIO


@dataclass(frozen=True)
class ParCalibracion:
    """Par del piloto reconciliado y enlazado: entrada del notebook de la semana 5."""

    uc3m_codigo: str
    new_code: str
    uc3m_nombre: str
    reconciliation_method: str
    destino_codigo: str
    destino_nombre: str
    catalogo_codigo: str | None
    catalogo_nombre: str | None
    dest_subject_id: int
    link_method: str
    grupo: int | None


def es_piloto(fila: FilaEnlace) -> bool:
    """Ingeniería Biomédica, sin depender de tildes ni de mayúsculas."""
    return GRADO_PILOTO in normalize_text(fila.grado)


def es_enlazada(fila: FilaEnlace) -> bool:
    """Tiene asignatura de catálogo. `unlinked` cuenta en la tasa, pero no calibra."""
    return fila.link_method in METODOS_ENLAZADOS and fila.dest_subject_id is not None


def es_transversal(codigo: str | None) -> bool:
    """Código UC3M de una asignatura transversal: no es una equivalencia de contenido."""
    return (codigo or "") in TRANSVERSALES


def es_calibrable(fila: FilaEnlace) -> bool:
    """Piloto, enlazada, con código vigente en `old_to_new` y no transversal."""
    return (
        es_piloto(fila)
        and es_enlazada(fila)
        and bool(fila.new_code)
        and bool(fila.reconciliation_method)
        and not es_transversal(fila.uc3m_codigo)
        and not es_transversal(fila.new_code)
    )


def tasa(filas: Iterable[FilaEnlace], ambito: str) -> Tasa:
    """Cuenta enlazadas y total. El total incluye las `unlinked`."""
    filas = tuple(filas)
    return Tasa(ambito, sum(es_enlazada(fila) for fila in filas), len(filas))


def tasas_por_grado(filas: Iterable[FilaEnlace]) -> tuple[TasaGrado, ...]:
    """Una fila por grado, de más pares enlazados a menos."""
    grupos: dict[str, list[FilaEnlace]] = {}
    for fila in filas:
        grupos.setdefault(normalize_text(fila.grado), []).append(fila)
    tasas = tuple(
        TasaGrado(grupo[0].grado, sum(es_enlazada(fila) for fila in grupo), len(grupo))
        for grupo in grupos.values()
    )
    return tuple(sorted(tasas, key=lambda item: (-item.enlazadas, item.grado)))


def grados_con_umbral_propio(tasas_grado: Iterable[TasaGrado]) -> int:
    """Grados con pares enlazados suficientes para un umbral propio en la fase 2."""
    return sum(item.umbral_propio for item in tasas_grado)


def tabla_calibracion(filas: Iterable[FilaEnlace]) -> tuple[ParCalibracion, ...]:
    """Pares de Biomédica que la semana 5 puede calibrar, ordenados por código vigente."""
    pares = [
        ParCalibracion(
            fila.uc3m_codigo,
            fila.new_code,
            fila.uc3m_nombre,
            fila.reconciliation_method,
            fila.destino_codigo,
            fila.destino_nombre,
            fila.catalogo_codigo,
            fila.catalogo_nombre,
            fila.dest_subject_id,
            fila.link_method,
            fila.grupo,
        )
        for fila in filas
        if es_calibrable(fila)
    ]
    return tuple(
        sorted(pares, key=lambda par: (par.new_code, par.catalogo_codigo or "", par.uc3m_codigo))
    )


def asignaturas_uc3m(pares: Iterable[ParCalibracion]) -> int:
    """Códigos vigentes distintos. Una asignatura con dos destinos cuenta una vez."""
    return len({par.new_code for par in pares})


def transversales_excluidas(filas: Iterable[FilaEnlace]) -> tuple[FilaEnlace, ...]:
    """Enlazadas del piloto que no entran en la tabla por ser transversales."""
    return tuple(
        fila
        for fila in filas
        if es_piloto(fila) and es_enlazada(fila) and es_transversal(fila.uc3m_codigo)
    )


def sin_reconciliar(filas: Iterable[FilaEnlace]) -> tuple[FilaEnlace, ...]:
    """Enlazadas del piloto que no entran en la tabla porque el código UC3M sigue pendiente."""
    return tuple(
        fila
        for fila in filas
        if es_piloto(fila)
        and es_enlazada(fila)
        and not es_transversal(fila.uc3m_codigo)
        and not es_calibrable(fila)
    )


def muestra_enlaces(filas: Iterable[FilaEnlace], n: int = 10) -> tuple[FilaEnlace, ...]:
    """Hasta `n` enlaces distintos, con los alias y los de nombre delante de los de código.

    Un mismo par código histórico → catálogo sale una vez aunque se repita en varios grados.
    """
    enlazadas = [fila for fila in filas if es_enlazada(fila)]

    def coger(metodo: str) -> list[FilaEnlace]:
        grupo = [fila for fila in enlazadas if fila.link_method == metodo]
        grupo.sort(key=lambda fila: (not es_piloto(fila), fila.id))
        return grupo

    vistos: set[tuple[str, str | None]] = set()
    elegidas = []
    for fila in coger("alias") + coger("name") + coger("code"):
        clave = (fila.destino_codigo.replace(" ", "").upper(), fila.catalogo_codigo)
        if clave not in vistos:
            vistos.add(clave)
            elegidas.append(fila)
    return tuple(elegidas[:n])


def texto_tasa(item: Tasa | TasaGrado) -> str:
    """`38/39 (97.4%)`."""
    return f"{item.enlazadas}/{item.total} ({item.ratio:.1%})"


def prefijo(codigo: str | None) -> str:
    """Letras del código: `CS 1332` y `PHYS3141` dan `CS` y `PHYS`."""
    return "".join(caracter for caracter in (codigo or "") if caracter.isalpha())


def prefijos_catalogo(filas: Iterable[FilaEnlace]) -> tuple[str, ...]:
    """Prefijos que sí aparecen en un código de catálogo enlazado."""
    return tuple(
        sorted({prefijo(fila.catalogo_codigo) for fila in filas if prefijo(fila.catalogo_codigo)})
    )


def fuera_de_catalogo(filas: Iterable[FilaEnlace]) -> tuple[int, int]:
    """No enlazadas con prefijo ausente del catálogo, y cuántas no enlazadas hay."""
    filas = tuple(filas)
    presentes = set(prefijos_catalogo(filas))
    no_enlazadas = [fila for fila in filas if not es_enlazada(fila)]
    fuera = sum(prefijo(fila.destino_codigo) not in presentes for fila in no_enlazadas)
    return fuera, len(no_enlazadas)


def _frase_cobertura(filas: tuple[FilaEnlace, ...]) -> str:
    """Explica cuántas no enlazadas caen fuera de los departamentos cargados."""
    fuera, no_enlazadas = fuera_de_catalogo(filas)
    presentes = set(prefijos_catalogo(filas))
    ausentes = sorted(
        {prefijo(fila.destino_codigo) for fila in filas if not es_enlazada(fila)} - presentes
    )
    frase = f"{fuera} de {no_enlazadas} no enlazadas tienen un prefijo que no está en el catálogo"
    if ausentes:
        frase += f" ({', '.join(ausentes)})"
    resto = "Todas tienen" if fuera == 0 else "El resto tiene"
    return (
        f"{frase}. {resto} su departamento cargado, pero el código no está en el "
        "catálogo 2026-27 y ningún nombre se parece. El motivo de cada una está en "
        "`docs/enlace_pendiente.md`."
    )


def _celda(valor: object) -> str:
    texto = "—" if valor is None or valor == "" else str(valor)
    return texto.replace("|", "\\|")


def _fila_markdown(celdas: Iterable[object]) -> str:
    return "| " + " | ".join(_celda(celda) for celda in celdas) + " |"


def informe(filas: Iterable[FilaEnlace]) -> str:
    """Markdown con las tres tasas, el tamaño de la tabla y los pares de calibración."""
    filas = tuple(filas)
    piloto = tuple(fila for fila in filas if es_piloto(fila))
    tasa_piloto = tasa(piloto, "Ingeniería Biomédica")
    tasa_todo = tasa(filas, "Georgia Tech")
    por_grado = tasas_por_grado(filas)
    con_umbral = grados_con_umbral_propio(por_grado)
    pares = tabla_calibracion(filas)
    pendientes = sin_reconciliar(filas)
    transversales = transversales_excluidas(filas)
    if tasa_piloto.ratio < 0.5:
        viernes = (
            "Por debajo del 50 %: la semana 5 corrige el enlace antes del notebook "
            "de calibración."
        )
    else:
        viernes = "Por encima del 50 %: la semana 5 puede calibrar sin corregir el enlace antes."

    lineas = [
        "# Tasas de enlace (Georgia Tech)",
        "",
        "Calculadas sobre `historical_matches` después de enlazar con el catálogo.",
        "Una fila está enlazada si `link_method` es `code`, `alias` o `name`.",
        "`unlinked` entra en el denominador y no calibra. Las filas de otras",
        "universidades tienen `link_method` vacío y no entran.",
        "",
        "El plan cita 49/50 en Biomédica y 263/276 en Georgia Tech: es el recuento",
        "a mano del EDA, antes de deduplicar y con el catálogo entero. Aquí el",
        "denominador es la tabla ya deduplicada, y solo enlaza lo que está en",
        "`dest_subjects`.",
        "",
        "## Biomédica",
        "",
        texto_tasa(tasa_piloto),
        "",
        viernes,
        "",
        "## Georgia Tech",
        "",
        texto_tasa(tasa_todo),
        "",
        _frase_cobertura(filas),
        "",
        "## Por grado",
        "",
        f"Grados con al menos {MINIMO_UMBRAL_PROPIO} pares enlazados, el mínimo para",
        f"un umbral propio en la fase 2: {con_umbral} de {len(por_grado)}.",
        "",
        "| Grado | Enlazadas | Total | Tasa | Umbral propio |",
        "|---|---|---|---|---|",
    ]
    for item in por_grado:
        propio = "sí" if item.umbral_propio else "no"
        lineas.append(
            _fila_markdown((item.grado, item.enlazadas, item.total, texto_tasa(item), propio))
        )
    lineas.extend(
        [
            "",
            "## Tabla de calibración",
            "",
            "Pares de Biomédica reconciliados y enlazados. La semana 5 los lee con",
            "`tabla_calibracion(cargar_filas())`.",
            "",
            f"- Pares: {len(pares)}",
            f"- Asignaturas UC3M distintas: {asignaturas_uc3m(pares)}",
            "- Enlazadas del piloto fuera de la tabla, con el código UC3M pendiente: "
            f"{len(pendientes)}",
            "- Enlazadas del piloto fuera de la tabla por ser transversales "
            f"(`TRANSVERSALES`): {len(transversales)}",
            "",
            "| Código vigente | Código antiguo | Asignatura UC3M | Reconciliación | "
            "Código histórico | Nombre histórico | Código catálogo | Nombre catálogo | "
            "Método | Grupo |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for par in pares:
        lineas.append(
            _fila_markdown(
                (
                    par.new_code,
                    par.uc3m_codigo,
                    par.uc3m_nombre,
                    par.reconciliation_method,
                    par.destino_codigo,
                    par.destino_nombre,
                    par.catalogo_codigo,
                    par.catalogo_nombre,
                    par.link_method,
                    par.grupo,
                )
            )
        )
    lineas.extend(
        [
            "",
            "## Vistazo de 10 enlaces",
            "",
            "Alias y nombre primero: son los que no salen de una coincidencia de código.",
            "La lectura está en `notebooks/02_enlace_gatech.ipynb`.",
            "",
            "| id | Grado | Código histórico | Nombre histórico | Código catálogo | "
            "Nombre catálogo | Método |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for fila in muestra_enlaces(filas):
        lineas.append(
            _fila_markdown(
                (
                    fila.id,
                    fila.grado,
                    fila.destino_codigo,
                    fila.destino_nombre,
                    fila.catalogo_codigo,
                    fila.catalogo_nombre,
                    fila.link_method,
                )
            )
        )
    lineas.append("")
    return "\n".join(lineas)


def escribir_informe(filas: Iterable[FilaEnlace], path: str | Path = INFORME_PATH) -> str:
    """Escribe el informe y devuelve el mismo texto."""
    texto = informe(filas)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(texto, encoding="utf-8")
    return texto


def cargar_filas(
    historico_path: str | Path = HISTORICO_PATH,
    uc3m_path: str | Path = UC3M_PATH,
) -> tuple[FilaEnlace, ...]:
    """Lee el histórico enlazado y le junta `old_to_new` y `dest_subjects`."""
    with closing(sqlite3.connect(historico_path)) as connection:
        connection.execute("ATTACH DATABASE ? AS uc3m", (str(Path(uc3m_path).resolve()),))
        try:
            crudas = connection.execute(_CONSULTA).fetchall()
        except sqlite3.OperationalError as error:
            raise ValueError(
                "Falta el enlace o la reconciliación. Ejecuta "
                "`python -m src.loaders.link_catalog` y "
                "`python -m src.reconciliation.old_to_new`."
            ) from error
    if not crudas:
        raise ValueError("No hay filas con link_method. Ejecuta link_catalog sobre el histórico.")
    return tuple(
        FilaEnlace(
            fila[0],
            fila[1],
            "" if fila[2] is None else str(fila[2]),
            "" if fila[3] is None else str(fila[3]),
            fila[4],
            "" if fila[5] is None else str(fila[5]),
            fila[6],
            fila[7],
            fila[8],
            fila[9],
            fila[10],
            fila[11],
            fila[12],
        )
        for fila in crudas
    )


def main() -> None:
    filas = cargar_filas()
    piloto = tasa(tuple(fila for fila in filas if es_piloto(fila)), "Biomédica")
    todo = tasa(filas, "Georgia Tech")
    por_grado = tasas_por_grado(filas)
    pares = tabla_calibracion(filas)
    escribir_informe(filas)
    print(
        f"Biomédica {texto_tasa(piloto)}; Georgia Tech {texto_tasa(todo)}; "
        f"{grados_con_umbral_propio(por_grado)} de {len(por_grado)} grados con "
        f">= {MINIMO_UMBRAL_PROPIO} pares enlazados; "
        f"calibración {len(pares)} pares, {asignaturas_uc3m(pares)} asignaturas UC3M. "
        f"Informe en {INFORME_PATH}."
    )


if __name__ == "__main__":
    main()
