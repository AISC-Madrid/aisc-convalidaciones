from types import SimpleNamespace

import pandas as pd

from src.loaders.historical_xls import (
    HISTORICAL_COLUMNS,
    deduplicate_historical_matches,
    normalize_code,
    normalize_historical,
    normalize_text,
    read_historical_xls,
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
        ("UNI", "A1"),
        ("UNI", "A2"),
        ("UNI", "C1"),
        ("OTRA UNI", "B1"),
    }
