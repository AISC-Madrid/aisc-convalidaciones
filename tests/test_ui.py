import json

import pytest
from streamlit.testing.v1 import AppTest

from src.ui.app import COLUMNAS, cargar_datos, preparar_tabla


def ejecutar_app(ruta):
    from src.ui.app import main

    main(ruta)


@pytest.fixture
def ejemplo():
    return {
        "generado": "2026-10-20",
        "modelo": "ejemplo",
        "umbral": 0.71,
        "grado": "Informática",
        "universidad": "Universidad de ejemplo",
        "resultados": [
            {
                "origen": {"codigo": "001", "nombre": "Redes", "ects": 6},
                "destino": {
                    "codigo": "CS1",
                    "nombre": "Networks",
                    "ects": 4,
                    "url": "https://example.org/curso",
                },
                "score": 0.79,
                "etiqueta": "SUGERENCIA_IA",
                "aviso_ects": True,
            }
        ],
    }


def test_pantalla_sin_archivo(tmp_path):
    app = AppTest.from_function(ejecutar_app, args=(str(tmp_path / "ausente.json"),)).run(
        timeout=15
    )
    assert not app.exception
    assert all(selector.disabled for selector in app.selectbox)
    assert "no hay resultados" in app.info[0].value


def test_carga_y_tabla(tmp_path, ejemplo):
    ruta = tmp_path / "ejemplo.json"
    ruta.write_text(json.dumps(ejemplo), encoding="utf-8")
    fila = preparar_tabla(cargar_datos(ruta)["resultados"])[0]
    assert fila["Asignatura de origen"] == "Redes (001)"
    assert fila["Asignatura de destino"] == "Networks (CS1)"
    assert fila["ECTS destino"] == 4
    assert fila["Etiqueta"] == "Sugerencia IA"
    assert fila["Aviso"] == "ECTS dispares"
    app = AppTest.from_function(ejecutar_app, args=(str(ruta),)).run(timeout=15)
    assert not app.exception
    assert app.selectbox[0].value == "Informática"
    assert not app.selectbox[0].disabled
    assert len(app.dataframe[0].value) == 1


@pytest.mark.parametrize("contenido", ["{", "[]", '{"grado": "Informática"}'])
def test_archivo_invalido(tmp_path, contenido):
    ruta = tmp_path / "invalido.json"
    ruta.write_text(contenido, encoding="utf-8")
    app = AppTest.from_function(ejecutar_app, args=(str(ruta),)).run(timeout=15)
    assert not app.exception
    assert app.error


def test_resultados_vacios(tmp_path, ejemplo):
    ejemplo["resultados"] = []
    ruta = tmp_path / "vacio.json"
    ruta.write_text(json.dumps(ejemplo), encoding="utf-8")
    app = AppTest.from_function(ejecutar_app, args=(str(ruta),)).run(timeout=15)
    assert not app.exception
    assert "No hay equivalencias" in app.info[0].value


def test_config_de_columnas_coincide_con_la_tabla(ejemplo):
    assert COLUMNAS.keys() == preparar_tabla(ejemplo["resultados"])[0].keys()


def test_precedente_sin_aviso(ejemplo):
    ejemplo["resultados"][0].update(etiqueta="PRECEDENTE_APROBADO", aviso_ects=False)
    fila = preparar_tabla(ejemplo["resultados"])[0]
    assert fila["Etiqueta"] == "Precedente aprobado"
    assert fila["Aviso"] == ""


def test_json_del_equipo_en_pantalla():
    from src.ui.app import RUTA_JSON

    app = AppTest.from_function(ejecutar_app, args=(str(RUTA_JSON),)).run(timeout=15)
    assert not app.exception
    assert not app.error
    tabla = app.dataframe[0].value
    assert len(tabla) == 6
    assert (tabla["Grupo conjunto"] == "1").sum() == 2
    assert (
        (tabla["Similitud"] < 0.71) & (tabla["Etiqueta"] == "Precedente aprobado")
    ).any()


def test_url_opcional_y_validacion(tmp_path, ejemplo):
    ejemplo["resultados"][0]["destino"].pop("url")
    ruta = tmp_path / "ejemplo.json"
    ruta.write_text(json.dumps(ejemplo), encoding="utf-8")
    assert preparar_tabla(cargar_datos(ruta)["resultados"])[0]["Ficha de destino"] is None
    ejemplo["resultados"][0]["score"] = 2
    ruta.write_text(json.dumps(ejemplo), encoding="utf-8")
    app = AppTest.from_function(ejecutar_app, args=(str(ruta),)).run(timeout=15)
    assert not app.exception
    assert app.error


def test_filtros_filtran_la_tabla(tmp_path, ejemplo):
    sugerencia = ejemplo["resultados"][0]
    ejemplo["resultados"] = [
        sugerencia,
        {
            **sugerencia,
            "origen": {"codigo": "002", "nombre": "Arquitectura", "ects": 6},
            "destino": {
                **sugerencia["destino"],
                "ects": 6,
            },
            "score": 0.95,
            "etiqueta": "PRECEDENTE_APROBADO",
            "aviso_ects": False,
        },
    ]
    ruta = tmp_path / "ejemplo.json"
    ruta.write_text(json.dumps(ejemplo), encoding="utf-8")

    app = AppTest.from_function(ejecutar_app, args=(str(ruta),)).run(timeout=15)
    assert not app.exception
    assert len(app.dataframe[0].value) == 2

    app.checkbox(key="filtro_Sugerencia IA").uncheck().run(timeout=15)
    assert len(app.dataframe[0].value) == 1
    assert app.dataframe[0].value.iloc[0]["Etiqueta"] == "Precedente aprobado"

    app = AppTest.from_function(ejecutar_app, args=(str(ruta),)).run(timeout=15)
    app.slider[0].set_value(0.8).run(timeout=15)
    assert len(app.dataframe[0].value) == 1
    assert app.dataframe[0].value.iloc[0]["Similitud"] == 0.95

    app = AppTest.from_function(ejecutar_app, args=(str(ruta),)).run(timeout=15)
    app.selectbox[2].set_value("Redes (001)").run(timeout=15)
    assert len(app.dataframe[0].value) == 1
    assert app.dataframe[0].value.iloc[0]["Asignatura de origen"] == "Redes (001)"

def test_seleccionar_grupo_actualiza_contadores():
    from src.ui.app import RUTA_JSON

    datos = cargar_datos(RUTA_JSON)
    resultados = datos["resultados"]

    indice = next(
        indice
        for indice, resultado in enumerate(resultados)
        if resultado.get("grupo") is not None
    )

    app = AppTest.from_function(
        ejecutar_app,
        args=(str(RUTA_JSON),),
    ).run(timeout=15)

    assert not app.exception
    assert [metrica.value for metrica in app.metric] == ["0", "0"]

    app.checkbox(key=f"propuesta_{indice}").check().run(timeout=15)

    assert not app.exception
    assert [float(metrica.value) for metrica in app.metric] == [6, 9]

    app.checkbox(key=f"propuesta_{indice}").uncheck().run(timeout=15)

    assert not app.exception
    assert [float(metrica.value) for metrica in app.metric] == [0, 0]

def test_boton_pdf_solo_con_seleccion():
    from src.ui.app import RUTA_JSON

    app = AppTest.from_function(ejecutar_app, args=(str(RUTA_JSON),)).run(timeout=15)

    assert not app.exception
    assert app.get("download_button")[0].proto.disabled

    app.checkbox(key="propuesta_0").check().run(timeout=15)

    assert not app.exception
    assert not app.get("download_button")[0].proto.disabled
