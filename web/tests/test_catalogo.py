"""Tests del catálogo: búsqueda, filtro, duplicados y BD ausente.

No usan la BD real (no está en git): cada test crea un SQLite pequeño
con el mismo esquema en una carpeta temporal.
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import catalogo  # noqa: E402


@pytest.fixture
def ruta_bd(tmp_path):
    ruta = tmp_path / "prueba.sqlite"
    con = sqlite3.connect(ruta)
    con.executescript("""
        CREATE TABLE subjects (
            codigo TEXT, nombre TEXT, estudio TEXT, curso_academico TEXT,
            creditos REAL, objetivos TEXT, programa TEXT, idioma TEXT, url TEXT
        );
        CREATE TABLE subject_plans (
            codigo TEXT, plan TEXT, estudio TEXT, curso_academico TEXT
        );
        CREATE TABLE dest_subjects (
            id INTEGER PRIMARY KEY, universidad TEXT, codigo TEXT,
            codigo_norm TEXT, nombre TEXT, descripcion TEXT, ects REAL
        );
        INSERT INTO subjects VALUES
            ('19903', 'Biomecánica', '257', '2025/2026', 6,
             'obj', 'prog', 'ES', 'ficha-vieja'),
            ('19903', 'Biomechanics', '257', '2026/2027', 6,
             'obj', 'prog', 'EN', 'ficha-en'),
            ('19903', 'Biomecánica', '257', '2026/2027', 6,
             'obj', 'prog', 'ES', 'ficha-buena'),
            ('15526', 'Cálculo I', '257', '2026/2027', 6,
             'obj', 'prog', 'ES', 'ficha-calculo'),
            ('99999', 'De otro grado', '999', '2026/2027', 6,
             'obj', 'prog', 'ES', 'otra'),
            ('14528', 'Habilidades Profesionales', '999', '2026/2027', 6,
             'obj', 'prog', 'ES', 'ficha-compartida'),
            ('11111', 'Antigua de Biomédica', '257', '2023/2024', 6,
             'obj', 'prog', 'ES', 'ficha-antigua');
        INSERT INTO subject_plans VALUES
            ('19903', '522', '257', '2026/2027'),
            ('15526', '522', '257', '2026/2027'),
            ('14528', '522', '257', '2026/2027'),
            ('14528', '600', '999', '2026/2027'),
            ('99999', '600', '999', '2026/2027'),
            ('11111', '419', '257', '2023/2024');
        INSERT INTO dest_subjects (universidad, codigo, nombre, descripcion, ects)
        VALUES
            ('GATECH', 'BMED 2110',
             'Conservation Principles in Biomedical Engineering', 'desc', 6),
            ('OTRA', 'XXX 1000', 'De otra universidad', 'desc', 6);
    """)
    con.commit()
    con.close()
    return ruta


def test_solo_biomedica_del_curso_actual_y_gatech(ruta_bd):
    codigos = {a["codigo"] for a in catalogo.cargar_catalogo(ruta_bd)}
    assert codigos == {"19903", "15526", "14528", "BMED 2110"}


def test_incluye_asignaturas_compartidas_con_otro_grado(ruta_bd):
    cat = catalogo.cargar_catalogo(ruta_bd)
    compartida = [a for a in cat if a["codigo"] == "14528"]
    assert len(compartida) == 1
    assert compartida[0]["nombre"] == "Habilidades Profesionales"


def test_sin_duplicados_y_version_mas_reciente_en_espanol(ruta_bd):
    cat = catalogo.cargar_catalogo(ruta_bd)
    biomecanica = [a for a in cat if a["codigo"] == "19903"]
    assert len(biomecanica) == 1
    assert biomecanica[0]["nombre"] == "Biomecánica"
    assert biomecanica[0]["url"] == "ficha-buena"


def test_no_expone_temarios(ruta_bd):
    for a in catalogo.cargar_catalogo(ruta_bd):
        assert set(a) == {"universidad", "codigo", "nombre", "ects", "url"}


def test_buscar_por_nombre_sin_tildes_ni_mayusculas(ruta_bd):
    cat = catalogo.cargar_catalogo(ruta_bd)
    assert [a["codigo"] for a in catalogo.buscar(cat, "BIOMECANICA")] == ["19903"]


def test_buscar_por_codigo_sin_espacio(ruta_bd):
    cat = catalogo.cargar_catalogo(ruta_bd)
    resultado = catalogo.buscar(cat, "bmed2110")
    assert [a["codigo"] for a in resultado] == ["BMED 2110"]
    assert resultado[0]["url"] == "https://catalog.gatech.edu/search/?P=BMED%202110"


def test_filtro_por_universidad(ruta_bd):
    cat = catalogo.cargar_catalogo(ruta_bd)
    solo_gt = catalogo.buscar(cat, "", catalogo.GATECH)
    assert {a["codigo"] for a in solo_gt} == {"BMED 2110"}


def test_busqueda_sin_resultados(ruta_bd):
    cat = catalogo.cargar_catalogo(ruta_bd)
    assert catalogo.buscar(cat, "astrofisica") == []


def test_bd_ausente(tmp_path):
    ruta = tmp_path / "no_existe.sqlite"
    with pytest.raises(catalogo.BDNoDisponible):
        catalogo.cargar_catalogo(ruta)
    assert not ruta.exists()


def test_bd_sin_tablas(tmp_path):
    ruta = tmp_path / "vacia.sqlite"
    sqlite3.connect(ruta).close()
    with pytest.raises(catalogo.BDNoDisponible):
        catalogo.cargar_catalogo(ruta)