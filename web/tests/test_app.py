"""Pruebas de integración de la aplicación Streamlit."""

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

WEB_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB_DIR))
import app  # noqa: E402


def test_ejemplo_de_web_se_carga_y_agrupa_precedentes():
    datos = app.cargar_datos(WEB_DIR / "ejemplo.json")
    bloques = app.preparar_bloques(datos["resultados"])

    assert len(bloques) == 5
    assert all(app.resultados.es_precedente(bloque) for bloque in bloques[:4])
    assert len(next(bloque for bloque in bloques if len(bloque) == 2)) == 2


def test_busqueda_y_filtro_conservan_grupos_completos():
    datos = app.cargar_datos(WEB_DIR / "ejemplo.json")

    bloques = app.preparar_bloques(
        datos["resultados"],
        texto="Programacion",
        filtro="Precedentes aprobados",
    )

    assert len(bloques) == 1
    assert len(bloques[0]) == 2


def test_generador_crea_pdf_real_con_grupo_nm_completo():
    datos = app.cargar_datos(WEB_DIR / "ejemplo.json")
    seleccion = [fila for fila in datos["resultados"] if fila["grupo"] == 1]

    propuestas = app.pdf._propuestas_seleccionadas(seleccion)
    contenido = app.pdf.generar_pdf(
        {
            "nombre": "Ana",
            "grado": datos["grado"],
            "universidad": datos["universidad"],
        },
        seleccion,
    )

    assert len(propuestas) == 1
    assert len(propuestas[0]) == 2
    assert app.pdf.calcular_ects(propuestas[0]) == (6, 9.0)
    assert contenido.startswith(b"%PDF-")


def test_falta_json_muestra_error_y_catalogo_falta_de_bd(tmp_path):
    ruta_inexistente = tmp_path / "ejemplo.json"
    ruta_bd_inexistente = tmp_path / "uc3m.sqlite"
    script = tmp_path / "integracion.py"
    script.write_text(
        "\n".join(
            [
                f"import sys; sys.path.insert(0, {str(WEB_DIR)!r})",
                "from pathlib import Path",
                "import app",
                (
                    "app.main("
                    f"ruta_json=Path({str(ruta_inexistente)!r}), "
                    f"ruta_bd=Path({str(ruta_bd_inexistente)!r})"
                    ")"
                ),
            ]
        ),
        encoding="utf-8",
    )
    at = AppTest.from_file(str(script)).run()

    assert not at.exception
    assert any("resultados de ejemplo" in error.value for error in at.error)
    assert any("catálogo no está disponible" in error.value for error in at.error)


def test_app_muestra_aviso_ejemplo_y_no_habilita_pdf_sin_seleccion():
    at = AppTest.from_file(str(WEB_DIR / "app.py")).run(timeout=10)

    assert not at.exception
    assert any("todavía de ejemplo" in warning.value for warning in at.warning)
    assert any("Selecciona al menos una propuesta" in info.value for info in at.info)
    boton = next(
        button
        for button in at.get("download_button")
        if button.label == "Descargar propuesta PDF"
    )
    assert boton.disabled


def test_seleccion_y_nombre_habilitan_descarga_pdf():
    at = AppTest.from_file(str(WEB_DIR / "app.py")).run(timeout=10)
    propuesta_grupo = next(checkbox for checkbox in at.checkbox if "Programación" in checkbox.label)
    propuesta_grupo.set_value(True)
    at.text_input[1].set_value("Ana")
    at.run(timeout=10)

    assert not at.exception
    assert at.metric[0].value == "6"
    assert at.metric[1].value == "9.0"
    boton = next(
        button
        for button in at.get("download_button")
        if button.label == "Descargar propuesta PDF"
    )
    assert not boton.disabled


RESULTADOS_SELECCION = """{
  "grado": "Grado de prueba",
  "universidad": "Universidad de prueba",
  "resultados": [
    {"origen": {"codigo": "A1", "nombre": "Álgebra", "ects": 6},
     "destino": {"codigo": "MATH 1", "nombre": "Algebra", "ects": 6},
     "score": 0.9, "etiqueta": "PRECEDENTE_APROBADO", "aviso_ects": false, "grupo": null},
    {"origen": {"codigo": "B2", "nombre": "Bioquímica", "ects": 6},
     "destino": {"codigo": "CHEM 2", "nombre": "Biochemistry", "ects": 6},
     "score": 0.8, "etiqueta": "PRECEDENTE_APROBADO", "aviso_ects": false, "grupo": null},
    {"origen": {"codigo": "C3", "nombre": "Cálculo", "ects": 6},
     "destino": {"codigo": "MATH 3", "nombre": "Calculus", "ects": 6},
     "score": 0.7, "etiqueta": "SUGERENCIA_IA", "aviso_ects": false, "grupo": null}
  ]
}"""


def _app_con_resultados(tmp_path):
    ruta_json = tmp_path / "resultados.json"
    ruta_json.write_text(RESULTADOS_SELECCION, encoding="utf-8")
    script = tmp_path / "app_seleccion.py"
    script.write_text(
        f"import sys; sys.path.insert(0, {str(WEB_DIR)!r})\n"
        "from pathlib import Path\n"
        "import app\n"
        f"app.main(ruta_json=Path({str(ruta_json)!r}), ruta_bd=Path('no_existe.sqlite'))\n",
        encoding="utf-8",
    )
    return AppTest.from_file(str(script)).run(timeout=10)


def _checkbox(at, texto):
    return next(checkbox for checkbox in at.checkbox if texto in checkbox.label)


def test_la_marca_no_salta_a_otra_propuesta_al_buscar(tmp_path):
    at = _app_con_resultados(tmp_path)
    _checkbox(at, "Bioquímica").check().run(timeout=10)

    at.text_input[0].set_value("calculo").run(timeout=10)
    assert not _checkbox(at, "Cálculo").value

    at.text_input[0].set_value("").run(timeout=10)
    assert _checkbox(at, "Bioquímica").value
    assert not _checkbox(at, "Álgebra").value
    assert not _checkbox(at, "Cálculo").value


def test_lo_seleccionado_que_oculta_el_filtro_sigue_en_el_pdf(tmp_path):
    at = _app_con_resultados(tmp_path)
    _checkbox(at, "Álgebra").check().run(timeout=10)
    _checkbox(at, "Bioquímica").check().run(timeout=10)

    at.text_input[0].set_value("algebra").run(timeout=10)

    assert not at.exception
    assert at.metric[0].value == "12"
    assert any("que el filtro oculta" in caption.value for caption in at.caption)


def test_json_invalido_da_error_controlado(tmp_path):
    for contenido in ["no es json", "[]", '{"grado": "G"}', '{"grado": "G", "universidad": "U"}']:
        ruta = tmp_path / "resultados.json"
        ruta.write_text(contenido, encoding="utf-8")
        try:
            app.cargar_datos(ruta)
        except ValueError:
            continue
        raise AssertionError(f"debería fallar con: {contenido!r}")


def test_resultados_vacios_no_dan_propuestas(tmp_path):
    ruta = tmp_path / "resultados.json"
    ruta.write_text('{"grado": "G", "universidad": "U", "resultados": []}', encoding="utf-8")
    assert app.preparar_bloques(app.cargar_datos(ruta)["resultados"]) == []