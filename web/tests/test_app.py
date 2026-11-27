"""Pruebas de integración de la aplicación Streamlit.

Los resultados vienen de la MySQL; aquí los sirve el fixture ``publicar`` de conftest.py.
"""

import app  # web/ está en sys.path: lo pone conftest.py
from conftest import WEB_DIR, ejemplo
from streamlit.testing.v1 import AppTest


def _app():
    return AppTest.from_file(str(WEB_DIR / "app.py")).run(timeout=10)


def _boton_pdf(at):
    return next(
        button
        for button in at.get("download_button")
        if button.label == "Descargar propuesta PDF"
    )


def test_ejemplo_se_carga_y_agrupa_precedentes():
    bloques = app.preparar_bloques(ejemplo()["resultados"])

    assert len(bloques) == 5
    assert all(app.resultados.es_precedente(bloque) for bloque in bloques[:4])
    assert len(next(bloque for bloque in bloques if len(bloque) == 2)) == 2


def test_busqueda_y_filtro_conservan_grupos_completos():
    bloques = app.preparar_bloques(
        ejemplo()["resultados"],
        texto="Programacion",
        filtro="Precedentes aprobados",
    )

    assert len(bloques) == 1
    assert len(bloques[0]) == 2


def test_generador_crea_pdf_real_con_grupo_nm_completo():
    datos = ejemplo()
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


def test_sin_bd_muestra_error_en_resultados_y_en_catalogo():
    # Sin variables MYSQL_* (conftest las quita) no hay conexión: la web no se rompe.
    at = _app()

    assert not at.exception
    assert any("resultados no están disponibles" in error.value for error in at.error)
    assert any("catálogo no está disponible" in error.value for error in at.error)


def test_bd_sin_combinaciones_avisa(publicar):
    publicar()
    at = _app()

    assert not at.exception
    assert any("no hay resultados publicados" in info.value for info in at.info)


def test_combinacion_que_desaparece_da_error_controlado(publicar, monkeypatch):
    publicar(ejemplo())
    # La lista dice que existe, pero al leerla ya no está (p. ej., a mitad de una importación).
    def cargar(grado, universidad):
        raise app.bd_resultados.SinResultados("borrada")

    monkeypatch.setattr(app.bd_resultados, "cargar", cargar)
    at = _app()

    assert not at.exception
    assert any("resultados de esta combinación" in error.value for error in at.error)


def test_app_muestra_aviso_ejemplo_y_no_habilita_pdf_sin_seleccion(publicar):
    publicar(ejemplo())
    at = _app()

    assert not at.exception
    assert any("todavía de ejemplo" in warning.value for warning in at.warning)
    assert any("Selecciona al menos una propuesta" in info.value for info in at.info)
    assert _boton_pdf(at).disabled


def test_seleccion_y_nombre_habilitan_descarga_pdf(publicar):
    publicar(ejemplo())
    at = _app()
    propuesta_grupo = next(checkbox for checkbox in at.checkbox if "Programación" in checkbox.label)
    propuesta_grupo.set_value(True)
    at.text_input[1].set_value("Ana")
    at.run(timeout=10)

    assert not at.exception
    assert at.metric[0].value == "6"
    assert at.metric[1].value == "9.0"
    assert not _boton_pdf(at).disabled


def _fila(origen, nombre_origen, destino, nombre_destino, score, etiqueta):
    return {
        "origen": {"codigo": origen, "nombre": nombre_origen, "ects": 6},
        "destino": {"codigo": destino, "nombre": nombre_destino, "ects": 6},
        "score": score,
        "etiqueta": etiqueta,
        "aviso_ects": False,
        "grupo": None,
    }


RESULTADOS_SELECCION = {
    "grado": "Grado de prueba",
    "universidad": "Universidad de prueba",
    "generado": "2026-11-25",
    "modelo": "multilingual-e5-small",
    "umbral": 0.7,
    "resultados": [
        _fila("A1", "Álgebra", "MATH 1", "Algebra", 0.9, "PRECEDENTE_APROBADO"),
        _fila("B2", "Bioquímica", "CHEM 2", "Biochemistry", 0.8, "PRECEDENTE_APROBADO"),
        _fila("C3", "Cálculo", "MATH 3", "Calculus", 0.7, "SUGERENCIA_IA"),
    ],
}


def _checkbox(at, texto):
    return next(checkbox for checkbox in at.checkbox if texto in checkbox.label)


def test_la_marca_no_salta_a_otra_propuesta_al_buscar(publicar):
    publicar(RESULTADOS_SELECCION)
    at = _app()
    _checkbox(at, "Bioquímica").check().run(timeout=10)

    at.text_input[0].set_value("calculo").run(timeout=10)
    assert not _checkbox(at, "Cálculo").value

    at.text_input[0].set_value("").run(timeout=10)
    assert _checkbox(at, "Bioquímica").value
    assert not _checkbox(at, "Álgebra").value
    assert not _checkbox(at, "Cálculo").value


def test_lo_seleccionado_que_oculta_el_filtro_sigue_en_el_pdf(publicar):
    publicar(RESULTADOS_SELECCION)
    at = _app()
    _checkbox(at, "Álgebra").check().run(timeout=10)
    _checkbox(at, "Bioquímica").check().run(timeout=10)

    at.text_input[0].set_value("algebra").run(timeout=10)

    assert not at.exception
    assert at.metric[0].value == "12"
    assert any("que el filtro oculta" in caption.value for caption in at.caption)


def test_resultados_vacios_no_dan_propuestas():
    assert app.preparar_bloques([]) == []


def test_cambiar_de_combinacion_cambia_la_tabla(publicar):
    datos = ejemplo()
    otro = {**datos, "grado": "Grado inventado", "resultados": datos["resultados"][:1]}
    publicar(datos, otro)

    at = _app()
    assert not at.exception
    at.selectbox(key="grado").set_value(datos["grado"]).run(timeout=10)
    filas_ejemplo = len(at.dataframe[0].value)

    at.selectbox(key="grado").set_value("Grado inventado").run(timeout=10)
    assert not at.exception
    assert len(at.dataframe[0].value) == 1
    assert filas_ejemplo > 1


def test_cabecera_formatea_fecha_y_umbral():
    texto = app.texto_cabecera(
        {"grado": "G", "universidad": "U", "generado": "2026-11-25", "umbral": 0.71}
    )
    assert texto == "G · U · Generado el 25/11/2026 · Umbral de similitud: 0,71"
    # Un booleano no es un umbral.
    assert "Umbral" not in app.texto_cabecera({"grado": "G", "universidad": "U", "umbral": True})


def _resultados_inventados(n):
    return {
        "grado": "Grado de prueba",
        "universidad": "Uni de prueba",
        "generado": "2026-11-25",
        "modelo": "multilingual-e5-small",
        "umbral": 0.5,
        "resultados": [
            {
                "origen": {"codigo": f"O{i}", "nombre": f"Asignatura {i:03d}", "ects": 6},
                "destino": {"codigo": f"D{i}", "nombre": f"Course {i:03d}", "ects": 6},
                "score": 0.5,
                "etiqueta": "SUGERENCIA_IA",
                "aviso_ects": False,
                "grupo": None,
            }
            for i in range(n)
        ],
    }


def test_200_resultados_se_paginan_y_la_seleccion_se_conserva(publicar):
    publicar(_resultados_inventados(200))
    at = _app()
    assert not at.exception

    tamano = app.resultados.TAMANO_PAGINA
    propuestas = [checkbox for checkbox in at.checkbox if "→" in checkbox.label]
    assert len(propuestas) == tamano
    assert len(at.dataframe[0].value) == tamano

    marcada = propuestas[0].label
    propuestas[0].check().run(timeout=10)
    at.number_input(key="pagina").set_value(2).run(timeout=10)

    assert not at.exception
    assert all(checkbox.label != marcada for checkbox in at.checkbox)
    assert at.metric[0].value == "6"
