"""Los 200 resultados inventados cumplen el contrato y se guardan en la BD."""

import importlib.util
import sqlite3
from pathlib import Path

from src.export import resultados_bd
from src.models.match import Resultados

RAIZ = Path(__file__).resolve().parent.parent


def _generador():
    ruta = RAIZ / "scripts" / "generar_ejemplo_200.py"
    spec = importlib.util.spec_from_file_location("generar_ejemplo_200", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_valida_con_el_modelo_y_tiene_200_filas_y_grupos():
    resultados = Resultados.model_validate(_generador().generar())

    assert len(resultados.resultados) == 200
    grupos = {m.grupo for m in resultados.resultados if m.grupo is not None}
    assert len(grupos) >= 5
    etiquetas = {m.etiqueta for m in resultados.resultados}
    assert etiquetas == {"PRECEDENTE_APROBADO", "SUGERENCIA_IA"}
    assert max(len(m.origen.nombre) for m in resultados.resultados) > 80


def test_propuestas_1a1_no_se_repiten():
    # La web identifica cada propuesta 1:1 por origen->destino; no puede haber dos iguales.
    claves = [
        (f["origen"]["codigo"], f["destino"]["codigo"])
        for f in _generador().generar()["resultados"]
        if f["grupo"] is None
    ]
    assert len(claves) == len(set(claves))


def test_la_semilla_fija_da_siempre_lo_mismo():
    generador = _generador()
    assert generador.generar() == generador.generar()


def test_main_guarda_las_200_filas_en_la_bd(tmp_path, capsys):
    ruta = tmp_path / "resultados.sqlite"
    generador = _generador()

    generador.main(["--salida", str(ruta)])
    generador.main(["--salida", str(ruta)])  # volver a lanzarlo no duplica

    datos = generador.generar()
    with sqlite3.connect(ruta) as conexion:
        leido = resultados_bd.leer(conexion, datos["grado"], datos["universidad"])
        assert conexion.execute("SELECT COUNT(*) FROM resultados").fetchone() == (200,)
    assert leido == Resultados.model_validate(datos)
    assert "200 filas, 10 grupos n:m" in capsys.readouterr().out
