import json
import sqlite3

from src.embeddings.generar_corpus_uc3m import calcular_estadisticas, generar_corpus


def _crear_bd(ruta):
    with sqlite3.connect(ruta) as conexion:
        conexion.executescript(
            """
            CREATE TABLE subjects (
                codigo TEXT NOT NULL,
                nombre TEXT,
                plan TEXT,
                estudio TEXT,
                curso_academico TEXT NOT NULL,
                objetivos TEXT,
                programa TEXT,
                idioma TEXT NOT NULL,
                tipo TEXT,
                url TEXT
            );
            CREATE TABLE subject_plans (
                codigo TEXT NOT NULL,
                plan TEXT NOT NULL,
                estudio TEXT,
                curso_academico TEXT NOT NULL
            );
            """
        )
        conexion.executemany(
            """
            INSERT INTO subjects
                (
                    codigo, nombre, plan, estudio, curso_academico,
                    objetivos, programa, idioma, tipo, url
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "10001",
                    "Linear Algebra",
                    "522",
                    "257",
                    "2026/2027",
                    "Understand vector spaces.",
                    "Matrices and transformations.",
                    "EN",
                    "FB",
                    "https://example.test/10001",
                ),
                (
                    "10002",
                    "Files and Databases",
                    "522",
                    "257",
                    "2026/2027",
                    None,
                    "Data models and database systems.",
                    "EN",
                    "OB",
                    "https://example.test/10002",
                ),
                (
                    "10004",
                    "Subject with objectives only",
                    "419",
                    "257",
                    "2026/2027",
                    "Understand the topic.",
                    None,
                    "EN",
                    "OP",
                    "https://example.test/10004",
                ),
                (
                    "10001",
                    "Álgebra Lineal",
                    "456",
                    "371",
                    "2026/2027",
                    "Objetivos",
                    "Programa",
                    "ES",
                    "FB",
                    None,
                ),
                (
                    "10003", "Other subject", "456", "257", "2025/2026",
                    "Other", "Other", "EN", "OP", None
                ),
                (
                    "10005", "Wrong degree", "419", "371", "2026/2027",
                    "Other degree", "Other degree", "EN", "OP", None
                ),
            ],
        )
        conexion.executemany(
            "INSERT INTO subject_plans VALUES (?, ?, ?, ?)",
            [
                ("10001", "522", "257", "2026/2027"),
                ("10002", "522", "257", "2026/2027"),
                ("10001", "419", "257", "2026/2027"),
                ("10004", "419", "257", "2026/2027"),
                ("10003", "522", "257", "2025/2026"),
                ("10002", "419", "371", "2026/2027"),
                ("10005", "419", "371", "2026/2027"),
            ],
        )


def test_genera_corpus_filtrando_estudio_planes_curso_idioma_y_sin_duplicados(tmp_path):
    database_path = tmp_path / "uc3m.sqlite"
    output_path = tmp_path / "corpus_uc3m.jsonl"
    _crear_bd(database_path)

    ruta, estadisticas = generar_corpus(database_path, output_path)
    registros = [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]

    assert [registro["codigo"] for registro in registros] == ["10001", "10002", "10004"]
    assert len({registro["codigo"] for registro in registros}) == len(registros)
    assert {registro["plan"] for registro in registros} == {"522", "419"}
    assert registros[1]["texto"] == (
        "query: Files and Databases. Data models and database systems."
    )
    assert registros[1]["objetivos_vacios"] is True
    assert registros[2]["programa_vacio"] is True
    assert registros[2]["objetivos_vacios"] is False
    assert estadisticas["asignaturas"] == 3
    assert estadisticas["objetivos_vacios"] == 1
    assert estadisticas["programas_vacios"] == 1
    assert estadisticas["ambos_vacios"] == 0
    assert all(registro["curso_academico"] == "2026/2027" for registro in registros)


def test_calcula_estadisticas_de_longitud():
    filas = [
        {
            "nombre": "A",
            "objetivos": "one two",
            "programa": "three four five",
            "texto": "query: A. one two. three four five",
        },
        {
            "nombre": "B",
            "objetivos": None,
            "programa": None,
            "texto": "query: B.",
        },
    ]

    estadisticas = calcular_estadisticas(filas)

    assert estadisticas["objetivos_vacios"] == 1
    assert estadisticas["programas_vacios"] == 1
    assert estadisticas["ambos_vacios"] == 1
    assert estadisticas["programa_mediana"] == 1.5
    assert estadisticas["texto_min"] == 0
    assert estadisticas["texto_max"] == 5
