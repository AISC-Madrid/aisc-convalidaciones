import sqlite3
from contextlib import closing

import pytest

from src.reconciliation.old_to_new import (
    MANUALES,
    AsignaturaVigente,
    CodigoAntiguo,
    Pendiente,
    Reconciliacion,
    cargar_estudios,
    indice_vigente,
    motivo_pendiente,
    nivel_2,
    reconciliar,
)


def _indice():
    return indice_vigente(
        [
            AsignaturaVigente("10", "Estadística", "ES"),
            AsignaturaVigente("11", "Estadística", "ES"),
            AsignaturaVigente("20", "Inferencia Estadística", "ES"),
        ],
        {"10": frozenset({"362"}), "11": frozenset({"350"}), "20": frozenset({"362"})},
    )


def test_manual_resuelve_lo_que_no_resuelven_los_niveles():
    antiguos = [CodigoAntiguo("99", ("Ampliación",)), CodigoAntiguo("98", ("Nada",))]

    filas = reconciliar(antiguos, _indice(), nivel_2, {"99": "20"})

    assert filas == (Reconciliacion("99", "20", "manual"), Reconciliacion("98", None, None))


def test_el_nivel_1_gana_al_manual():
    filas = reconciliar([CodigoAntiguo("10", ("Estadística",))], _indice(), nivel_2, {"10": "20"})

    assert filas == (Reconciliacion("10", "10", "code"),)


def test_manual_a_un_codigo_que_no_existe_se_para():
    with pytest.raises(ValueError, match="MANUALES"):
        reconciliar([CodigoAntiguo("99", ("X",))], _indice(), nivel_2, {"99": "55555"})


def test_manuales_del_piloto():
    assert MANUALES == {"18274": "20563", "18276": "20567"}


def test_sin_estudio_conocido_el_nombre_repetido_es_ambiguo():
    antiguo = CodigoAntiguo("99", ("Estadística",))

    assert nivel_2(antiguo, _indice()) is None
    assert motivo_pendiente(antiguo, _indice()).candidatos == ("10", "11")


def test_con_estudio_solo_cuenta_el_del_mismo_estudio():
    antiguo = CodigoAntiguo("99", ("Estadística",), frozenset({"362"}))

    assert nivel_2(antiguo, _indice()) == Reconciliacion("99", "10", "exact")


def test_candidatos_pendientes_solo_del_mismo_estudio():
    antiguo = CodigoAntiguo("99", ("Estadística",), frozenset({"999"}))

    assert motivo_pendiente(antiguo, _indice()) == Pendiente(
        "99", ("Estadística",), "sin_coincidencia", ()
    )


def test_cargar_estudios_por_curso_y_sin_tabla(tmp_path):
    base = tmp_path / "uc3m.sqlite"
    with closing(sqlite3.connect(base)) as connection, connection:
        connection.execute("CREATE TABLE otra (x)")
    assert cargar_estudios(base) == {}

    with closing(sqlite3.connect(base)) as connection, connection:
        connection.execute(
            "CREATE TABLE subject_plans "
            "(codigo TEXT, plan TEXT, estudio TEXT, curso_academico TEXT)"
        )
        connection.executemany(
            "INSERT INTO subject_plans VALUES (?, ?, ?, ?)",
            [
                ("18274", "433", "362", "2025/2026"),
                ("20563", "567", "362", "2026/2027"),
                ("20563", "999", "350", "2026/2027"),
            ],
        )

    assert cargar_estudios(base) == {
        "18274": frozenset({"362"}),
        "20563": frozenset({"362", "350"}),
    }
    assert cargar_estudios(base, "2026/2027") == {"20563": frozenset({"362", "350"})}
