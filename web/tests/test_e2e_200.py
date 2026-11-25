"""Test end-to-end de la pantalla de resultados con el JSON inventado de 200 filas (#41).

Recorre lo mismo que hará un alumno en el servidor: cargar, filtrar, seleccionar un grupo
n:m y descargar el PDF. Usa el index.json y el ejemplo_200.json reales de public/data.
"""

import json
from pathlib import Path

from pypdf import PdfReader
from streamlit.testing.v1 import AppTest

WEB_DIR = Path(__file__).resolve().parents[1]
DATOS_DIR = WEB_DIR.parent / "public" / "data"
GRADO = "Grado en Ingeniería Biomédica"


def _datos():
    return json.loads((DATOS_DIR / "ejemplo_200.json").read_text(encoding="utf-8"))


def _app(tmp_path):
    """Arranca la web real, guardando en tmp_path el PDF que genere para poder abrirlo."""
    salida = tmp_path / "propuesta.pdf"
    script = tmp_path / "app_e2e.py"
    script.write_text(
        f"import sys; sys.path.insert(0, {str(WEB_DIR)!r})\n"
        "from pathlib import Path\n"
        "import pdf\n"
        "_original = pdf.generar_pdf\n"
        "def _espia(*args, **kwargs):\n"
        "    contenido = _original(*args, **kwargs)\n"
        f"    Path({str(salida)!r}).write_bytes(contenido)\n"
        "    return contenido\n"
        "pdf.generar_pdf = _espia\n"
        "import app\n"
        "app.main(ruta_bd=Path('no_existe.sqlite'))\n",
        encoding="utf-8",
    )
    at = AppTest.from_file(str(script), default_timeout=20).run()
    at.selectbox(key="grado").set_value(GRADO).run()
    return at, salida


def _boton_pdf(at):
    return next(b for b in at.get("download_button") if b.label == "Descargar propuesta PDF")


def test_cabecera_muestra_fecha_y_umbral_del_json(tmp_path):
    at, _ = _app(tmp_path)

    assert not at.exception
    cabecera = " ".join(caption.value for caption in at.caption)
    assert "Generado el 25/11/2026" in cabecera
    assert "Umbral de similitud: 0,71" in cabecera


def test_200_resultados_se_paginan(tmp_path):
    datos = _datos()
    filas = datos["resultados"]
    grupos = {f["grupo"] for f in filas if f["grupo"] is not None}
    en_grupo = sum(f["grupo"] is not None for f in filas)
    bloques = len(filas) - en_grupo + len(grupos)

    at, _ = _app(tmp_path)

    assert len(filas) == 200
    assert len(at.dataframe[0].value) == 20
    assert any(f"de {bloques}" in caption.value for caption in at.caption)


def test_cargar_filtrar_seleccionar_grupo_y_sacar_pdf(tmp_path):
    datos = _datos()
    # El grupo 1 tiene los nombres más largos: es el caso difícil para el PDF.
    grupo = [f for f in datos["resultados"] if f["grupo"] == 1]
    codigos_origen = {f["origen"]["codigo"] for f in grupo}
    codigos_destino = {f["destino"]["codigo"] for f in grupo}
    buscar = sorted(codigos_destino)[0]

    at, salida = _app(tmp_path)

    # Filtrar: solo precedentes y búsqueda por un código de destino del grupo.
    at.selectbox[2].set_value("Precedentes aprobados").run()
    next(t for t in at.text_input if t.label.startswith("Buscar")).set_value(buscar).run()
    propuesta = next(c for c in at.checkbox if buscar in c.label)
    # El grupo sale como una sola propuesta con todas sus asignaturas.
    assert all(codigo in propuesta.label for codigo in codigos_origen | codigos_destino)

    # Seleccionar el grupo entero y poner el nombre.
    propuesta.check().run()
    next(t for t in at.text_input if t.label == "Nombre del alumno").set_value(
        # nombre largo, con tilde, guión para probar PDF
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