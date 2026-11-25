"""El JSON inventado de 200 resultados cumple el contrato y está al día con su generador."""

import importlib.util
import json
from pathlib import Path

from src.models.match import Resultados

RAIZ = Path(__file__).resolve().parent.parent
RUTA_JSON = RAIZ / "public" / "data" / "ejemplo_200.json"


def _generador():
    ruta = RAIZ / "scripts" / "generar_ejemplo_200.py"
    spec = importlib.util.spec_from_file_location("generar_ejemplo_200", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_valida_con_el_modelo_y_tiene_200_filas_y_grupos():
    datos = json.loads(RUTA_JSON.read_text(encoding="utf-8"))
    resultados = Resultados.model_validate(datos)

    assert len(resultados.resultados) == 200
    grupos = {m.grupo for m in resultados.resultados if m.grupo is not None}
    assert len(grupos) >= 5
    etiquetas = {m.etiqueta for m in resultados.resultados}
    assert etiquetas == {"PRECEDENTE_APROBADO", "SUGERENCIA_IA"}
    assert max(len(m.origen.nombre) for m in resultados.resultados) > 80


def test_propuestas_1a1_no_se_repiten():
    # La web identifica cada propuesta 1:1 por origen->destino; no puede haber dos iguales.
    datos = json.loads(RUTA_JSON.read_text(encoding="utf-8"))
    claves = [
        (f["origen"]["codigo"], f["destino"]["codigo"])
        for f in datos["resultados"]
        if f["grupo"] is None
    ]
    assert len(claves) == len(set(claves))


def test_el_json_del_repo_es_el_que_sale_del_generador():
    # Si alguien toca el generador y no regenera el JSON, este test lo avisa.
    datos = json.loads(RUTA_JSON.read_text(encoding="utf-8"))
    assert datos == _generador().generar()