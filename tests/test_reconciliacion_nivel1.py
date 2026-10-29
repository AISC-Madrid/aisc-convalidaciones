import sqlite3
from contextlib import closing

import pytest

from src.reconciliation.old_to_new import (
    AsignaturaVigente,
    CodigoAntiguo,
    Reconciliacion,
    cargar_plan_vigente,
    ejecutar,
    guardar_reconciliacion,
    indice_vigente,
    main,
    nivel_1,
    nivel_2,
    reconciliar,
    resumen,
)


def test_el_nivel_1_manda_aunque_el_nombre_sea_distinto():
    indice = indice_vigente([AsignaturaVigente("15363", "Robótica blanda", "ES")])
    llamadas: list[str] = []

    def doble(antiguo: CodigoAntiguo, indice_recibido: object) -> Reconciliacion:
        llamadas.append(antiguo.old_code)
        return Reconciliacion(antiguo.old_code, "otro", "exact")

    resultado = reconciliar([CodigoAntiguo("15363", ("Soft Robotics",))], indice, doble)

    assert resultado == (Reconciliacion("15363", "15363", "code"),)
    assert llamadas == []
    assert nivel_1("15363", indice) == "15363"


def test_deduplica_el_codigo_vigente_por_idioma_y_grado():
    indice = indice_vigente(
        [
            AsignaturaVigente("15363", "Álgebra Lineal", "ES"),
            AsignaturaVigente("15363", "Linear Algebra", "EN"),
            AsignaturaVigente("15363", "Álgebra Lineal", "ES"),
        ]
    )

    assert indice.codigos == frozenset({"15363"})
    assert indice.por_nombre == {"ALGEBRA LINEAL": frozenset({"15363"})}
    assert "LINEAR ALGEBRA" not in indice.por_nombre


def test_un_codigo_solo_en_ingles_sigue_contando_en_el_nivel_1():
    indice = indice_vigente([AsignaturaVigente("15363", "Soft robotics", "EN")])

    assert nivel_1("15363", indice) == "15363"
    assert indice.por_nombre == {}


def test_un_nombre_espanol_vacio_no_entra_en_el_indice():
    indice = indice_vigente(
        [
            AsignaturaVigente("1", "   ", "ES"),
            AsignaturaVigente("1", "Cálculo", "ES"),
        ]
    )

    assert indice.codigos == frozenset({"1"})
    assert set(indice.por_nombre) == {"CALCULO"}


def test_ignora_cursos_que_no_son_el_vigente(tmp_path):
    database_path = tmp_path / "uc3m.sqlite"
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(
            """
            CREATE TABLE subjects (
                codigo TEXT, nombre TEXT, idioma TEXT, curso_academico TEXT
            )
            """
        )
        connection.execute("CREATE TABLE subject_plans (codigo TEXT, plan TEXT)")
        connection.executemany(
            "INSERT INTO subjects VALUES (?, ?, ?, ?)",
            [
                ("11111", "Álgebra", "ES", "2026/2027"),
                ("11111", "Linear Algebra", "EN", "2026/2027"),
                ("22222", "Vieja", "ES", "2025/2026"),
                ("33333", "Guion", "ES", "2024-2025"),
            ],
        )
        connection.execute("INSERT INTO subject_plans VALUES ('11111', '456')")
        connection.execute("INSERT INTO subject_plans VALUES ('11111', '789')")

    asignaturas = cargar_plan_vigente(database_path)
    indice = indice_vigente(asignaturas)

    assert [asignatura.codigo for asignatura in asignaturas] == ["11111", "11111"]
    assert indice.codigos == frozenset({"11111"})
    assert "22222" not in indice.codigos
    assert "33333" not in indice.codigos
    assert "LINEAR ALGEBRA" not in indice.por_nombre


def test_dos_registros_del_mismo_codigo_producen_una_fila():
    indice = indice_vigente([AsignaturaVigente("1", "Algo", "ES")])
    resultado = reconciliar(
        [
            CodigoAntiguo("1", ("Algo",)),
            CodigoAntiguo("1", ("Otro nombre",)),
            CodigoAntiguo("2", ("Nada",)),
        ],
        indice,
        lambda antiguo, indice_recibido: None,
    )

    assert [fila.old_code for fila in resultado] == ["1", "2"]
    assert resultado[0] == Reconciliacion("1", "1", "code")
    assert resultado[1] == Reconciliacion("2", None, None)


def test_solo_acepta_exact_con_codigo_nuevo():
    indice = indice_vigente([])

    def doble(antiguo: CodigoAntiguo, indice_recibido: object) -> Reconciliacion | None:
        if antiguo.old_code == "1":
            return Reconciliacion("1", "10", "exact")
        if antiguo.old_code == "2":
            return Reconciliacion("2", "10", "embedding")
        return Reconciliacion("3", None, "exact")

    resultado = reconciliar(
        [CodigoAntiguo(codigo, ("Nombre",)) for codigo in ("1", "2", "3")],
        indice,
        doble,
    )

    assert resultado == (
        Reconciliacion("1", "10", "exact"),
        Reconciliacion("2", None, None),
        Reconciliacion("3", None, None),
    )


def test_la_cascada_delega_el_nombre_en_nivel_2():
    indice = indice_vigente([AsignaturaVigente("10", "Cálculo", "ES")])
    resultado = reconciliar([CodigoAntiguo("99", ("Cálculo",))], indice, nivel_2)

    assert resultado == (Reconciliacion("99", "10", "exact"),)


def test_guardar_es_idempotente_y_no_toca_otras_tablas(tmp_path):
    database_path = tmp_path / "uc3m.sqlite"
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute("CREATE TABLE subjects (codigo TEXT, nombre TEXT)")
        connection.execute("INSERT INTO subjects VALUES ('sentinel', 'no tocar')")

    filas = (
        Reconciliacion("1", "1", "code"),
        Reconciliacion("2", None, None),
    )
    guardar_reconciliacion(filas, database_path)
    guardar_reconciliacion(filas, database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        guardadas = connection.execute(
            "SELECT old_code, new_code, method FROM old_to_new ORDER BY old_code"
        ).fetchall()
        sentinel = connection.execute("SELECT nombre FROM subjects").fetchone()
        tablas = {
            fila[0]
            for fila in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }

    assert guardadas == [("1", "1", "code"), ("2", None, None)]
    assert sentinel == ("no tocar",)
    assert "subjects" in tablas


def test_rechaza_method_pendiente(tmp_path):
    with pytest.raises(sqlite3.IntegrityError):
        guardar_reconciliacion([Reconciliacion("1", "1", "pendiente")], tmp_path / "uc3m.sqlite")


def test_ejecutar_enlaza_las_dos_bases_sin_borrar_el_resto(tmp_path):
    historico = tmp_path / "historico.sqlite"
    uc3m = tmp_path / "uc3m.sqlite"
    pendientes = tmp_path / "pendientes.md"
    with closing(sqlite3.connect(historico)) as connection, connection:
        connection.execute(
            "CREATE TABLE historical_matches (uc3m_codigo TEXT, uc3m_nombre TEXT)"
        )
        connection.executemany(
            "INSERT INTO historical_matches VALUES (?, ?)",
            [
                ("15363", "Soft Robotics"),
                ("99999", "cálculo"),
                ("88888", "Estadística"),
                ("77777", "Nada de nada"),
            ],
        )
    with closing(sqlite3.connect(uc3m)) as connection, connection:
        connection.execute(
            """
            CREATE TABLE subjects (
                codigo TEXT, nombre TEXT, idioma TEXT, curso_academico TEXT
            )
            """
        )
        connection.execute("CREATE TABLE descargas (estado TEXT)")
        connection.execute("INSERT INTO descargas VALUES ('centinela')")
        connection.executemany(
            "INSERT INTO subjects VALUES (?, ?, ?, ?)",
            [
                ("15363", "Robótica blanda", "ES", "2026/2027"),
                ("10", "Cálculo", "ES", "2026/2027"),
                ("11", "Estadística", "ES", "2026/2027"),
                ("12", "Estadística", "ES", "2026/2027"),
                ("77", "Antigua", "ES", "2025/2026"),
            ],
        )

    ejecutar(historico, uc3m, pendientes)
    filas = ejecutar(historico, uc3m, pendientes)
    texto = pendientes.read_text(encoding="utf-8")

    with closing(sqlite3.connect(uc3m)) as connection:
        guardadas = connection.execute("SELECT COUNT(*) FROM old_to_new").fetchone()[0]
        centinela = connection.execute("SELECT estado FROM descargas").fetchone()[0]
        subjects = connection.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]

    assert resumen(filas) == "1 con method=code, 1 con exact, 2 con NULL"
    assert guardadas == 4
    assert centinela == "centinela"
    assert subjects == 5
    assert "88888" in texto
    assert "77777" in texto
    assert "15363" not in texto


def test_main_imprime_el_resumen_calculado(monkeypatch, capsys):
    monkeypatch.setattr(
        "src.reconciliation.old_to_new.ejecutar",
        lambda: (
            Reconciliacion("1", "1", "code"),
            Reconciliacion("2", None, None),
        ),
    )

    main()

    assert capsys.readouterr().out.strip() == "1 con method=code, 0 con exact, 1 con NULL"
