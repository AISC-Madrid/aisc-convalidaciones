import sqlite3
from contextlib import closing

import pytest

from src.loaders.link_report import (
    FilaEnlace,
    asignaturas_uc3m,
    cargar_filas,
    es_calibrable,
    grados_con_umbral_propio,
    informe,
    muestra_enlaces,
    sin_reconciliar,
    tabla_calibracion,
    tasa,
    tasas_por_grado,
    texto_tasa,
)


def fila(**cambios) -> FilaEnlace:
    base = dict(
        id=1,
        grado="Grado en Ingeniería Biomédica",
        uc3m_codigo="15363",
        uc3m_nombre="Álgebra",
        destino_codigo="CS1332",
        destino_nombre="Data Structures",
        grupo=None,
        dest_subject_id=7,
        link_method="code",
        new_code="15363",
        reconciliation_method="code",
        catalogo_codigo="CS 1332",
        catalogo_nombre="Data Structures",
    )
    base.update(cambios)
    return FilaEnlace(**base)


def test_la_tasa_cuenta_unlinked_en_el_total():
    filas = (
        fila(id=1),
        fila(id=2, link_method="unlinked", dest_subject_id=None),
    )

    resultado = tasa(filas, "piloto")

    assert resultado.enlazadas == 1
    assert resultado.total == 2
    assert texto_tasa(resultado) == "1/2 (50.0%)"


def test_un_enlace_sin_id_de_catalogo_no_cuenta():
    assert not es_calibrable(fila(dest_subject_id=None))


def test_grados_con_distinta_grafia_se_juntan_y_el_umbral_mira_enlazadas():
    fisicas = [fila(id=i, grado="Ingeniería Física", uc3m_codigo=str(i)) for i in range(19)]
    fisicas.append(
        fila(
            id=19,
            grado="INGENIERIA FISICA",
            uc3m_codigo="19",
            link_method="unlinked",
            dest_subject_id=None,
        )
    )
    propias = [
        fila(id=100 + i, grado="Grado en Informática", uc3m_codigo=str(100 + i)) for i in range(20)
    ]

    por_grado = tasas_por_grado([*fisicas, *propias])

    assert [item.total for item in por_grado] == [20, 20]
    assert [item.enlazadas for item in por_grado] == [20, 19]
    assert grados_con_umbral_propio(por_grado) == 1


def test_la_tabla_solo_guarda_el_piloto_reconciliado_y_enlazado():
    filas = (
        fila(id=1, new_code="20000", uc3m_codigo="111"),
        fila(id=2, new_code="20000", uc3m_codigo="111", destino_codigo="MATH2551", grupo=4),
        fila(id=3, new_code=None, reconciliation_method=None, uc3m_codigo="999"),
        fila(id=4, link_method="unlinked", dest_subject_id=None),
        fila(id=5, grado="Grado en Ingeniería Informática", new_code="30000"),
    )

    pares = tabla_calibracion(filas)

    assert [par.dest_subject_id for par in pares] == [7, 7]
    assert asignaturas_uc3m(pares) == 1
    assert [par.uc3m_codigo for par in sin_reconciliar(filas)] == ["999"]
    assert pares[0].new_code == "20000"


def test_la_muestra_antepone_alias_y_nombre():
    filas = [fila(id=i, link_method="code") for i in range(1, 12)]
    filas.append(fila(id=20, link_method="alias", grado="Otro grado"))
    filas.append(fila(id=21, link_method="name"))

    muestra = muestra_enlaces(filas)

    assert [fila.link_method for fila in muestra[:2]] == ["alias", "name"]
    assert len(muestra) == 10
    assert muestra[0].id == 20


def test_el_informe_anota_las_tres_tasas_y_avisa_por_debajo_del_50():
    filas = (
        fila(
            id=1,
            link_method="unlinked",
            dest_subject_id=None,
            new_code=None,
            reconciliation_method=None,
        ),
        fila(id=2, grado="Grado en Informática"),
    )

    texto = informe(filas)

    assert "0/1 (0.0%)" in texto
    assert "1/2 (50.0%)" in texto
    assert "0 de 2" in texto
    assert "0 de 1 no enlazadas" in texto
    assert "corrige el enlace antes" in texto
    assert "Pares: 0" in texto


def _bases(tmp_path):
    historico, uc3m = tmp_path / "historico.sqlite", tmp_path / "uc3m.sqlite"
    with closing(sqlite3.connect(uc3m)) as connection, connection:
        connection.execute(
            "CREATE TABLE old_to_new (old_code TEXT PRIMARY KEY, new_code TEXT, method TEXT)"
        )
        connection.execute("INSERT INTO old_to_new VALUES ('15363', '15363', 'code')")
        connection.execute(
            "CREATE TABLE dest_subjects (id INTEGER PRIMARY KEY, codigo TEXT, nombre TEXT)"
        )
        connection.execute("INSERT INTO dest_subjects VALUES (7, 'CS 1332', 'Data Structures')")
    with closing(sqlite3.connect(historico)) as connection, connection:
        connection.execute(
            """
            CREATE TABLE historical_matches (
                id INTEGER PRIMARY KEY,
                grado TEXT,
                uc3m_codigo TEXT,
                uc3m_nombre TEXT,
                destino_codigo TEXT,
                destino_nombre TEXT,
                grupo INTEGER,
                dest_subject_id INTEGER,
                link_method TEXT
            )
            """
        )
        connection.executemany(
            "INSERT INTO historical_matches VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    1,
                    "Grado en Ingeniería Biomédica",
                    "15363",
                    "Álgebra",
                    "CS1332",
                    "Data",
                    None,
                    7,
                    "code",
                ),
                (2, "University of California", "1", "Otra", "CS1332", "Data", None, None, None),
            ],
        )
    return historico, uc3m


def test_cargar_filas_junta_reconciliacion_y_catalogo_e_ignora_otras_universidades(tmp_path):
    historico, uc3m = _bases(tmp_path)

    filas = cargar_filas(historico, uc3m)

    assert len(filas) == 1
    assert filas[0].new_code == "15363"
    assert filas[0].catalogo_codigo == "CS 1332"
    assert es_calibrable(filas[0])


def test_cargar_filas_sin_columnas_de_enlace_explica_el_paso_que_falta(tmp_path):
    historico = tmp_path / "historico.sqlite"
    with closing(sqlite3.connect(historico)) as connection, connection:
        connection.execute("CREATE TABLE historical_matches (id INTEGER PRIMARY KEY, grado TEXT)")
    with closing(sqlite3.connect(tmp_path / "uc3m.sqlite")) as connection, connection:
        connection.execute("CREATE TABLE old_to_new (old_code TEXT)")
        connection.execute("CREATE TABLE dest_subjects (id INTEGER)")

    with pytest.raises(ValueError, match="link_catalog"):
        cargar_filas(historico, tmp_path / "uc3m.sqlite")
