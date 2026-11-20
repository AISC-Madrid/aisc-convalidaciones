import json
import sys
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB_DIR))

import indice  # noqa: E402


def escribir_indice(tmp_path, contenido):
    ruta = tmp_path / "index.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return ruta


COMBINACIONES = [
    {"grado": "Grado B", "universidad": "Uni 2", "archivo": "b__2.json"},
    {"grado": "Grado A", "universidad": "Uni 2", "archivo": "a__2.json"},
    {"grado": "Grado A", "universidad": "Uni 1", "archivo": "a__1.json"},
]


def test_el_indice_del_repo_es_valido_y_sus_archivos_existen():
    combinaciones = indice.cargar_indice()
    for c in combinaciones:
        assert indice.ruta_resultados(combinaciones, c["grado"], c["universidad"]).exists()


def test_desplegables_ordenados_y_universidades_filtradas_por_grado(tmp_path):
    combinaciones = indice.cargar_indice(
        escribir_indice(tmp_path, {"combinaciones": COMBINACIONES})
    )
    assert indice.grados(combinaciones) == ["Grado A", "Grado B"]
    assert indice.universidades(combinaciones, "Grado A") == ["Uni 1", "Uni 2"]
    assert indice.universidades(combinaciones, "Grado B") == ["Uni 2"]


def test_ruta_resultados_apunta_al_archivo_de_la_combinacion(tmp_path):
    ruta = indice.ruta_resultados(COMBINACIONES, "Grado A", "Uni 1", dir_datos=tmp_path)
    assert ruta == tmp_path / "a__1.json"


def test_ruta_resultados_de_combinacion_inexistente():
    with pytest.raises(ValueError, match="No hay resultados"):
        indice.ruta_resultados(COMBINACIONES, "Grado B", "Uni 1")


def test_indice_inexistente(tmp_path):
    with pytest.raises(ValueError, match="No se puede leer"):
        indice.cargar_indice(tmp_path / "no_existe.json")


def test_indice_con_json_mal_formado(tmp_path):
    ruta = tmp_path / "index.json"
    ruta.write_text("{ esto no es json", encoding="utf-8")
    with pytest.raises(ValueError, match="No se puede leer"):
        indice.cargar_indice(ruta)


@pytest.mark.parametrize(
    "contenido",
    [[], {}, {"combinaciones": []}, {"combinaciones": "Grado A"}],
)
def test_indice_sin_combinaciones(tmp_path, contenido):
    with pytest.raises(ValueError, match="ninguna combinación"):
        indice.cargar_indice(escribir_indice(tmp_path, contenido))


def test_combinacion_sin_archivo(tmp_path):
    contenido = {"combinaciones": [{"grado": "Grado A", "universidad": "Uni 1"}]}
    with pytest.raises(ValueError, match="sin grado, universidad o archivo"):
        indice.cargar_indice(escribir_indice(tmp_path, contenido))


def test_archivo_con_carpetas_se_rechaza(tmp_path):
    contenido = {
        "combinaciones": [
            {"grado": "Grado A", "universidad": "Uni 1", "archivo": "../secreto.json"}
        ]
    }
    with pytest.raises(ValueError, match="sin carpetas"):
        indice.cargar_indice(escribir_indice(tmp_path, contenido))


def test_combinacion_repetida(tmp_path):
    contenido = {"combinaciones": [COMBINACIONES[0], dict(COMBINACIONES[0])]}
    with pytest.raises(ValueError, match="repetida"):
        indice.cargar_indice(escribir_indice(tmp_path, contenido))
    