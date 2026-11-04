import sqlite3
from contextlib import closing

import pytest

from src.loaders.link_catalog import (
    AsignaturaDestino,
    Enlace,
    FilaHistorico,
    crear_catalogo,
    ejecutar,
    enlazar,
    escribir_pendientes,
    resumen,
)


def _catalogo():
    return crear_catalogo(
        [
            AsignaturaDestino(1, "CS1332", "Data Structures"),
            AsignaturaDestino(2, "AE4699", "Undergraduate Research"),
            AsignaturaDestino(3, "BIOL7210", "Computational Genomics"),
            AsignaturaDestino(4, "BIOS1107", "Biological Principles"),
            AsignaturaDestino(5, "BIOL1107", "Otra Asignatura"),
            AsignaturaDestino(6, "PHYS2211", "Principles of Physics I"),
            AsignaturaDestino(7, "PHYS2212", "Principles of Physics II"),
            AsignaturaDestino(8, "ECE4100", "Advanced Computer Architecture"),
            AsignaturaDestino(9, "ECE6100", "Advanced Computer Architecture"),
        ]
    )


@pytest.mark.parametrize("codigo", ["CS1332", "CS 1332", "cs 1332"])
def test_codigo_normalizado(codigo):
    assert enlazar(codigo, "Otro nombre", _catalogo()) == Enlace(1, "code")


def test_alias_sufijo_rom():
    assert enlazar("AE4699ROM", "Research in Rome", _catalogo()) == Enlace(2, "alias")


def test_alias_prefijo_doble():
    assert enlazar("BIOS7210", "Genomics", _catalogo()) == Enlace(3, "alias")


def test_prefijo_bios_que_existe_no_es_alias():
    assert enlazar("BIOS1107", "Biological Principles", _catalogo()) == Enlace(4, "code")


@pytest.mark.parametrize("codigo", [None, "", "XX9999"])
def test_por_nombre_parecido_con_o_sin_codigo(codigo):
    assert enlazar(codigo, "DATA STRUCTURE", _catalogo()) == Enlace(1, "name")


def test_nombre_exacto_con_tildes():
    assert enlazar(None, "Computatíonal Genomics", _catalogo()) == Enlace(3, "name")


def test_nombre_por_debajo_del_umbral():
    assert enlazar(None, "Data", _catalogo()) == Enlace(None, "unlinked", "sin_codigo")


def test_ordinal_distinto_no_enlaza_y_el_exacto_gana():
    assert enlazar(None, "Principles of Physics II", _catalogo()) == Enlace(7, "name")
    assert enlazar(None, "Principles of Physics III", _catalogo()).link_method == "unlinked"


def test_nombre_repetido_en_el_catalogo_es_ambiguo():
    assert enlazar(None, "Advanced Computer Architecture", _catalogo()) == Enlace(
        None, "unlinked", "nombre_ambiguo", ("ECE4100", "ECE6100")
    )


def test_codigo_fuera_de_catalogo():
    assert enlazar("PHYS3211", "Quantum Mechanics", _catalogo()) == Enlace(
        None, "unlinked", "fuera_de_catalogo"
    )


def test_pendientes_agrupa_y_explica(tmp_path):
    enlace = Enlace(None, "unlinked", "fuera_de_catalogo")
    resultados = [
        (FilaHistorico(1, "PHYS3211", "Quantum"), enlace),
        (FilaHistorico(2, "PHYS3211", "Quantum"), enlace),
        (FilaHistorico(3, "CS1332", "Data"), Enlace(1, "code")),
    ]
    path = tmp_path / "enlace_pendiente.md"

    escribir_pendientes(resultados, path)

    texto = path.read_text(encoding="utf-8")
    assert "| PHYS3211 | Quantum | 2 | El código no está en el catálogo" in texto
    assert "CS1332" not in texto


def _bases(tmp_path, filas_historico):
    historico, uc3m = tmp_path / "historico.sqlite", tmp_path / "uc3m.sqlite"
    with closing(sqlite3.connect(uc3m)) as connection, connection:
        connection.execute(
            "CREATE TABLE dest_subjects (id INTEGER PRIMARY KEY, universidad, codigo_norm, nombre)"
        )
        connection.execute("INSERT INTO dest_subjects VALUES (7, 'GATECH', 'CS1332', 'Data')")
    with closing(sqlite3.connect(historico)) as connection, connection:
        connection.execute(
            "CREATE TABLE historical_matches "
            "(id INTEGER PRIMARY KEY, universidad, destino_codigo, destino_nombre)"
        )
        connection.executemany(
            "INSERT INTO historical_matches (universidad, destino_codigo, destino_nombre) "
            "VALUES (?, ?, ?)",
            filas_historico,
        )
    return historico, uc3m


def test_ejecutar_guarda_solo_la_universidad_y_se_puede_relanzar(tmp_path):
    historico, uc3m = _bases(
        tmp_path,
        [
            ("GEORGIA INSTITUTE OF TECHNOLOGY", "CS1332", "Data"),
            ("Georgia Institute of Technology", "PHYS3211", "Quantum"),
            ("UNIVERSITY OF CALIFORNIA", "CS1332", "Data"),
        ],
    )
    pendientes = tmp_path / "enlace_pendiente.md"

    ejecutar(historico, uc3m, pendientes)
    resultados = ejecutar(historico, uc3m, pendientes)

    with closing(sqlite3.connect(historico)) as connection:
        filas = connection.execute(
            "SELECT dest_subject_id, link_method FROM historical_matches ORDER BY id"
        ).fetchall()
    assert filas == [(7, "code"), (None, "unlinked"), (None, None)]
    assert "PHYS3211" in pendientes.read_text(encoding="utf-8")
    assert resumen(resultados) == "1/2 filas enlazadas (50.0%): 1 code, 0 alias, 0 name, 1 unlinked"


def test_ejecutar_sin_filas_de_la_universidad_no_escribe(tmp_path):
    historico, uc3m = _bases(tmp_path, [("UNIVERSITY OF CALIFORNIA", "CS1332", "Data")])
    pendientes = tmp_path / "enlace_pendiente.md"

    with pytest.raises(ValueError, match="no tiene filas"):
        ejecutar(historico, uc3m, pendientes)

    assert not pendientes.exists()


def test_ejecutar_con_catalogo_vacio_se_para(tmp_path):
    historico, uc3m = _bases(tmp_path, [("GEORGIA INSTITUTE OF TECHNOLOGY", "CS1332", "Data")])
    with closing(sqlite3.connect(uc3m)) as connection, connection:
        connection.execute("DELETE FROM dest_subjects")

    with pytest.raises(ValueError, match="dest_subjects no tiene"):
        ejecutar(historico, uc3m, tmp_path / "enlace_pendiente.md")
