"""Tests del scraper del destino: parser del catálogo, tabla dest_subjects y descargas."""

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.scrapers import destination
from src.scrapers.destination import (
    cargar_config,
    crear_tabla,
    descargar,
    guardar,
    normalizar_codigo,
    parse_catalog,
    permitido_por_robots,
)

FIXTURE = Path(__file__).parent / "fixtures" / "gatech" / "sintetico.html"
CFG = {"university_code": "TEST"}


@pytest.fixture(scope="module")
def catalogo():
    """Parser con el YAML real de Georgia Tech sobre la página inventada."""
    html = FIXTURE.read_text(encoding="utf-8")
    asignaturas, fallos = parse_catalog(html, cargar_config("gatech"))
    return {a["codigo"]: a for a in asignaturas}, fallos


def asignatura(codigo, nombre="Asignatura inventada", ects=6.0):
    """Crea una asignatura de prueba (datos inventados)."""
    return {
        "codigo": codigo,
        "nombre": nombre,
        "descripcion": "Descripción inventada.",
        "ects": ects,
    }


@pytest.fixture
def con():
    """BD temporal en memoria con la tabla ya creada. Se borra al acabar cada test."""
    conexion = sqlite3.connect(":memory:")
    crear_tabla(conexion)
    yield conexion
    conexion.close()


# --- parse_catalog ---


def test_lee_una_asignatura_normal(catalogo):
    asignaturas, _ = catalogo
    a = asignaturas["TEST 1000"]
    assert a["nombre"] == "Introduction to Testing"
    assert a["descripcion"] == "An invented introduction to the field."
    assert a["departamento"] == "TEST"
    assert (a["creditos"], a["ects"]) == (1.0, 2.0)


def test_el_codigo_no_lleva_nbsp(catalogo):
    asignaturas, _ = catalogo
    assert all("\xa0" not in codigo for codigo in asignaturas)


def test_descripcion_con_enlace_se_queda_en_texto(catalogo):
    asignaturas, _ = catalogo
    assert "TEST 2110 and TEST 1300" in asignaturas["TEST 2110"]["descripcion"]
    assert asignaturas["TEST 2110"]["ects"] == 6.0


def test_creditos_variables_dejan_ects_vacio(catalogo):
    asignaturas, _ = catalogo
    a = asignaturas["TEST 2698"]
    assert (a["creditos"], a["creditos_max"], a["ects"]) == (1.0, 12.0, None)


def test_descarta_comodines_cero_creditos_y_nivel_8000(catalogo):
    asignaturas, _ = catalogo
    for codigo in ("TEST 1XXX", "TEST 2111", "TEST 8901"):
        assert codigo not in asignaturas


def test_conserva_posgrado_hasta_el_nivel_maximo(catalogo):
    asignaturas, _ = catalogo
    assert "TEST 6110" in asignaturas


def test_codigo_con_letra_y_sin_descripcion(catalogo):
    asignaturas, _ = catalogo
    assert asignaturas["TEST 4699R"]["descripcion"] is None


def test_titulo_ilegible_va_a_fallos(catalogo):
    asignaturas, fallos = catalogo
    assert fallos == ["Broken title without code"]
    assert set(asignaturas) == {"TEST 1000", "TEST 2110", "TEST 2698", "TEST 4699R", "TEST 6110"}


# --- dest_subjects ---


def test_normalizar_codigo():
    assert normalizar_codigo("BMED 2110") == "BMED2110"
    assert normalizar_codigo(" bmed\xa02110 ") == "BMED2110"


def test_guardar_inserta_las_asignaturas(con):
    guardar(con, [asignatura("BMED 1000"), asignatura("BMED 2110")], CFG)
    assert con.execute("SELECT COUNT(*) FROM dest_subjects").fetchone()[0] == 2


def test_guardar_rellena_codigo_norm(con):
    guardar(con, [asignatura("BMED 2110")], CFG)
    assert con.execute("SELECT codigo_norm FROM dest_subjects").fetchone()[0] == "BMED2110"


def test_guardar_dos_veces_no_duplica_ni_cambia_ids(con):
    datos = [asignatura("BMED 1000"), asignatura("BMED 2110")]
    guardar(con, datos, CFG)
    ids_antes = con.execute("SELECT id, codigo FROM dest_subjects ORDER BY codigo").fetchall()
    guardar(con, datos, CFG)
    ids_despues = con.execute("SELECT id, codigo FROM dest_subjects ORDER BY codigo").fetchall()
    assert ids_antes == ids_despues


def test_guardar_actualiza_si_la_asignatura_cambia(con):
    guardar(con, [asignatura("BMED 1000", nombre="Nombre viejo", ects=2.0)], CFG)
    guardar(con, [asignatura("BMED 1000", nombre="Nombre nuevo", ects=4.0)], CFG)
    fila = con.execute(
        "SELECT nombre, ects FROM dest_subjects WHERE codigo = 'BMED 1000'"
    ).fetchone()
    assert fila == ("Nombre nuevo", 4.0)


def test_mismo_codigo_en_dos_universidades_son_filas_distintas(con):
    guardar(con, [asignatura("MATH 1551")], {"university_code": "GATECH"})
    guardar(con, [asignatura("MATH 1551")], {"university_code": "PURDUE"})
    assert con.execute("SELECT COUNT(*) FROM dest_subjects").fetchone()[0] == 2


def test_ects_puede_quedar_vacio(con):
    guardar(con, [asignatura("BMED 2698", ects=None)], CFG)
    ects = con.execute("SELECT ects FROM dest_subjects").fetchone()[0]
    assert ects is None


def test_crear_tabla_no_toca_las_demas_tablas():
    conexion = sqlite3.connect(":memory:")
    conexion.execute("CREATE TABLE subjects (codigo TEXT)")
    conexion.execute("INSERT INTO subjects VALUES ('15363')")
    crear_tabla(conexion)
    crear_tabla(conexion)  # dos veces: tampoco debe fallar
    assert conexion.execute("SELECT COUNT(*) FROM subjects").fetchone()[0] == 1
    conexion.close()


def test_crear_tabla_anade_codigo_norm_a_una_tabla_antigua():
    conexion = sqlite3.connect(":memory:")
    conexion.execute(
        "CREATE TABLE dest_subjects (id INTEGER PRIMARY KEY, universidad TEXT NOT NULL, "
        "codigo TEXT NOT NULL, nombre TEXT NOT NULL, descripcion TEXT, ects REAL, "
        "UNIQUE (universidad, codigo))"
    )
    crear_tabla(conexion)
    guardar(conexion, [asignatura("BMED 2110")], CFG)
    assert conexion.execute("SELECT codigo_norm FROM dest_subjects").fetchone()[0] == "BMED2110"
    conexion.close()


# --- descargas ---


CFG_DESCARGA = {"user_agent": "test", "rate_limit_seconds": 0}


def test_descargar_usa_la_cache_sin_conectarse(tmp_path, monkeypatch):
    ruta = tmp_path / "bmed.html"
    ruta.write_text("<html>en caché</html>", encoding="utf-8")
    monkeypatch.setattr(destination.requests, "get", lambda *a, **k: pytest.fail("sin red"))
    assert descargar("https://ejemplo.edu/coursesaz/bmed/", ruta, CFG_DESCARGA) == (
        "<html>en caché</html>"
    )


def _falso_get(robots_txt: str, pedidas: list[str]):
    def get(url, **kwargs):
        pedidas.append(url)
        texto = robots_txt if url.endswith("/robots.txt") else "<html>pagina</html>"
        return SimpleNamespace(ok=True, text=texto, raise_for_status=lambda: None)

    return get


def test_descargar_guarda_en_cache_si_robots_lo_permite(tmp_path, monkeypatch):
    destination._robots.cache_clear()
    pedidas: list[str] = []
    monkeypatch.setattr(
        destination.requests, "get", _falso_get("User-agent: *\nDisallow: /search/", pedidas)
    )
    ruta = tmp_path / "sub" / "bmed.html"
    assert descargar("https://permitido.edu/coursesaz/bmed/", ruta, CFG_DESCARGA) == (
        "<html>pagina</html>"
    )
    assert ruta.read_text(encoding="utf-8") == "<html>pagina</html>"
    assert pedidas == ["https://permitido.edu/robots.txt", "https://permitido.edu/coursesaz/bmed/"]


def test_descargar_respeta_robots(tmp_path, monkeypatch):
    destination._robots.cache_clear()
    pedidas: list[str] = []
    monkeypatch.setattr(
        destination.requests, "get", _falso_get("User-agent: *\nDisallow: /coursesaz/", pedidas)
    )
    assert not permitido_por_robots("https://prohibido.edu/coursesaz/bmed/", "test")
    with pytest.raises(PermissionError):
        descargar("https://prohibido.edu/coursesaz/bmed/", tmp_path / "x.html", CFG_DESCARGA)
    assert not (tmp_path / "x.html").exists()
