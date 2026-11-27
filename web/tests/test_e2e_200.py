"""Test end-to-end de la pantalla de resultados con los 200 resultados inventados (#41).

Recorre lo mismo que hará un alumno en el servidor: cargar, filtrar, seleccionar un grupo
n:m y descargar el PDF. Los resultados son los que ``scripts/generar_ejemplo_200.py`` guarda
en la BD, pasados por el mismo camino que en producción: SQLite → filas → web. Solo la
conexión a la MySQL se sustituye (fixture ``publicar``).
"""

import importlib.util
import sqlite3

import pytest
from conftest import RAIZ, WEB_DIR
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

from src.export import resultados_bd

GRADO = "Grado en Ingeniería Biomédica"
UNIVERSIDAD = "Georgia Institute of Technology"


def _generador():
    ruta = RAIZ / "scripts" / "generar_ejemplo_200.py"
    spec = importlib.util.spec_from_file_location("generar_ejemplo_200", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def datos(tmp_path, publicar):
    """Genera los 200 resultados, los guarda en un SQLite y los publica tal como se leen."""
    ruta = tmp_path / "resultados.sqlite"
    _generador().main(["--salida", str(ruta)])
    with sqlite3.connect(ruta) as conexion:
        leidos = resultados_bd.leer(conexion, GRADO, UNIVERSIDAD).model_dump(mode="json")
    publicar(leidos)
    return leidos


def _app(tmp_path, monkeypatch):
    """Arranca la web real, guardando en tmp_path el PDF que genere para poder abrirlo.

    El espía se pone con monkeypatch (el módulo pdf es el mismo que usa la app), así que se
    quita solo al acabar el test y no se apila en cada rerun.
    """
    import pdf

    salida = tmp_path / "propuesta.pdf"
    original = pdf.generar_pdf

    def espia(*args, **kwargs):
        contenido = original(*args, **kwargs)
        salida.write_bytes(contenido)
        return contenido

    monkeypatch.setattr(pdf, "generar_pdf", espia)
    at = AppTest.from_file(str(WEB_DIR / "app.py"), default_timeout=20).run()
    return at, salida


def _boton_pdf(at):
    return next(b for b in at.get("download_button") if b.label == "Descargar propuesta PDF")


def test_cabecera_muestra_fecha_y_umbral(tmp_path, monkeypatch, datos):
    at, _ = _app(tmp_path, monkeypatch)

    assert not at.exception
    cabecera = " ".join(caption.value for caption in at.caption)
    assert "Generado el 25/11/2026" in cabecera
    assert "Umbral de similitud: 0,71" in cabecera


def test_200_resultados_se_paginan(tmp_path, monkeypatch, datos):
    filas = datos["resultados"]
    grupos = {f["grupo"] for f in filas if f["grupo"] is not None}
    en_grupo = sum(f["grupo"] is not None for f in filas)
    bloques = len(filas) - en_grupo + len(grupos)

    at, _ = _app(tmp_path, monkeypatch)

    assert len(filas) == 200
    assert len(at.dataframe[0].value) == 20
    assert any(f"de {bloques}" in caption.value for caption in at.caption)


def test_cargar_filtrar_seleccionar_grupo_y_sacar_pdf(tmp_path, monkeypatch, datos):
    # El grupo 1 tiene los nombres más largos: es el caso difícil para el PDF.
    grupo = [f for f in datos["resultados"] if f["grupo"] == 1]
    codigos_origen = {f["origen"]["codigo"] for f in grupo}
    codigos_destino = {f["destino"]["codigo"] for f in grupo}
    buscar = sorted(codigos_destino)[0]

    at, salida = _app(tmp_path, monkeypatch)

    # Filtrar: solo precedentes y búsqueda por un código de destino del grupo.
    next(s for s in at.selectbox if s.label == "Tipo de resultado").set_value(
        "Precedentes aprobados"
    ).run()
    next(t for t in at.text_input if t.label.startswith("Buscar")).set_value(buscar).run()
    propuesta = next(c for c in at.checkbox if buscar in c.label)
    # El grupo sale como una sola propuesta con todas sus asignaturas.
    assert all(codigo in propuesta.label for codigo in codigos_origen | codigos_destino)

    # Seleccionar el grupo entero y poner el nombre.
    propuesta.check().run()
    next(t for t in at.text_input if t.label == "Nombre del alumno").set_value(
        # nombre largo, con tilde y guion, para probar el PDF
        "María de los Ángeles Fernández-Villaverde Rodríguez"
    ).run()

    assert not at.exception
    ects_origen = sum({f["origen"]["codigo"]: f["origen"]["ects"] for f in grupo}.values())
    assert float(at.metric[0].value) == ects_origen
    assert not _boton_pdf(at).disabled

    # El PDF sale, es un PDF de verdad y trae todo el grupo.
    contenido = salida.read_bytes()
    assert contenido.startswith(b"%PDF")
    texto = " ".join(pagina.extract_text() for pagina in PdfReader(salida).pages)
    texto = " ".join(texto.split())  # los nombres largos parten líneas
    for codigo in codigos_origen | codigos_destino:
        assert codigo in texto
    assert "Fernández-Villaverde" in texto
