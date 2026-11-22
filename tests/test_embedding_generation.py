import json

import numpy as np
import pytest

from src.embeddings.generar_embeddings import (
    cargar_embeddings,
    comprobar_top5,
    generar_embeddings_catalogos,
    generar_embeddings_corpus,
)


def _vector(indice):
    vector = np.zeros(384, dtype=np.float32)
    vector[indice] = 1.0
    return vector


def _escribir_corpus(ruta, asignaturas):
    ruta.write_text(
        "".join(json.dumps(asignatura) + "\n" for asignatura in asignaturas),
        encoding="utf-8",
    )
    return ruta


def test_generacion_y_carga_conservan_texto_y_alineacion_de_metadatos(tmp_path):
    corpus = _escribir_corpus(
        tmp_path / "corpus.jsonl",
        [
            {"codigo": "UC1", "nombre": "Estructuras de Datos", "texto": "query: texto completo."},
            {"codigo": "UC2", "nombre": "Algoritmos", "texto": "query: otro texto."},
        ],
    )
    textos_codificados = []

    def encoder(textos):
        textos_codificados.extend(textos)
        return np.stack([_vector(0), _vector(1)])

    ruta_vectores = tmp_path / "salida" / "vectors.npy"
    ruta_metadatos = tmp_path / "salida" / "metadata.json"
    generar_embeddings_corpus(
        corpus,
        ruta_vectores,
        ruta_metadatos,
        encoder=encoder,
    )

    vectores, metadatos = cargar_embeddings(ruta_vectores, ruta_metadatos)
    assert textos_codificados == ["query: texto completo.", "query: otro texto."]
    assert vectores.shape == (2, 384)
    assert [fila["codigo"] for fila in metadatos["asignaturas"]] == ["UC1", "UC2"]
    assert [fila["nombre"] for fila in metadatos["asignaturas"]] == [
        "Estructuras de Datos",
        "Algoritmos",
    ]
    np.testing.assert_array_equal(vectores, np.stack([_vector(0), _vector(1)]))


def test_top5_carga_vectores_y_devuelve_metadatos_en_orden(tmp_path, capsys):
    corpus_uc3m = _escribir_corpus(
        tmp_path / "uc3m.jsonl",
        [
            {
                "codigo": "UC1",
                "nombre": "Estructuras de Datos",
                "texto": "query: estructura completa.",
            },
            {"codigo": "UC2", "nombre": "Otra asignatura", "texto": "query: otro texto."},
        ],
    )
    corpus_gatech = _escribir_corpus(
        tmp_path / "gatech.jsonl",
        [
            {"codigo": "GT1", "nombre": "Curso A", "texto": "query: curso a."},
            {"codigo": "GT2", "nombre": "Curso B", "texto": "query: curso b."},
            {"codigo": "GT3", "nombre": "Curso C", "texto": "query: curso c."},
            {"codigo": "GT4", "nombre": "Curso D", "texto": "query: curso d."},
            {"codigo": "GT5", "nombre": "Curso E", "texto": "query: curso e."},
            {"codigo": "GT6", "nombre": "Curso F", "texto": "query: curso f."},
        ],
    )

    def encoder(textos):
        if "query: estructura completa." in textos:
            return np.stack([_vector(0), _vector(1)])
        return np.stack(
            [
                _vector(2),
                _vector(0),
                _vector(1),
                0.8 * _vector(0) + 0.6 * _vector(1),
                0.6 * _vector(0) + 0.8 * _vector(1),
                -_vector(0),
            ]
        )

    generar_embeddings_catalogos(
        corpus_uc3m,
        corpus_gatech,
        tmp_path,
        encoder=encoder,
    )

    resultados = comprobar_top5(tmp_path)

    assert [resultado[:2] for resultado in resultados] == [
        ("GT2", "Curso B"),
        ("GT4", "Curso D"),
        ("GT5", "Curso E"),
        ("GT1", "Curso A"),
        ("GT3", "Curso C"),
    ]
    assert [resultado[2] for resultado in resultados] == pytest.approx([1.0, 0.8, 0.6, 0.0, 0.0])
    salida = capsys.readouterr().out
    assert "UC1: Estructuras de Datos" in salida
    assert "GT2: Curso B — 1.000000" in salida
    assert "GT6: Curso F" not in salida


def test_simulacion_reproducible_separada_y_no_apta_para_top5(tmp_path):
    corpus_uc3m = _escribir_corpus(
        tmp_path / "uc3m.jsonl",
        [{"codigo": "UC1", "nombre": "Estructuras de Datos", "texto": "query: texto."}],
    )
    corpus_gatech = _escribir_corpus(
        tmp_path / "gatech.jsonl",
        [{"codigo": "GT1", "nombre": "Curso", "texto": "query: curso."}],
    )

    primera = generar_embeddings_catalogos(
        corpus_uc3m,
        corpus_gatech,
        tmp_path / "primera",
        simular=True,
        semilla=123,
    )
    segunda = generar_embeddings_catalogos(
        corpus_uc3m,
        corpus_gatech,
        tmp_path / "segunda",
        simular=True,
        semilla=123,
    )

    for nombre in ("uc3m", "gatech"):
        ruta_primera, metadata_primera = primera[nombre]
        ruta_segunda, _ = segunda[nombre]
        assert ruta_primera.parent.name == "simulados"
        assert not (tmp_path / "primera" / f"embeddings_{nombre}.npy").exists()
        np.testing.assert_array_equal(
            np.load(ruta_primera, allow_pickle=False),
            np.load(ruta_segunda, allow_pickle=False),
        )
        assert json.loads(metadata_primera.read_text(encoding="utf-8"))["simulado"] is True

    with pytest.raises(ValueError, match="no permiten validar similitudes reales"):
        comprobar_top5(tmp_path / "primera" / "simulados")


def test_coincidencias_multiples_se_muestran_sin_elegir(tmp_path, capsys):
    corpus_uc3m = _escribir_corpus(
        tmp_path / "uc3m.jsonl",
        [
            {"codigo": "UC1", "nombre": "Estructuras de Datos", "texto": "query: texto 1."},
            {"codigo": "UC2", "nombre": "Estructuras de Datos", "texto": "query: texto 2."},
        ],
    )
    corpus_gatech = _escribir_corpus(
        tmp_path / "gatech.jsonl",
        [{"codigo": "GT1", "nombre": "Curso", "texto": "query: curso."}],
    )

    def encoder(textos):
        return np.stack([_vector(indice) for indice, _ in enumerate(textos)])

    generar_embeddings_catalogos(
        corpus_uc3m,
        corpus_gatech,
        tmp_path,
        encoder=encoder,
    )

    with pytest.raises(ValueError, match="varias coincidencias"):
        comprobar_top5(tmp_path)

    salida = capsys.readouterr().out
    assert "UC1: Estructuras de Datos" in salida
    assert "UC2: Estructuras de Datos" in salida
    assert "Top-5" not in salida


def test_carga_rechaza_desajuste_entre_vectores_y_metadatos(tmp_path):
    ruta_vectores = tmp_path / "vectors.npy"
    ruta_metadatos = tmp_path / "metadata.json"
    np.save(ruta_vectores, np.stack([_vector(0)]), allow_pickle=False)
    ruta_metadatos.write_text(
        json.dumps({"dimension": 384, "asignaturas": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="forma"):
        cargar_embeddings(ruta_vectores, ruta_metadatos)


def test_fallo_del_encoder_real_no_activa_simulacion_ni_guarda_resultados(tmp_path):
    corpus = _escribir_corpus(
        tmp_path / "corpus.jsonl",
        [{"codigo": "UC1", "nombre": "Asignatura", "texto": "query: texto."}],
    )
    ruta_vectores = tmp_path / "embeddings.npy"
    ruta_metadatos = tmp_path / "embeddings.json"

    def encoder_fallido(_textos):
        raise RuntimeError("error del encoder")

    with pytest.raises(RuntimeError, match="error del encoder"):
        generar_embeddings_corpus(
            corpus,
            ruta_vectores,
            ruta_metadatos,
            encoder=encoder_fallido,
        )

    assert not ruta_vectores.exists()
    assert not ruta_metadatos.exists()
