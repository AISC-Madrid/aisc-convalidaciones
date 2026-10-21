import sqlite3
from contextlib import closing
from types import SimpleNamespace

import pandas as pd

from src.loaders.historical_xls import (
    HISTORICAL_COLUMNS,
    assign_groups,
    deduplicate_historical_matches,
    normalize_code,
    normalize_historical,
    normalize_text,
    read_historical_xls,
    save_historical,
    validate_historical_rows,
)


def test_lee_las_hojas_de_datos_de_un_xls_temporal(monkeypatch, tmp_path):
    # Los XLS de data/raw no se suben; simulamos su lectura para CI/GitHub Actions.
    xls_path = tmp_path / "historical.xls"
    xls_path.touch()
    rows = [
        ["España", "Uni", "Grado", "123", "Álgebra", 6, 1, "OB", "A1", "Algebra"],
    ]
    sheets = {
        "INFORMACIÓN IMPORTANTE": pd.DataFrame(),
        "2024-2025": pd.DataFrame(rows, columns=["columna"] * 10),
        "2025-2026": pd.DataFrame(rows, columns=["columna"] * 10),
    }

    monkeypatch.setattr(
        pd,
        "ExcelFile",
        lambda path, engine: SimpleNamespace(sheet_names=list(sheets)),
    )
    monkeypatch.setattr(
        pd,
        "read_excel",
        lambda path, sheet_name, engine, dtype: sheets[sheet_name].copy(),
    )

    historical = read_historical_xls(xls_path)

    normalized_columns = [f"{column}_norm" for column in [
        "country",
        "university",
        "degree",
        "uc_code",
        "uc_subject",
        "dest_code",
        "dest_subject",
    ]]
    assert list(historical.columns) == [
        *HISTORICAL_COLUMNS,
        "academic_year",
        *normalized_columns,
    ]
    assert set(historical["academic_year"]) == {"2024-2025", "2025-2026"}
    assert len(historical) == 2
    assert historical["uc_code"].tolist() == ["123", "123"]


def test_normaliza_texto_y_valores_vacios():
    assert normalize_text("  Ingeniería\xa0de   Datos  ") == "INGENIERIA DE DATOS"
    assert normalize_text(None) == ""
    assert normalize_text(float("nan")) == ""


def test_normaliza_codigos_sin_espacios_ni_tildes():
    assert normalize_code(" cs 13 32 ") == "CS1332"
    assert normalize_code(" áb 12 ") == "AB12"
    assert normalize_code(None) == ""


def test_aplica_normalizacion_a_las_columnas_del_dataframe():
    frame = pd.DataFrame(
        {
            "country": [" España "],
            "university": ["  Université  "],
            "degree": [" Ingeniería   Informática"],
            "uc_code": [" 13 884 "],
            "uc_subject": ["  Álgebra  Lineal "],
            "ects": [6],
            "course": [1],
            "subject_type": [" Obligatoria "],
            "dest_code": [None],
            "dest_subject": ["  Linear   Algebra "],
            "academic_year": ["2024-2025"],
        }
    )

    normalized = normalize_historical(frame)

    assert normalized.loc[0, "degree_norm"] == "INGENIERIA INFORMATICA"
    assert normalized.loc[0, "uc_code_norm"] == "13884"
    assert normalized.loc[0, "dest_code_norm"] == ""
    assert normalized.loc[0, "dest_subject_norm"] == "LINEAR ALGEBRA"


def test_valida_una_fila_inventada_y_la_convierte_al_modelo():
    frame = pd.DataFrame(
        {
            "country": [" España "],
            "university": [" Universidad de Prueba "],
            "degree": [" Ingeniería Informática "],
            "uc_code": [" 13 884 "],
            "uc_subject": [" Álgebra Lineal "],
            "ects": [6],
            "course": [1],
            "subject_type": [" Obligatoria "],
            "dest_code": [" CS 1332 "],
            "dest_subject": [" Data Structures "],
            "academic_year": ["2025-2026"],
        }
    )

    result = validate_historical_rows(frame)

    assert result.invalid_count == 0
    assert len(result.valid_rows) == 1
    assert result.valid_rows[0].uc3m_codigo == "13884"
    assert result.valid_rows[0].destino_codigo == "CS1332"
    assert result.valid_rows[0].ects == 6


def test_informa_de_todas_las_filas_invalidas_y_sus_motivos():
    frame = pd.DataFrame(
        {
            "country": ["España", "España"],
            "university": ["Uni", "Uni"],
            "degree": ["Grado", "Grado"],
            "uc_code": ["123", None],
            "uc_subject": ["Asignatura válida", "Asignatura sin código"],
            "ects": [0, 6],
            "course": [1, 1],
            "subject_type": ["OB", "OB"],
            "dest_code": ["A1", "A2"],
            "dest_subject": ["Destino 1", "Destino 2"],
            "academic_year": ["2025", "2025-2026"],
        }
    )

    result = validate_historical_rows(frame)

    assert len(result.valid_rows) == 0
    assert result.invalid_count == 2
    assert [row.index for row in result.invalid_rows] == [0, 1]
    assert any("curso_academico" in message for message in result.invalid_rows[0].errors)
    assert any("ects" in message for message in result.invalid_rows[0].errors)
    assert any("uc3m_codigo" in message for message in result.invalid_rows[1].errors)


def _validated_records(rows: list[dict]) -> tuple:
    return validate_historical_rows(pd.DataFrame(rows)).valid_rows


def test_deduplica_la_misma_equivalencia_entre_cursos_y_conserva_la_mas_reciente():
    records = _validated_records(
        [
            {
                "country": "España",
                "university": "Uni",
                "degree": "Grado",
                "uc_code": "123",
                "uc_subject": "Álgebra",
                "ects": 6,
                "course": 1,
                "subject_type": "OB",
                "dest_code": "A1",
                "dest_subject": "Algebra",
                "academic_year": "2025-2026",
            },
            {
                "country": "España",
                "university": "Uni",
                "degree": "Grado",
                "uc_code": "123",
                "uc_subject": "Algebra",
                "ects": 6,
                "course": 1,
                "subject_type": "OB",
                "dest_code": "A1",
                "dest_subject": "Algebra",
                "academic_year": "2024-2025",
            },
        ]
    )

    result = deduplicate_historical_matches(records)

    assert result.duplicates_removed == 1
    assert len(result.records) == 1
    assert result.records[0].curso_academico == "2025-2026"


def test_conserva_equivalencias_distintas_y_relaciones_n_m():
    records = _validated_records(
        [
            {
                "country": "España",
                "university": "Uni",
                "degree": "Grado",
                "uc_code": "123",
                "uc_subject": "Álgebra",
                "ects": 6,
                "course": 1,
                "subject_type": "OB",
                "dest_code": "A1",
                "dest_subject": "Algebra I",
                "academic_year": "2025-2026",
            },
            {
                "country": "España",
                "university": "Uni",
                "degree": "Grado",
                "uc_code": "123",
                "uc_subject": "Álgebra",
                "ects": 6,
                "course": 1,
                "subject_type": "OB",
                "dest_code": "A2",
                "dest_subject": "Algebra II",
                "academic_year": "2025-2026",
            },
        ]
    )

    result = deduplicate_historical_matches(records)

    assert result.duplicates_removed == 0
    assert len(result.records) == 2
    assert {record.destino_codigo for record in result.records} == {"A1", "A2"}


def test_pipeline_de_tres_ficheros_deduplica_sin_perder_n_m():
    base = {
        "country": "España",
        "university": "Uni",
        "degree": "Grado",
        "uc_code": "123",
        "uc_subject": "Álgebra",
        "ects": 6,
        "course": 1,
        "subject_type": "OB",
    }
    frames = [
        pd.DataFrame(
            [
                {
                    **base,
                    "dest_code": "A1",
                    "dest_subject": "Algebra I",
                    "academic_year": "2024-2025",
                },
                {
                    **base,
                    "dest_code": "A2",
                    "dest_subject": "Algebra II",
                    "academic_year": "2024-2025",
                },
            ]
        ),
        pd.DataFrame(
            [
                {
                    **base,
                    "dest_code": "A1",
                    "dest_subject": "Algebra I",
                    "academic_year": "2025-2026",
                },
                {
                    **base,
                    "uc_code": "456",
                    "uc_subject": "Cálculo",
                    "dest_code": "C1",
                    "dest_subject": "Calculus",
                    "academic_year": "2025-2026",
                },
            ]
        ),
        pd.DataFrame(
            [
                {
                    **base,
                    "university": "Otra Uni",
                    "dest_code": "B1",
                    "dest_subject": "Algebra I",
                    "academic_year": "2026-2027",
                }
            ]
        ),
    ]

    validations = [validate_historical_rows(frame) for frame in frames]
    records = [record for result in validations for record in result.valid_rows]
    deduplicated = deduplicate_historical_matches(records)

    assert [len(result.valid_rows) for result in validations] == [2, 2, 1]
    assert all(result.invalid_count == 0 for result in validations)
    assert deduplicated.duplicates_removed == 1
    assert len(deduplicated.records) == 4
    assert {(record.universidad, record.destino_codigo) for record in deduplicated.records} == {
        ("Uni", "A1"),
        ("Uni", "A2"),
        ("Uni", "C1"),
        ("Otra Uni", "B1"),
    }


def _fila(uc, dest, year, uc_subject=None, uni="Univ. de Zürich"):
    return {
        "country": "Suiza",
        "university": uni,
        "degree": "Informática",
        "uc_code": uc,
        "uc_subject": uc_subject or f"Asignatura {uc}",
        "ects": 6,
        "course": 1,
        "subject_type": "OB",
        "dest_code": dest,
        "dest_subject": f"Subject {dest}",
        "academic_year": year,
    }


def _pipeline(rows):
    records = assign_groups(_validated_records(rows))
    return deduplicate_historical_matches(records)


def test_n_m_del_mismo_curso_comparte_grupo():
    result = _pipeline([_fila("1", "A1", "2025-2026"), _fila("1", "A2", "2025-2026")])

    assert [r.grupo for r in result.records] == [1, 1]


def test_alternativas_de_cursos_distintos_no_forman_grupo():
    result = _pipeline([_fila("1", "A1", "2024-2025"), _fila("1", "A2", "2025-2026")])

    assert [r.grupo for r in result.records] == [None, None]


def test_n_m_inversa_varias_uc3m_un_destino():
    result = _pipeline([_fila("1", "A1", "2025-2026"), _fila("2", "A1", "2025-2026")])

    assert [r.grupo for r in result.records] == [1, 1]


def test_no_encadena_una_uc3m_con_varias_destino_y_la_inversa():
    # Fisiología I se convalida con teoría y laboratorio. Fisiología II solo
    # comparte el laboratorio: es otra convalidación y no entra en el grupo.
    result = _pipeline(
        [
            _fila("1", "TEO", "2025-2026", uc_subject="Fisiología I"),
            _fila("1", "LAB", "2025-2026", uc_subject="Fisiología I"),
            _fila("2", "LAB", "2025-2026", uc_subject="Fisiología II"),
        ]
    )

    grupos = {(r.uc3m_nombre, r.destino_codigo): r.grupo for r in result.records}
    assert grupos[("Fisiología I", "TEO")] == grupos[("Fisiología I", "LAB")]
    assert grupos[("Fisiología I", "TEO")] is not None
    assert grupos[("Fisiología II", "LAB")] is None


def test_grupo_que_queda_con_una_fila_tras_deduplicar_deja_de_serlo():
    # A1 se repite en 2025-2026 sin n:m: gana esa fila y A2 se queda sola.
    result = _pipeline(
        [
            _fila("1", "A1", "2024-2025"),
            _fila("1", "A2", "2024-2025"),
            _fila("1", "A1", "2025-2026"),
        ]
    )

    assert result.duplicates_removed == 1
    assert [r.grupo for r in result.records] == [None, None]


def test_diez_filas_con_una_duplicada_y_una_n_m_conservan_nombres_originales():
    rows = [_fila(str(n), f"D{n}", "2025-2026", uc_subject=f"Álgebra {n}") for n in range(1, 7)]
    rows += [
        _fila("7", "D7", "2025-2026"),  # n:m: UC3M 7 -> D7 y D8
        _fila("7", "D8", "2025-2026"),
        _fila("1", "D1", "2024-2025", uc_subject="Álgebra 1"),  # duplicada de otro curso
        _fila("9", "D9", "2024-2025"),
    ]

    result = _pipeline(rows)

    assert len(rows) == 10
    assert result.duplicates_removed == 1
    assert len(result.records) == 9
    assert {r.uc3m_codigo for r in result.records if r.grupo} == {"7"}
    assert sum(r.grupo is not None for r in result.records) == 2
    assert result.records[0].uc3m_nombre == "Álgebra 1"
    assert result.records[0].universidad == "Univ. de Zürich"


def test_guarda_historical_matches_en_sqlite_y_se_puede_relanzar(tmp_path):
    result = _pipeline([_fila("1", "A1", "2025-2026"), _fila("1", "A2", "2025-2026"),
                        _fila("2", "B1", "2025-2026")])  # fmt: skip
    path = tmp_path / "processed" / "historico.sqlite"

    save_historical(result.records, path)
    save_historical(result.records, path)

    with closing(sqlite3.connect(path)) as connection:
        rows = connection.execute(
            "SELECT uc3m_codigo, destino_codigo, grupo FROM historical_matches ORDER BY id"
        ).fetchall()
    assert rows == [("1", "A1", 1), ("1", "A2", 1), ("2", "B1", None)]
