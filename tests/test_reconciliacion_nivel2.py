import sqlite3
from contextlib import closing

from src.reconciliation.old_to_new import (
    AsignaturaVigente,
    CodigoAntiguo,
    IndiceVigente,
    Pendiente,
    Reconciliacion,
    cargar_codigos_historico,
    codigos_antiguos,
    escribir_pendientes,
    indice_vigente,
    motivo_pendiente,
    nivel_2,
)


def _indice() -> IndiceVigente:
    return indice_vigente(
        [
            AsignaturaVigente("10", "Cálculo", "ES"),
            AsignaturaVigente("11", "Física", "ES"),
        ]
    )


def test_nombre_exacto_unico():
    antiguo = CodigoAntiguo("99", ("Cálculo",))

    assert nivel_2(antiguo, _indice()) == Reconciliacion("99", "10", "exact")


def test_sin_coincidencia():
    indice = _indice()
    antiguo = CodigoAntiguo("99", ("Química orgánica",))

    assert nivel_2(antiguo, indice) is None
    assert motivo_pendiente(antiguo, indice) == Pendiente(
        "99", ("Química orgánica",), "sin_coincidencia", ()
    )


def test_nombre_ambiguo():
    indice = indice_vigente(
        [
            AsignaturaVigente("10", "Estadística", "ES"),
            AsignaturaVigente("11", "Estadística", "ES"),
        ]
    )
    antiguo = CodigoAntiguo("99", ("Estadística",))

    assert nivel_2(antiguo, indice) is None
    assert motivo_pendiente(antiguo, indice) == Pendiente(
        "99", ("Estadística",), "ambiguo", ("10", "11")
    )


def test_tildes_mayusculas_y_espacios():
    indice = indice_vigente([AsignaturaVigente("10", "Álgebra  Lineal", "ES")])
    antiguo = CodigoAntiguo("99", ("  algebra\tlineal ",))

    assert nivel_2(antiguo, indice) == Reconciliacion("99", "10", "exact")


def test_varias_filas_y_nombres_por_codigo_antiguo():
    filas = [
        ("1", "Habilidades Profesionales"),
        ("1", "Habilidades Profesionales"),
        ("1", "Habilidades profesionales movilidad"),
        ("2", "Cálculo"),
        ("", "Sin código"),
    ]

    assert codigos_antiguos(filas) == (
        CodigoAntiguo("1", ("Habilidades Profesionales", "Habilidades profesionales movilidad")),
        CodigoAntiguo("2", ("Cálculo",)),
    )


def test_cargar_codigos_historico_agrupa_sin_escribir(tmp_path):
    database_path = tmp_path / "historico.sqlite"
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(
            "CREATE TABLE historical_matches (uc3m_codigo TEXT, uc3m_nombre TEXT, ects REAL)"
        )
        connection.executemany(
            "INSERT INTO historical_matches VALUES (?, ?, ?)",
            [
                ("1", "Habilidades profesionales movilidad", 6),
                ("1", "Habilidades Profesionales", 6),
                ("1", "Habilidades Profesionales", 6),
                ("2", "Cálculo", 6),
            ],
        )

    assert cargar_codigos_historico(database_path) == (
        CodigoAntiguo("1", ("Habilidades Profesionales", "Habilidades profesionales movilidad")),
        CodigoAntiguo("2", ("Cálculo",)),
    )
    with closing(sqlite3.connect(database_path)) as connection:
        tablas = {
            fila[0]
            for fila in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert tablas == {"historical_matches"}


def test_nombres_incompatibles():
    indice = _indice()
    antiguo = CodigoAntiguo("99", ("Cálculo", "Física"))

    assert nivel_2(antiguo, indice) is None
    assert motivo_pendiente(antiguo, indice) == Pendiente(
        "99", ("Cálculo", "Física"), "nombres_incompatibles", ("10", "11")
    )


def test_un_nombre_sin_hit_no_invalida_el_unico():
    indice = _indice()
    antiguo = CodigoAntiguo("99", ("Cálculo", "Nombre que no existe"))

    assert nivel_2(antiguo, indice) == Reconciliacion("99", "10", "exact")


def test_escribe_el_listado_de_pendientes(tmp_path):
    path = tmp_path / "docs" / "reconciliacion_pendiente.md"
    escribir_pendientes(
        [
            Pendiente("18276", ("Ampliación de cálculo numérico",), "sin_coincidencia", ()),
            Pendiente("18274", ("Estadística",), "ambiguo", ("13410", "13876")),
        ],
        path,
    )

    texto = path.read_text(encoding="utf-8")
    estadistica = texto.index("18274")
    ampliacion = texto.index("18276")
    assert estadistica < ampliacion
    assert "ambiguo" in texto
    assert "sin_coincidencia" in texto
    assert "13410, 13876" in texto
